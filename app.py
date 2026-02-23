from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, request


BASE_DIR = Path(__file__).resolve().parent

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)


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


if __name__ == "__main__":
    # Development entrypoint:
    #   python app.py
    app.run(host="0.0.0.0", port=8000, debug=True)

