from __future__ import annotations

"""
Lookup pipeline shared by CLI (main.py) and the Flask app.

NOTE:
- This is structurally identical to the previous lookup_service implementation.
- Business logic, prompts, retry flow, scoring, alias handling, validation,
  and cache behavior are preserved as-is.
"""

import json

from crewai import Crew, Task

from agents.researcher import create_researcher
from agents.validator import create_validator, extract_urls
from tools.cache import get_cached_result, set_cached_result
from tools.alias import title_matches
from tools.scoring import calculate_confidence


def build_error_output(message, company, designation, attempts, confidence=0.0):
    """
    Helper lifted verbatim from the original main.py.
    """
    return {
        "error": message,
        "company": company,
        "current_title": designation,
        "confidence_score": confidence,
        "attempts": attempts,
        "cache": False,
    }


def generate_query_variations(company, designation):
    """
    Helper lifted verbatim from the original main.py.
    """
    return [
        f"{designation} of {company} full name official website",
        f"{company} {designation} LinkedIn profile",
        f"{company} current {designation} news announcement",
    ]


# -----------------------
# Config
# -----------------------

max_retries = 2
threshold = 0.7


def run_lookup(company: str, role: str) -> dict:
    """
    Execute the full lookup pipeline for a given company and role.
    """
    designation = role  # Preserve original variable name used throughout the logic.

    # -----------------------
    # Cache Check
    # -----------------------
    cached = get_cached_result(company, designation)
    if cached:
        # Preserve original CLI logging behavior.
        print("\n=== FINAL STRUCTURED OUTPUT ===\n")
        print(json.dumps(cached, indent=4))
        return cached

    researcher = create_researcher()
    validator = create_validator()

    final_output = None

    # -----------------------
    # Retry Loop
    # -----------------------

    for attempt in range(max_retries + 1):
        print(f"\n===== ATTEMPT {attempt + 1} =====\n")

        # Generate query variations
        query_variations = generate_query_variations(company, designation)

        # -----------------------
        # Task 1: Research
        # -----------------------

        if attempt == 0:
            research_description = (
                f"Find the full name of the current {designation} of {company}. "
                "Use the DuckDuckGo search tool if necessary and focus on authoritative sources "
                "such as the company's official website, LinkedIn, or reputable news outlets. "
                "Return only the person's full name and one best source URL.\n\n"
            )

        elif attempt == 1:
            research_description = (
                f"Find the full name of the current {designation} of {company}. "
                "Prioritize the company's official website, Wikipedia, or major business news outlets. "
                "Avoid unofficial blogs or speculative content. "
                "Return only the most reliable source.\n\n"
            )

        else:
            research_description = (
                f"Find the full name of the current {designation} of {company}. "
                "Strictly verify using official company domain or Wikipedia. "
                "If confidence is low, indicate uncertainty.\n\n"
            )

        # Append query variations WITHOUT changing your original text
        research_description += (
            "Try the following search queries one by one using ONLY the 'duck_duck_go_search' tool:\n"
        )

        for i, query in enumerate(query_variations, 1):
            research_description += f"{i}. {query}\n"

        research_task = Task(
            description=research_description,
            expected_output="Person's full name and one best source URL.",
            agent=researcher,
            verbose=False,
            allow_delegation=False,
        )

        # -----------------------
        # Task 2: Validation
        # -----------------------

        validation_task = Task(
            description=(
                f"Validate the discovered name for the {designation} of {company}. "
                "Search again using the name, company, and role. "
                "Confirm the name appears in at least 2 credible sources.\n\n"
                "Return STRICT JSON in the following format:\n"
                "{\n"
                '  "validated": true or false,\n'
                '  "full_name": "Exact confirmed full name",\n'
                '  "confirming_urls": ["url1", "url2"],\n'
                '  "reasoning": "Short explanation"\n'
                "}\n\n"
                "Do not include any text outside the JSON."
            ),
            expected_output="Strict JSON validation result.",
            agent=validator,
            verbose=False,
            allow_delegation=False,
        )

        crew = Crew(
            agents=[researcher, validator],
            tasks=[research_task, validation_task],
            verbose=False,
        )

        try:
            crew_output = crew.kickoff()
        except Exception as e:
            error_message = str(e)

            if "ratelimit" in error_message.lower() or "429" in error_message:
                final_output = build_error_output(
                    "LLM rate limit reached",
                    company,
                    designation,
                    attempt + 1,
                )
            elif "api_key" in error_message.lower():
                final_output = build_error_output(
                    "Invalid or missing API key",
                    company,
                    designation,
                    attempt + 1,
                )
            else:
                final_output = build_error_output(
                    "System execution failure",
                    company,
                    designation,
                    attempt + 1,
                )
            break

        research_text = crew_output.tasks_output[0].raw
        validation_text = crew_output.tasks_output[1].raw

        print("\n=== RESEARCH OUTPUT ===\n", research_text)
        print("\n=== VALIDATION OUTPUT ===\n", validation_text)

        # -----------------------
        # Parse Validation JSON
        # -----------------------

        try:
            validation_json = json.loads(validation_text)
        except Exception:
            final_output = build_error_output(
                "Validation output parsing failed",
                company,
                designation,
                attempt + 1,
            )
            break

        validated = validation_json.get("validated", False)
        name = validation_json.get("full_name")
        urls = validation_json.get("confirming_urls", [])

        first_name = None
        last_name = None

        if name:
            parts = name.strip().split()
            if len(parts) >= 2:
                first_name = parts[0]
                last_name = parts[-1]

        # Primary source = first URL from research output
        primary_source = None
        research_urls = extract_urls(research_text)
        if research_urls:
            primary_source = research_urls[0]

        # -----------------------
        # Dynamic Matching
        # -----------------------

        title_match = title_matches(designation, validation_text)
        company_match = company.lower() in validation_text.lower()

        # -----------------------
        # Calculate Confidence
        # -----------------------

        confidence = calculate_confidence(
            urls=urls,
            company_name=company,
            title_match=title_match,
            company_match=company_match,
        )

        print("\nExtracted Name:", name)
        print("Extracted URLs:", urls)
        print("Confidence Score:", confidence)

        final_output = {
            "first_name": first_name,
            "last_name": last_name,
            "company": company,
            "current_title": designation,
            "primary_source": primary_source,
            "confidence_score": confidence,
            "validation_sources": urls,
            "attempts": attempt + 1,
        }

        # -----------------------
        # Stop if confidence good
        # -----------------------

        if validated:
            print("\nValidator confirmed identity. Stopping retries.")
            break

        elif confidence >= threshold:
            print("\nConfidence threshold met. Stopping retries.")
            break

        else:
            print("\nConfidence too low. Retrying...\n")

    # -----------------------
    # Graceful No Result Handling
    # -----------------------

    if not final_output:
        final_output = build_error_output(
            "No reliable result found",
            company,
            designation,
            attempt + 1,
            0,
        )

    # Mark non-cached responses explicitly
    if isinstance(final_output, dict) and "cache" not in final_output:
        final_output["cache"] = False

    # Persist successful responses to cache
    set_cached_result(company, designation, final_output)

    print("\n=== FINAL STRUCTURED OUTPUT ===\n")
    print(json.dumps(final_output, indent=4))

    return final_output

