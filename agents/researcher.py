from crewai import Agent
from config import get_llm
from tools.search_tool import duckduckgo_search_tool

def extract_name(text: str):
    # Simple heuristic: first capitalized full name
    import re
    match = re.search(r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b", text)
    if match:
        return match.group(1)
    return None

def create_researcher():
    return Agent(
        role="OSINT Research Specialist",
        goal="Discover the full name of the person holding a specific role in a given company using smart query generation and public sources.",
        backstory=(
            "You are an expert in open-source intelligence gathering. "
            "You generate intelligent search queries and extract relevant person names "
            "from publicly available sources like LinkedIn, official websites, "
            "Wikipedia, and news articles."
        ),
        llm=get_llm(),
        tools=[duckduckgo_search_tool],
        verbose=True
    )