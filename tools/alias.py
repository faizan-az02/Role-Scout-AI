# tools/alias.py

import re

# Core role families
C_LEVEL_MAP = {
    "ceo": "chief executive officer",
    "cto": "chief technology officer",
    "cfo": "chief financial officer",
    "coo": "chief operating officer",
    "cmo": "chief marketing officer",
    "cio": "chief information officer"
}

SENIORITY_KEYWORDS = [
    "chief",
    "head",
    "director",
    "manager",
    "lead",
    "owner",
    "founder",
    "co-founder",
    "president",
    "partner",
    "officer"
]


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[|,&]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def expand_c_level(designation: str):
    designation = designation.lower().strip()

    if designation in C_LEVEL_MAP:
        return [designation, C_LEVEL_MAP[designation]]

    # handle cases like "CEO & Founder"
    expanded = []
    words = designation.split()

    for word in words:
        if word in C_LEVEL_MAP:
            expanded.append(C_LEVEL_MAP[word])
            expanded.append(word)

    return expanded


def split_compound_title(designation: str):
    designation = normalize_text(designation)

    # Split by common separators
    parts = re.split(r" and | & |,|/", designation)
    return [p.strip() for p in parts if p.strip()]


def title_matches(designation: str, text: str) -> bool:
    text = normalize_text(text)
    designation = normalize_text(designation)

    # 1️⃣ Direct match
    if designation in text:
        return True

    # 2️⃣ Compound role handling
    parts = split_compound_title(designation)

    for part in parts:
        if part in text:
            return True

    # 3️⃣ C-level expansion
    expanded = expand_c_level(designation)
    for variant in expanded:
        if variant in text:
            return True

    # 4️⃣ Seniority fallback check
    for keyword in SENIORITY_KEYWORDS:
        if keyword in designation and keyword in text:
            return True

    return False