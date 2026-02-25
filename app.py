from __future__ import annotations

import csv
import json
import re
import uuid
from io import BytesIO, StringIO
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file, url_for

from lookup_service import run_lookup  # shared backend lookup pipeline


BASE_DIR = Path(__file__).resolve().parent

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)

# In-memory store for generated batch CSVs/PDFs keyed by a one-time token.
_BATCH_CSV_DOWNLOADS: dict[str, bytes] = {}
_BATCH_PDF_DOWNLOADS: dict[str, bytes] = {}

from reporter import build_report  # noqa: E402
from report_pdf import generate_batch_csv_pdf, generate_report_pdf  # noqa: E402


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


@app.route("/csv-report", methods=["POST"])
def csv_report():
    """
    Accept an uploaded CSV of Title / Company pairs, run lookups,
    and return a PDF summarising the enriched rows.

    The expected header structure is based on test_data.csv:
      Title,Company Name,First Name,Last Name,Source
    """
    uploaded = request.files.get("csv_file")
    if not uploaded or uploaded.filename == "":
        return "Missing CSV file", 400

    try:
        raw = uploaded.read()
        # Handle simple UTF-8 / UTF-8 with BOM.
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(StringIO(text))
    except Exception:
        return "Invalid CSV file", 400

    rows_for_report = []

    # Only process the first 5 data rows to save LLM calls.
    for idx, row in enumerate(reader, start=1):
        if idx > 5:
            break

        title = (row.get("Title") or "").strip()
        company_name = (row.get("Company Name") or "").strip()

        # Preserve any existing values, but typically these are blank in the template.
        first_name = (row.get("First Name") or "").strip()
        last_name = (row.get("Last Name") or "").strip()
        source_val = (row.get("Source") or "").strip()

        # If either key field is missing, just carry the row through unchanged.
        if not title or not company_name:
            rows_for_report.append(
                {
                    "Title": title,
                    "Company Name": company_name,
                    "First Name": first_name,
                    "Last Name": last_name,
                    "Source": source_val,
                }
            )
            continue

        try:
            result = run_lookup(company=company_name, role=title)
            first_name = (result.get("first_name") or "").strip()
            last_name = (result.get("last_name") or "").strip()

            primary = (result.get("primary_source") or "").strip()
            validation_sources = result.get("validation_sources") or []
            first_validation = ""
            if validation_sources:
                first_validation = (validation_sources[0] or "").strip()

            source_val = primary or first_validation or source_val
        except Exception as exc:  # noqa: B902
            # On failure, surface an inline note in the Source column
            source_val = f"Lookup error: {exc}"

        rows_for_report.append(
            {
                "Title": title,
                "Company Name": company_name,
                "First Name": first_name,
                "Last Name": last_name,
                "Source": source_val,
            }
        )

    # Build an enriched CSV alongside the PDF.
    fieldnames = ["Title", "Company Name", "First Name", "Last Name", "Source"]
    csv_buffer = StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows_for_report:
        writer.writerow(
            {
                "Title": row.get("Title", ""),
                "Company Name": row.get("Company Name", ""),
                "First Name": row.get("First Name", ""),
                "Last Name": row.get("Last Name", ""),
                "Source": row.get("Source", ""),
            }
        )
    csv_bytes = csv_buffer.getvalue().encode("utf-8-sig")

    token = uuid.uuid4().hex
    _BATCH_CSV_DOWNLOADS[token] = csv_bytes

    download_url = url_for("csv_download", token=token, _external=True)
    pdf_bytes = generate_batch_csv_pdf(rows_for_report, download_url=download_url)

    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=False,
        download_name="role_scout_batch_report.pdf",
    )


@app.route("/csv-download/<token>", methods=["GET"])
def csv_download(token: str):
    csv_bytes = _BATCH_CSV_DOWNLOADS.pop(token, None)
    if not csv_bytes:
        return "CSV download not found or has expired.", 404

    return send_file(
        BytesIO(csv_bytes),
        mimetype="text/csv",
        as_attachment=True,
        download_name="role_scout_batch_report.csv",
    )


def _result_to_report_row(result: dict, title: str, company_name: str) -> dict:
    """Build a single report row from a lookup result (same shape as csv_report rows)."""
    first_name = (result.get("first_name") or "").strip()
    last_name = (result.get("last_name") or "").strip()
    primary = (result.get("primary_source") or "").strip()
    validation_sources = result.get("validation_sources") or []
    first_validation = (validation_sources[0] or "").strip() if validation_sources else ""
    source_val = primary or first_validation
    return {
        "Title": title,
        "Company Name": company_name,
        "First Name": first_name,
        "Last Name": last_name,
        "Source": source_val,
    }


@app.route("/batch-report-pdf", methods=["POST"])
def batch_report_pdf():
    """
    Accept a JSON body with pre-computed lookup results, build the batch report
    and CSV, store both by token, return tokens so the client can open the PDF
    when ready (same-page flow).
    Body: { "results": [ { "title": "...", "company_name": "...", "result": { ... } }, ... ] }
    """
    data = request.get_json(silent=True) or {}
    items = data.get("results") or []
    if not items:
        return jsonify({"error": "Missing or empty 'results' array."}), 400

    rows_for_report = []
    for item in items:
        title = (item.get("title") or "").strip()
        company_name = (item.get("company_name") or "").strip()
        result = item.get("result")
        if not result:
            rows_for_report.append({
                "Title": title,
                "Company Name": company_name,
                "First Name": "",
                "Last Name": "",
                "Source": item.get("error") or "No result",
            })
            continue
        if isinstance(result, dict) and result.get("error"):
            rows_for_report.append({
                "Title": title,
                "Company Name": company_name,
                "First Name": "",
                "Last Name": "",
                "Source": result.get("detail") or result.get("error") or "Lookup failed",
            })
            continue
        rows_for_report.append(_result_to_report_row(result, title, company_name))

    fieldnames = ["Title", "Company Name", "First Name", "Last Name", "Source"]
    csv_buffer = StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows_for_report:
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    csv_bytes = csv_buffer.getvalue().encode("utf-8-sig")

    csv_token = uuid.uuid4().hex
    _BATCH_CSV_DOWNLOADS[csv_token] = csv_bytes

    download_url = url_for("csv_download", token=csv_token, _external=True)
    pdf_bytes = generate_batch_csv_pdf(rows_for_report, download_url=download_url)

    pdf_token = uuid.uuid4().hex
    _BATCH_PDF_DOWNLOADS[pdf_token] = pdf_bytes

    return jsonify({"pdf_token": pdf_token, "csv_token": csv_token})


@app.route("/pdf-download/<token>", methods=["GET"])
def pdf_download(token: str):
    pdf_bytes = _BATCH_PDF_DOWNLOADS.pop(token, None)
    if not pdf_bytes:
        return "Report not found or has expired.", 404
    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=False,
        download_name="role_scout_batch_report.pdf",
    )


if __name__ == "__main__":
    # Development entrypoint:
    #   python app.py
    app.run(host="0.0.0.0", port=8000, debug=True)

