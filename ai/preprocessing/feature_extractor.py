from typing import List, Dict, Any, Optional

PRIORITY_KEYWORDS = {"high", "medium", "low", "urgent", "critical", "normal", "minor", "med", "moderate"}
STATUS_KEYWORDS = {"completed", "pending", "done", "finished", "open", "in_progress", "todo"}
DATE_KEYWORDS = {
    "today", "tomorrow", "tonight", "yesterday", "monday", "tuesday", "wednesday",
    "thursday", "friday", "saturday", "sunday", "week", "month", "morning", "afternoon", "evening", "night"
}
ORDINAL_KEYWORDS = {"first", "1st", "second", "2nd", "third", "3rd", "last", "previous", "latest", "next"}
TITLE_VERBS = {
    "study", "learn", "read", "prepare", "build", "write", "fix", "implement",
    "review", "revise", "clean", "design", "create", "test", "deploy", "organize",
    "call", "schedule", "inspect", "refactor", "finish", "submit", "buy", "check",
    "draft", "record", "insert", "develop", "setup", "configure"
}
CATEGORY_INDICATORS = {"category", "project", "tag", "domain", "area"}

def get_word_shape(token: str) -> str:
    shape = []
    for c in token:
        if c.isupper():
            shape.append("X")
        elif c.islower():
            shape.append("x")
        elif c.isdigit():
            shape.append("d")
        else:
            shape.append("-")
    # Collapse consecutive identical chars
    collapsed = []
    for c in shape:
        if not collapsed or collapsed[-1] != c:
            collapsed.append(c)
    return "".join(collapsed)

def token_to_features(tokens: List[str], i: int) -> Dict[str, Any]:
    """
    Extract rich classical NLP token and window features for token at index `i`.
    """
    token = tokens[i]
    token_lower = token.lower()
    
    features = {
        "bias": 1.0,
        "token.lower": token_lower,
        "token.len": len(token),
        "token.shape": get_word_shape(token),
        "token.isupper": token.isupper(),
        "token.istitle": token.istitle(),
        "token.isdigit": token.isdigit(),
        "token.is_quote": token in ("'", '"', "''", '""', "`", "“", "”", "‘", "’"),
        "token.prefix_2": token_lower[:2] if len(token) >= 2 else token_lower,
        "token.prefix_3": token_lower[:3] if len(token) >= 3 else token_lower,
        "token.suffix_2": token_lower[-2:] if len(token) >= 2 else token_lower,
        "token.suffix_3": token_lower[-3:] if len(token) >= 3 else token_lower,
        "token.is_priority_kw": token_lower in PRIORITY_KEYWORDS,
        "token.is_status_kw": token_lower in STATUS_KEYWORDS,
        "token.is_date_kw": token_lower in DATE_KEYWORDS,
        "token.is_ordinal_kw": token_lower in ORDINAL_KEYWORDS,
        "token.is_title_verb": token_lower in TITLE_VERBS,
        "pos_relative": round(i / max(1, len(tokens) - 1), 2),
    }

    # Features for previous token (i - 1)
    if i > 0:
        prev_token = tokens[i - 1]
        prev_lower = prev_token.lower()
        features.update({
            "-1:token.lower": prev_lower,
            "-1:token.istitle": prev_token.istitle(),
            "-1:token.isupper": prev_token.isupper(),
            "-1:token.isdigit": prev_token.isdigit(),
            "-1:token.is_priority_kw": prev_lower in PRIORITY_KEYWORDS,
            "-1:token.is_status_kw": prev_lower in STATUS_KEYWORDS,
            "-1:token.is_date_kw": prev_lower in DATE_KEYWORDS,
            "-1:token.is_title_verb": prev_lower in TITLE_VERBS,
            "-1:token.is_quote": prev_token in ("'", '"', "`", "“", "”", "‘", "’"),
            "-1:token.is_to": prev_lower == "to",
            "-1:token.is_for": prev_lower == "for",
            "-1:token.is_called": prev_lower in ("called", "named", "titled"),
            "-1:token.is_category": prev_lower in CATEGORY_INDICATORS,
            "-1:token.is_priority": prev_lower in ("priority", "prio"),
            "-1:token.is_status": prev_lower == "status",
            "-1:token.is_deadline": prev_lower in ("deadline", "due", "by"),
            "-1:token.is_and": prev_lower in ("and", "&", ","),
            "bigram:-1+0": f"{prev_lower}_{token_lower}",
        })
    else:
        features["BOS"] = True

    # Features for two tokens prior (i - 2)
    if i > 1:
        prev2_token = tokens[i - 2]
        prev2_lower = prev2_token.lower()
        features.update({
            "-2:token.lower": prev2_lower,
            "-2:token.is_category": prev2_lower in CATEGORY_INDICATORS,
            "-2:token.is_priority": prev2_lower in ("priority", "prio"),
            "-2:token.is_status": prev2_lower == "status",
            "-2:token.is_deadline": prev2_lower in ("deadline", "due"),
            "-2:token.is_task": prev2_lower == "task",
            "-2:token.is_called": prev2_lower in ("called", "named", "titled"),
            "-2:token.is_quote": prev2_token in ("'", '"', "`", "“", "”", "‘", "’"),
            "trigram:-2+-1+0": f"{prev2_lower}_{tokens[i-1].lower()}_{token_lower}",
        })

    # Features for three tokens prior (i - 3)
    if i > 2:
        prev3_lower = tokens[i - 3].lower()
        features["-3:token.lower"] = prev3_lower
        features["-3:token.is_category"] = prev3_lower in CATEGORY_INDICATORS

    # Features for next token (i + 1)
    if i < len(tokens) - 1:
        next_token = tokens[i + 1]
        next_lower = next_token.lower()
        features.update({
            "+1:token.lower": next_lower,
            "+1:token.istitle": next_token.istitle(),
            "+1:token.isupper": next_token.isupper(),
            "+1:token.isdigit": next_token.isdigit(),
            "+1:token.is_priority_kw": next_lower in PRIORITY_KEYWORDS,
            "+1:token.is_status_kw": next_lower in STATUS_KEYWORDS,
            "+1:token.is_date_kw": next_lower in DATE_KEYWORDS,
            "+1:token.is_category": next_lower in CATEGORY_INDICATORS,
            "+1:token.is_priority": next_lower in ("priority", "prio"),
            "+1:token.is_quote": next_token in ("'", '"', "`", "“", "”", "‘", "’"),
            "+1:token.is_with": next_lower == "with",
            "+1:token.is_in": next_lower in ("in", "for", "under"),
            "+1:token.is_and": next_lower in ("and", "&", ","),
            "bigram:0++1": f"{token_lower}_{next_lower}",
        })
    else:
        features["EOS"] = True

    # Features for two tokens ahead (i + 2)
    if i < len(tokens) - 2:
        next2_token = tokens[i + 2]
        next2_lower = next2_token.lower()
        features.update({
            "+2:token.lower": next2_lower,
            "+2:token.is_category": next2_lower in CATEGORY_INDICATORS,
            "+2:token.is_priority": next2_lower in ("priority", "prio"),
            "+2:token.is_priority_kw": next2_lower in PRIORITY_KEYWORDS,
            "trigram:0++1++2": f"{token_lower}_{tokens[i+1].lower()}_{next2_lower}",
        })

    return features

def sentence_to_features(tokens: List[str]) -> List[Dict[str, Any]]:
    """Convert a sequence of tokens into a list of feature dictionaries."""
    return [token_to_features(tokens, i) for i in range(len(tokens))]
