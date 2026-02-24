## Role Scout AI – Valid Person Finder

Role Scout AI is a **CrewAI‑powered OSINT assistant** that takes a **company** and **role/title** (e.g. “Meta, CEO”) and:

- Generates smart search queries via **CrewAI agents**  
- Uses **DuckDuckGo** search to find strong public sources  
- Cross‑validates the person’s name across multiple URLs  
- Stores and serves results from a **Redis cache** for fast repeat lookups  
- Presents results in a modern web UI with **single lookups**, **CSV batch runs**, and **PDF/CSV reports**

### Video Link:
- https://drive.google.com/file/d/1cQkVhNtUNAD0sExyXUPtnvhi_QU6CXJu/view?usp=drive_link

### Tech Stack
- **CrewAI** for Orchestration and Agents
- **Redis** for Cache
- **Flask** for Web Application
- **Multiple APIs** support through .env file

### High‑level architecture

- **`main.py`**  
  - CLI entrypoint used by the web app via subprocess.  
  - Orchestrates a **CrewAI `Crew`** with two agents:
    - `Researcher` – runs DuckDuckGo queries, finds candidate names & sources.
    - `Validator` – cross‑checks the name across multiple sources and outputs strict JSON.
  - Implements a retry loop with **increasingly strict prompts** and query variations.
  - Computes a **confidence score** using `tools/scoring.py` and writes a final structured JSON result.
  - Reads/writes from **Redis** via `cache.py` to avoid re‑running expensive lookups.

- **Agents (`agents/researcher.py`, `agents/validator.py`)**
  - Wrap CrewAI `Agent` definitions with roles, goals, and tools.
  - Both agents can call the **DuckDuckGo tool** defined in `tools/search_tool.py`.

- **Tools**
  - `tools/search_tool.py` – DuckDuckGo search via `ddgs`, returns top 5 results per query.  
  - `tools/scoring.py` – classifies sources (official domain, Wikipedia, news, LinkedIn, other) and computes a **numeric confidence score** based on domain credibility and URL set.  
  - `tools/alias.py` – handles **designation aliases and decomposition**, e.g.:
    - Maps “CEO” → “Chief Executive Officer”
    - Handles compound titles like “CEO & Founder”
    - Provides `title_matches()` to check if the validated text really talks about the requested role.

- **Cache (`cache.py`)**
  - Uses **Redis** (config via `REDIS_URL`) to cache successful lookups.
  - Keys shaped as `lookup:<company>:<role>` (lower‑cased).
  - Adds `cache: true` when a response is served from cache; writes non‑error responses with a TTL.

- **Web app (`app.py`)**
  - Flask app that **adapts the existing CLI (`main.py`)** without touching its internal logic.
  - Routes:
    - `GET /` – serves the HTML UI.
    - `POST /lookup` – JSON API:
      - Calls `run_lookup(company, role)` which shells out to `python main.py` and parses the final JSON.
      - Attaches a presentation‑friendly `report` via `reporter.build_report`.
    - `POST /report` – generates a **single‑lookup PDF** using `report_pdf.generate_report_pdf`.
    - `POST /csv-report` – legacy form endpoint that still supports direct CSV→PDF if needed.
    - `POST /batch-report-pdf` – **JSON endpoint used by the CSV modal**:
      - Accepts an array of per‑row lookup results.
      - Builds a batch table of `Title, Company Name, First Name, Last Name, Source`.
      - Generates both **PDF** and **CSV**, stores them in memory under random tokens, and returns `{ pdf_token, csv_token }`.
    - `GET /csv-download/<token>` – one‑time CSV download for batch runs.
    - `GET /pdf-download/<token>` – one‑time PDF download for batch runs.

- **Presentation & reporting**
  - `reporter.py` – shapes raw lookup output into a human‑friendly report object:
    - Proper‑cases company and role for consistent display.
    - Bins confidence into **High / Medium / Low** bands with explanations.
  - `report_pdf.py` – builds **ReportLab** PDFs:
    - Single‑lookup one‑pager (headline, confidence, summary, primary + validation sources).
    - Batch CSV report:
      - Table of up to **5 rows** from the CSV batch.
      - Notice explaining only the first 5 rows were processed to limit LLM/API usage.
      - A **“Download CSV Here”** link at the end of the report.

---

### Frontend behaviour

The UI is plain HTML/CSS/JS served by Flask:

- Main form:
  - Fields: **Company**, **Role**.
  - Submit calls `POST /lookup` via `fetch` and renders:
    - Person name
    - Current title
    - Confidence score + bar
    - “Show complete info” modal with all metadata (sources, attempts, cached, etc.).
  - “View Full Report” button opens the detailed PDF in a new tab.

