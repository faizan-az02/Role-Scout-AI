from crewai import Agent
from config import get_llm
from tools.search_tool import duckduckgo_search_tool


def create_researcher():
    return Agent(
        role="OSINT Research Specialist",
        goal="Discover the full name of the person holding a specific role in a given company using smart query generation and public sources.",
        backstory=(
            "You are an expert in open-source intelligence gathering. "
            "You MUST ONLY use the 'duck_duck_go_search' tool for web searches. "
            "Do NOT attempt to call any other tools such as brave_search or browser.search. "
            "Extract relevant person names from public sources."
        ),
        llm=get_llm(),
        tools=[duckduckgo_search_tool],
        verbose=True
    )