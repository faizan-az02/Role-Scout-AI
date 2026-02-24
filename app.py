from __future__ import annotations

import json
import subprocess
import sys
from io import BytesIO
from pathlib import Path
import re

from flask import Flask, jsonify, render_template, request, send_file


BASE_DIR = Path(__file__).resolve().parent

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)

from reporter import build_report  # noqa: E402
from report_pdf import generate_report_pdf  # noqa: E402


def _extract_final_json(stdout: str) -> dict:
    """
    Extract the final JSON object printed by the existing CLI (main.py)
    without modifying any of its logic.
    """
    last_brace_index = stdout.rfind("{")
    if last_brace_index == -1:
        raise ValueError("No JSON object found in CLI output.")

    json_text = stdout[last_brace_index:]
    return json.loads(json_text)


def run_lookup(company: str, role: str) -> dict:
    """
    Adapter around the existing CLI-based main.py.

    It:
    - Executes main.py as a subprocess.
    - Feeds company and role via stdin (as the CLI expects).
    - Parses the final JSON printed by main.py.

    IMPORTANT: Does not modify or depend on any internal logic of main.py.
    """
    proc = subprocess.run(
        [sys.executable, "main.py"],
        input=f"{company}\n{role}\n",
        text=True,
        capture_output=True,
        cwd=str(BASE_DIR),
    )

    if proc.returncode != 0:
        # Surface combined output for easier debugging in the API error response.
        combined = (proc.stderr or "") + "\n" + (proc.stdout or "")
        raise RuntimeError(f"Lookup process failed with code {proc.returncode}: {combined}")

    return _extract_final_json(proc.stdout)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/lookup", methods=["POST"])
def lookup():
    data = request.get_json(silent=True) or {}

    company = (data.get("company") or "").strip()
    role = (data.get("role") or "").strip()

    if not company or not role:
        return (
            jsonify(
                {
                    "error": "Both 'company' and 'role' are required.",
                    "company": company,
                    "current_title": role,
                    "confidence_score": 0.0,
                    "attempts": 0,
                }
            ),
            400,
        )

    try:
        result = run_lookup(company=company, role=role)
        # Attach a presenter-friendly report object for the UI.
        try:
            report = build_report(result)
            result["report"] = report
        except Exception:
            # Reporting is non-critical; if it fails, we still return core result.
            pass
        return jsonify(result)
    except Exception as exc:  # noqa: B902
        # Do NOT modify or inspect internal logic; just surface a structured error.
        return (
            jsonify(
                {
                    "error": "Lookup failed",
                    "detail": str(exc),
                    "company": company,
                    "current_title": role,
                    "confidence_score": 0.0,
                    "attempts": 0,
                }
            ),
            500,
        )


@app.route("/report", methods=["POST"])
def report_pdf():
  """
  Generate a PDF report in a new tab based on the existing lookup result.

  The frontend posts the full JSON result as a hidden form field named 'payload',
  so we don't need to re-run the lookup or change core logic.
  """
  payload = request.form.get("payload") or ""
  if not payload:
    return "Missing payload", 400

  try:
    result = json.loads(payload)
  except Exception:
    return "Invalid payload", 400

  report = build_report(result)
  pdf_bytes = generate_report_pdf(report)

  # Use the found person's name as the browser tab/file title when possible.
  full_name = (report.get("full_name") or "").strip()
  if full_name:
    # Simple, safe filename from the full name.
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", full_name) or "role_scout_report"
    download_name = f"{safe_stem}.pdf"
  else:
    download_name = "role_scout_report.pdf"

  return send_file(
    BytesIO(pdf_bytes),
    mimetype="application/pdf",
    as_attachment=False,
    download_name=download_name,
  )


if __name__ == "__main__":
    # Development entrypoint:
    #   python app.py
    app.run(host="0.0.0.0", port=8000, debug=True)

