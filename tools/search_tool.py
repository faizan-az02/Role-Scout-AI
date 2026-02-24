from crewai.tools import tool
from ddgs import DDGS

@tool("DuckDuckGo Search")
def duckduckgo_search_tool(query: str) -> str:
    """
    Performs a DuckDuckGo search and returns top 5 results.
    """
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=5):
            results.append(
                f"Title: {r['title']}\n"
                f"Snippet: {r['body']}\n"
                f"URL: {r['href']}\n"
            )
    return "\n".join(results)