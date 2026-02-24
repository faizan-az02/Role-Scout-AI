from __future__ import annotations

from io import BytesIO
from typing import Any, Dict

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas


def _draw_wrapped_text(c: canvas.Canvas, text: str, x: int, y: int, max_width: int, line_height: int = 14) -> int:
  """
  Draw simple wrapped text and return the new y position.
  """
  if not text:
    return y

  words = text.split()
  line = ""
  for word in words:
    test_line = (line + " " + word).strip()
    if c.stringWidth(test_line, "Helvetica", 10) <= max_width:
      line = test_line
    else:
      c.drawString(x, y, line)
      y -= line_height
      line = word
  if line:
    c.drawString(x, y, line)
    y -= line_height
  return y


def generate_report_pdf(report: Dict[str, Any]) -> bytes:
  """
  Generate a simple one-page PDF from the report object.
  """
  buffer = BytesIO()
  c = canvas.Canvas(buffer, pagesize=LETTER)
  width, height = LETTER

  # Set the internal PDF document title so viewers can show a meaningful name.
  doc_title = report.get("full_name") or report.get("headline") or "Role Scout AI Lookup Report"
  c.setTitle(str(doc_title))

  margin_x = 60
  y = height - 72

  c.setFont("Helvetica-Bold", 16)
  title = report.get("headline") or "Role Scout AI Lookup Report"
  c.drawString(margin_x, y, title)
  y -= 28

  c.setFont("Helvetica", 10)
  c.drawString(margin_x, y, report.get("confidence_label", ""))
  y -= 20

  c.setFont("Helvetica-Bold", 11)
  c.drawString(margin_x, y, "Summary")
  y -= 16

  c.setFont("Helvetica", 10)
  y = _draw_wrapped_text(
    c,
    report.get("confidence_explanation", ""),
    margin_x,
    y,
    int(width - 2 * margin_x),
  )

  c.setFont("Helvetica-Bold", 11)
  c.drawString(margin_x, y, "Primary source")
  y -= 14

  c.setFont("Helvetica", 10)
  primary = report.get("primary_source") or "N/A"
  y = _draw_wrapped_text(c, primary, margin_x, y, int(width - 2 * margin_x))

  c.setFont("Helvetica-Bold", 11)
  c.drawString(margin_x, y, "Validation sources")
  y -= 14

  c.setFont("Helvetica", 10)
  sources = report.get("sources") or []
  if not sources:
    y = _draw_wrapped_text(c, "None", margin_x, y, int(width - 2 * margin_x))
  else:
    for url in sources:
      y = _draw_wrapped_text(c, f"- {url}", margin_x, y, int(width - 2 * margin_x))

  notes = report.get("notes") or []
  if notes:
    y -= 10
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin_x, y, "Notes")
    y -= 14
    c.setFont("Helvetica", 10)
    for note in notes:
      y = _draw_wrapped_text(c, f"- {note}", margin_x, y, int(width - 2 * margin_x))

  c.showPage()
  c.save()

  buffer.seek(0)
  return buffer.getvalue()

