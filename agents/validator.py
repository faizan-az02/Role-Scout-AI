from crewai import Agent
from config import get_llm
from tools.search_tool import duckduckgo_search_tool
from tools.scoring import calculate_confidence

import re


def extract_urls(text: str):
    raw_urls = re.findall(r"https?://[^\s]+", text)
    cleaned_urls = []

    for url in raw_urls:
        # Remove trailing quotes, commas, brackets
        cleaned = url.rstrip('",] )')
        cleaned_urls.append(cleaned)

    return cleaned_urls


def create_validator():
    return Agent(
        role="Source Validation Analyst",
        goal=(
            "Verify that the discovered person truly holds the given role "
            "in the specified company using multiple credible public sources."
        ),
        backstory=(
            "You are a meticulous verification analyst. "
            "You cross-check names, roles, and companies across multiple "
            "public sources such as official websites, Wikipedia, and reputable news outlets. "
            "You reject weak or single-source claims."
        ),
        tools=[duckduckgo_search_tool],
        llm=get_llm(),
        verbose=True
    )