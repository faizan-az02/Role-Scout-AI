from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, List

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


def generate_batch_csv_pdf(rows: List[Dict[str, Any]], download_url: str | None = None) -> bytes:
  """
  Generate a PDF summarising a batch CSV lookup.

  Each row is expected to have:
    Title, Company Name, First Name, Last Name, Source
  """
  buffer = BytesIO()
  c = canvas.Canvas(buffer, pagesize=LETTER)
  width, height = LETTER

  c.setTitle("Role Scout AI CSV Batch Report")

  margin_x = 40
  top_y = height - 60
  y = top_y

  def draw_page_header() -> None:
    nonlocal y
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin_x, y, "Role Scout AI – CSV Batch Report")
    y -= 24
    c.setFont("Helvetica", 10)
    c.drawString(margin_x, y, f"Total rows in this report: {len(rows)}")
    y -= 14
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(margin_x, y, "Only the first 5 rows of the uploaded CSV are processed to limit LLM and API usage.")
    y -= 24
    c.setFont("Helvetica-Bold", 9)
    # Table headers
    c.drawString(margin_x + 0, y, "Title")
    c.drawString(margin_x + 140, y, "Company")
    c.drawString(margin_x + 280, y, "First")
    c.drawString(margin_x + 340, y, "Last")
    c.drawString(margin_x + 400, y, "Source")
    y -= 14
    c.setFont("Helvetica", 8)

  def truncate(text: str, max_len: int = 80) -> str:
    text = text or ""
    if len(text) <= max_len:
      return text
    return text[: max_len - 1] + "…"

  draw_page_header()

  for row in rows:
    if y < 60:
      c.showPage()
      y = top_y
      draw_page_header()

    title = truncate(str(row.get("Title") or ""))
    company = truncate(str(row.get("Company Name") or ""), 40)
    first = truncate(str(row.get("First Name") or ""), 24)
    last = truncate(str(row.get("Last Name") or ""), 24)
    source = truncate(str(row.get("Source") or ""), 80)

    c.drawString(margin_x + 0, y, title)
    c.drawString(margin_x + 140, y, company)
    c.drawString(margin_x + 280, y, first)
    c.drawString(margin_x + 340, y, last)
    c.drawString(margin_x + 400, y, source)
    y -= 12

  if download_url:
    if y < 80:
      c.showPage()
      y = top_y
      draw_page_header()

    y -= 6
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin_x, y, "Link to CSV")
    y -= 14
    c.setFont("Helvetica", 9)
    link_text = "Download CSV Here"
    c.setFillColorRGB(0.2, 0.9, 0.8)
    c.drawString(margin_x, y, link_text)
    link_width = c.stringWidth(link_text, "Helvetica", 9)
    # Make the text clickable; link points to the CSV download URL.
    c.linkURL(download_url, (margin_x, y - 2, margin_x + link_width, y + 10), relative=0)
    c.setFillColorRGB(0, 0, 0)

  c.showPage()
  c.save()

  buffer.seek(0)
  return buffer.getvalue()

