"""
Server-side input validation for the search term.

This is the authoritative security boundary (OWASP Proactive Control C3:
Validate All Input). The frontend performs the same checks purely for
usability (immediate feedback) - it must never be trusted on its own,
since it is trivially bypassable by anyone calling the endpoint directly.

No unicode handling is required: only plain ASCII letters, digits and
spaces are accepted.
"""
import re

MIN_LENGTH = 1
MAX_LENGTH = 100

# Positive (allow-list) validation - OWASP C3 recommends allow-list over
# deny-list matching wherever the valid input shape is known in advance.
# This is the actual control that stops SQL Injection / XSS payloads: none
# of the characters they depend on (<, >, ', ", ;, --, =, /* ... */) are
# permitted.
ALLOWED_PATTERN = re.compile(r"^[A-Za-z0-9 ]+$")

# Deny-list signatures for common attack payloads. Redundant with the
# allow-list above by design (defense in depth) - kept only so a rejected
# request can be classified and reported with a clearer reason.
SQLI_PATTERN = re.compile(
    r"(--|;|/\*|\*/|'|\"|\bunion\b|\bselect\b|\binsert\b|\bupdate\b|"
    r"\bdelete\b|\bdrop\b|\bexec\b|\bxp_\w+|\bor\b\s+\d+\s*=\s*\d+)",
    re.IGNORECASE,
)
XSS_PATTERN = re.compile(
    r"(<\s*script|</\s*script|javascript:|on\w+\s*=|<\s*img|<\s*svg|"
    r"<\s*iframe|<[^>]+>)",
    re.IGNORECASE,
)


def validate_search_term(term):
    """Validate a search term.

    Returns (is_valid: bool, error_message: str).
    """
    if term is None:
        return False, "Search term is required."

    term = term.strip()

    if len(term) < MIN_LENGTH:
        return False, f"Search term must be at least {MIN_LENGTH} character(s) long."

    if len(term) > MAX_LENGTH:
        return False, f"Search term must not exceed {MAX_LENGTH} characters."

    if SQLI_PATTERN.search(term):
        return False, "Input rejected: potential SQL Injection attack detected."

    if XSS_PATTERN.search(term):
        return False, "Input rejected: potential XSS attack detected."

    if not ALLOWED_PATTERN.fullmatch(term):
        return False, "Only letters, numbers and spaces are allowed."

    return True, ""
