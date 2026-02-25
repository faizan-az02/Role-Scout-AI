from __future__ import annotations

from typing import Any, Dict, List


def _to_proper_case(s: str | None) -> str:
  """Return string in proper (title) case for consistent report display."""
  if not s or not isinstance(s, str):
    return s or ""
  return s.strip().title()


def build_report(result: Dict[str, Any]) -> Dict[str, Any]:
  """
  Build a structured, human-friendly report object from the final lookup result.

  This is a pure formatter: no LLM calls, no extra network access.
  It does NOT change the core lookup logic or retries.
  Company and role are shown in proper case for consistency.
  """
  first = result.get("first_name")
  last = result.get("last_name")
  company = _to_proper_case(result.get("company"))
  title = _to_proper_case(result.get("current_title"))
  confidence = result.get("confidence_score") or 0.0
  primary = result.get("primary_source")
  sources: List[str] = list(result.get("validation_sources") or [])

  full_name_parts = [p for p in [first, last] if p]
  full_name = " ".join(full_name_parts) if full_name_parts else ""

  if confidence > 0.8:
    band = "High"
    band_copy = "High confidence based on strong, agreeing sources."
  elif confidence >= 0.6:
    band = "Medium"
    band_copy = "Moderate confidence: sources are good but not overwhelming."
  else:
    band = "Low"
    band_copy = "Low confidence: treat this as a lead, not a fact."

  headline_parts = []
  if full_name:
    headline_parts.append(full_name)
  if title:
    headline_parts.append(title)
  if company:
    headline_parts.append(f"@ {company}")

  headline = " – ".join(headline_parts) if headline_parts else ""

  notes: List[str] = []
  if not full_name:
    notes.append("No clear full name could be extracted from the validation output.")
  if not sources:
    notes.append("No validation URLs were available; confidence is derived heuristically.")

  return {
    "headline": headline,
    "full_name": full_name,
    "company": company,
    "title": title,
    "confidence_label": f"{band} confidence ({confidence:.2f})",
    "confidence_band": band,
    "confidence_explanation": band_copy,
    "primary_source": primary,
    "source_count": len(sources),
    "sources": sources,
    "notes": notes,
  }

