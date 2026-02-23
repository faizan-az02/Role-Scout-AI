import tldextract
from duckduckgo_search import DDGS

# -----------------------------
# Source Credibility Weights
# -----------------------------

CREDIBILITY_SCORES = {
    "official": 0.40,
    "wikipedia": 0.25,
    "news": 0.20,
    "linkedin": 0.10,
    "other": 0.05,
}

NEWS_DOMAINS = [
    "bbc.com",
    "reuters.com",
    "forbes.com",
    "cnn.com",
    "nytimes.com",
    "bloomberg.com"
]

# -----------------------------
# Utility: Extract Root Domain
# -----------------------------

def get_root_domain(url: str):
    """
    Extracts root domain from URL.
    Example:
        https://about.meta.com/xyz -> meta.com
        https://news.bbc.co.uk -> bbc.co.uk
    """
    ext = tldextract.extract(url)
    if ext.domain and ext.suffix:
        return f"{ext.domain}.{ext.suffix}"
    return None


# -----------------------------
# Step 1: Discover Official Domain
# -----------------------------

def discover_official_domain(company_name: str):
    """
    Searches for official company website and returns root domain.
    """
    query = f"{company_name} official website"
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=5)
        for r in results:
            url = r.get("href")
            if url:
                root = get_root_domain(url)
                if root:
                    return root
    return None


# -----------------------------
# Step 2: Classify Source Properly
# -----------------------------

def classify_source(url: str, official_domain: str):
    root = get_root_domain(url)

    if not root:
        return "other"

    if official_domain and root == official_domain:
        return "official"

    if "wikipedia.org" in root:
        return "wikipedia"

    if "linkedin.com" in root:
        return "linkedin"

    if any(news in root for news in NEWS_DOMAINS):
        return "news"

    return "other"


# -----------------------------
# Step 3: Confidence Calculation
# -----------------------------

def calculate_confidence(
    urls,
    company_name: str,
    title_match: bool = True,
    company_match: bool = True
):
    """
    Calculates deterministic confidence score.
    """

    score = 0.0
    unique_domains = set()

    official_domain = discover_official_domain(company_name)

    for url in urls:
        source_type = classify_source(url, official_domain)
        score += CREDIBILITY_SCORES[source_type]

        root = get_root_domain(url)
        if root:
            unique_domains.add(root)

    # Cross-source bonus
    if len(unique_domains) > 1:
        cross_bonus = min(0.30, 0.10 * (len(unique_domains) - 1))
        score += cross_bonus

    # Title bonus
    if title_match:
        score += 0.10

    # Company match bonus
    if company_match:
        score += 0.10

    return min(1.0, round(score, 2))