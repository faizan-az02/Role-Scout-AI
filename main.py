from crewai import Task, Crew
from agents.researcher import create_researcher, extract_name
from agents.validator import create_validator, extract_urls
from tools.scoring import calculate_confidence
from tools.alias import title_matches
import json

# -----------------------
# Config
# -----------------------

max_retries = 2
threshold = 0.6

company = input("Enter the company: ")
designation = input("Enter the role: ")

researcher = create_researcher()
validator = create_validator()

final_output = None

# -----------------------
# Retry Loop
# -----------------------

for attempt in range(max_retries + 1):

    print(f"\n===== ATTEMPT {attempt + 1} =====\n")

    # -----------------------
    # Task 1: Research
    # -----------------------

    if attempt == 0:
        research_description = (
        f"Find the full name of the current {designation} of {company}. "
        "Use the DuckDuckGo search tool if necessary and focus on authoritative sources "
        "such as the company's official website, LinkedIn, or reputable news outlets. "
        "Return only the person's full name and one best source URL."
        )

    elif attempt == 1:
        research_description = (
            f"Find the full name of the current {designation} of {company}. "
            "Prioritize the company's official website, Wikipedia, or major business news outlets. "
            "Avoid unofficial blogs or speculative content. "
            "Return only the most reliable source."
            )

    else:
        research_description = (
            f"Find the full name of the current {designation} of {company}. "
            "Strictly verify using official company domain or Wikipedia. "
            "If confidence is low, indicate uncertainty."
            )

    research_task = Task(
        description=research_description,
        expected_output="Person's full name and one best source URL.",
        agent=researcher,
        verbose=False,
        allow_delegation=False
    )

    # -----------------------
    # Task 2: Validation
    # -----------------------

    validation_task = Task(
        description=(
            f"Validate the discovered name for the {designation} of {company}. "
            "Search again using the name, company, and role. "
            "Confirm the name appears in at least 2 credible sources. "
            "Return structured output including validated (true/false), "
            "list of confirming URLs, and reasoning."
        ),
        expected_output="Validation result in structured format.",
        agent=validator,
        verbose=False,
        allow_delegation=False
    )

    crew = Crew(
        agents=[researcher, validator],
        tasks=[research_task, validation_task],
        verbose=False
    )

    crew_output = crew.kickoff()

    research_text = crew_output.tasks_output[0].raw
    validation_text = crew_output.tasks_output[1].raw

    print("\n=== RESEARCH OUTPUT ===\n", research_text)
    print("\n=== VALIDATION OUTPUT ===\n", validation_text)

    # -----------------------
    # Extract Name
    # -----------------------

    name = extract_name(research_text)

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
    # Extract URLs
    # -----------------------

    urls = extract_urls(validation_text)

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
        company_match=company_match
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
        "attempts": attempt + 1
    }

    # -----------------------
    # Stop if confidence good
    # -----------------------

    if confidence >= threshold:
        print("\nConfidence threshold met. Stopping retries.")
        break
    else:
        print("\nConfidence too low. Retrying...\n")

# -----------------------
# Graceful No Result Handling
# -----------------------

if not final_output["first_name"] or final_output["confidence_score"] < threshold:
    final_output = {
        "error": "No reliable result found",
        "company": company,
        "current_title": designation,
        "confidence_score": confidence,
        "attempts": attempt + 1
    }

print("\n=== FINAL STRUCTURED OUTPUT ===\n")
print(json.dumps(final_output, indent=4))