- CSV batch mode:
  - “Upload CSV” button below the presets, styled like the chips.
  - A **modal dialog** guides the CSV flow:
    - Shows selected file name and **total rows** detected.
    - Explains that **only the first 5 rows** are processed to conserve LLM/API calls.
    - Shows a per‑row progress bar: `1/5`, `2/5`, … `5/5` as `/lookup` is called for each pair.
  - After all 5 rows have been processed:
    - The frontend calls `POST /batch-report-pdf` with collected results.
    - The modal enables **“View Report”**, which opens the batch PDF (with a CSV download link).

---

### Data flow – single lookup

1. User submits **company** + **role** in the web UI.  
2. `app.py` → `POST /lookup`:
   - Calls `run_lookup(company, role)` which runs `main.py` as a subprocess.
3. `main.py`:
   - Checks **Redis cache**; if hit, returns cached JSON (with `cache: true`).
   - If miss:
     - Builds **query variations** from company + designation.
     - Creates a CrewAI `Crew` with **Researcher** + **Validator**.
     - Researcher uses **DuckDuckGo** via `duckduckgo_search_tool` to gather candidate names & URLs.
     - Validator checks consistency and confirms the name appears in **≥ 2 credible URLs**.
     - Uses `tools/scoring.calculate_confidence()` to produce a numeric confidence score.
   - Outputs structured JSON:
     - `first_name`, `last_name`, `company`, `current_title`, `primary_source`,  
       `validation_sources`, `confidence_score`, `attempts`, `cache`.
   - Writes successful responses into **Redis** for future reuse.
4. `app.py` attaches a **report view model** via `reporter.build_report` and returns JSON to the browser.
5. The browser updates the main card and details modal; the user can optionally open a **PDF report**.

---

### Data flow – CSV batch (first 5 rows)

1. User clicks **Upload CSV** and selects a file shaped like `test_data.csv`:

   ```text
   Title,Company Name,First Name,Last Name,Source
   Founder & CMO,SBC International Services,,,
   ...
   ```

2. The frontend:
   - Reads the CSV client‑side, counts rows, and shows the total in the modal.
   - Extracts the first **5** `Title` + `Company Name` pairs.
3. For each of those 5 rows, the browser calls **`POST /lookup`** (same as single lookup) and updates the modal progress bar (`1/5 … 5/5`).
4. When all lookups complete, the browser posts the collected results to **`POST /batch-report-pdf`**.
5. The server:
   - Converts each result into a row with `Title, Company Name, First Name, Last Name, Source`.
   - Generates:
     - A **batch PDF** table view (with a footnote about 5‑row processing).
     - A matching **CSV** of the enriched rows.
   - Stores both under random tokens and returns `{ pdf_token, csv_token }`.
6. The modal enables **View Report**; clicking it opens `/pdf-download/<pdf_token>` in a new tab.  
   The PDF itself includes a clickable **“Download CSV Here”** link pointing to `/csv-download/<csv_token>`.

---

### Setup & running locally

#### 1. Prerequisites

- Python 3.10+  
- Redis server (local or remote)  
- A virtual environment tool (`venv`, `conda`, etc.)

#### 2. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> If `requirements.txt` is missing, install at least:
> - `flask`
> - `crewai`
> - `ddgs`
> - `redis`
> - `reportlab`
> - `tldextract`

#### 3. Configure environment

Create a `.env` file (if not already present) with your LLM provider of choice and Redis URL, for example:

```bash
REDIS_URL=redis://localhost:6379/0

# Example (do NOT commit real keys)
API_KEY=your_llm_api_key
MODEL=your_model_name
BASE_URL=https://your-llm-endpoint.example.com
```

Make sure Redis is running and reachable at `REDIS_URL`.

#### 4. Run the web app

```bash
python app.py
```

Then open `http://localhost:8000` in your browser.

- Use the **Company** and **Role** fields for single lookups.
- Try **CSV batch** using `test_data.csv` to see the modal, progress, and batch PDF/CSV.

#### 5. CLI‑only mode (optional)

You can run the underlying CrewAI pipeline directly:

```bash
python main.py
```

You’ll be prompted for **company** and **role** in the terminal; the script will print the final structured JSON result.

---

### Notes & caveats

- The system relies on **public web search** and LLM reasoning; results should be treated as **best‑effort leads**, not guaranteed truth.  
- CSV batch mode deliberately processes **only the first 5 data rows** to keep LLM/API usage modest.  
- Caching via Redis lets repeated company/role lookups return instantly without re‑hitting the LLM.

