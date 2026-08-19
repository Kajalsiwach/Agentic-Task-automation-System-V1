import re
from typing import List, Tuple, Set

# Regex that preserves words, contractions, numbers, and individual punctuation characters including quotes
TOKEN_REGEX = re.compile(r"[A-Za-z0-9_]+(?:'[A-Za-z]+)?|[^\w\s]")

def tokenize(text: str) -> List[str]:
    """
    Deterministic regex-based tokenizer that preserves alphanumerics,
    contractions/possessives (e.g., task's), quotes, and standalone punctuation.
    """
    if not text:
        return []
    tokens = TOKEN_REGEX.findall(text)
    return tokens

def clean_text(text: str) -> str:
    """Normalize whitespace and strip extraneous control characters."""
    if not text:
        return ""
    return " ".join(text.strip().split())

def find_quoted_spans(text: str) -> List[Tuple[int, int, str]]:
    """
    Extract quoted substrings (single or double quotes) with start/end character offsets.
    """
    spans = []
    for match in re.finditer(r"['\"]([^'\"]+)['\"]", text):
        spans.append((match.start(1), match.end(1), match.group(1).strip()))
    return spans
