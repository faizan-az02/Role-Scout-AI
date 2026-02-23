# tools/alias.py

ROLE_ALIASES = {
    "ceo": [
        "ceo",
        "chief executive officer",
        "president and ceo",
        "chief exec officer"
    ],
    "cto": [
        "cto",
        "chief technology officer",
        "chief technical officer"
    ],
    "cfo": [
        "cfo",
        "chief financial officer"
    ],
    "coo": [
        "coo",
        "chief operating officer"
    ],
    "founder": [
        "founder",
        "co-founder",
        "cofounder"
    ],
    "president": [
        "president",
        "president & ceo"
    ],
    "managing director": [
        "managing director",
        "md"
    ]
}


def normalize_role(role: str):
    """
    Normalize role to lowercase stripped form.
    """
    return role.strip().lower()


def title_matches(designation: str, text: str) -> bool:
    """
    Check if designation or any of its known aliases
    appear in the given text.
    """
    designation_norm = normalize_role(designation)
    text_lower = text.lower()

    # Direct match first
    if designation_norm in text_lower:
        return True

    # Check alias dictionary
    aliases = ROLE_ALIASES.get(designation_norm, [])

    for alias in aliases:
        if alias in text_lower:
            return True

    return False