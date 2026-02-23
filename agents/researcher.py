from crewai import Agent
from config import get_llm

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
        verbose=True
    )