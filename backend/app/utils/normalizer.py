import re
from typing import Dict, Any, Optional
from .date_parser import parse_natural_date

PRIORITY_MAP = {
    "high": "High",
    "urgent": "High",
    "critical": "High",
    "important": "High",
    "medium": "Medium",
    "med": "Medium",
    "normal": "Medium",
    "moderate": "Medium",
    "low": "Low",
    "minor": "Low",
}

STATUS_MAP = {
    "completed": "Completed",
    "complete": "Completed",
    "done": "Completed",
    "finished": "Completed",
    "pending": "Pending",
    "open": "Pending",
    "todo": "Pending",
    "in_progress": "Pending",
    "in progress": "Pending",
}

ORDINAL_MAP = {
    "first": "first",
    "1st": "first",
    "second": "second",
    "2nd": "second",
    "third": "third",
    "3rd": "third",
    "previous": "previous",
    "last": "last",
    "latest": "last",
}

def normalize_priority(raw_priority: Optional[str]) -> Optional[str]:
    if not raw_priority:
        return None
    val = raw_priority.strip().lower()
    return PRIORITY_MAP.get(val, "Medium")

def normalize_status(raw_status: Optional[str]) -> Optional[str]:
    if not raw_status:
        return None
    val = raw_status.strip().lower()
    return STATUS_MAP.get(val, "Pending")

ACRONYMS = {"ai": "AI", "ml": "ML", "ui": "UI", "ux": "UX", "api": "API", "devops": "DevOps"}

def normalize_category(raw_category: Optional[str]) -> Optional[str]:
    if not raw_category:
        return None
    val = raw_category.strip()
    # Strip leading 'the ' or trailing ' category' if part of a longer phrase
    val = re.sub(r"^the\s+", "", val, flags=re.IGNORECASE).strip()
    if len(val.split()) > 1:
        val = re.sub(r"\s+category$", "", val, flags=re.IGNORECASE).strip()

    val_lower = val.lower()
    if val_lower in ACRONYMS:
        return ACRONYMS[val_lower]
    if val_lower in ("category", "general", ""):
        return "General"

    return val.title()

def extract_task_id(raw_val: Optional[str]) -> Optional[Any]:
    """
    Extract either an explicit integer ID or an ordinal reference ('first', 'last', 'previous').
    """
    if not raw_val:
        return None
    raw_str = str(raw_val).strip().lower()
    
    # Check for direct integer
    digits = re.findall(r"\d+", raw_str)
    if digits:
        return int(digits[0])

    # Check for ordinal references
    for k, v in ORDINAL_MAP.items():
        if k in raw_str:
            return v

    return None

def normalize_entities(raw_entities: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize extracted NER entities into canonical formats.
    """
    normalized: Dict[str, Any] = {}

    if "title" in raw_entities and raw_entities["title"]:
        title_val = raw_entities["title"].strip()
        # Remove leading "to ", "for ", "a " if captured
        title_val = re.sub(r"^(to|for|a|the)\s+", "", title_val, flags=re.IGNORECASE).strip()
        if title_val:
            normalized["title"] = title_val

    if "description" in raw_entities and raw_entities["description"]:
        normalized["description"] = raw_entities["description"].strip()

    if "priority" in raw_entities and raw_entities["priority"]:
        norm_p = normalize_priority(raw_entities["priority"])
        if norm_p:
            normalized["priority"] = norm_p

    if "status" in raw_entities and raw_entities["status"]:
        norm_s = normalize_status(raw_entities["status"])
        if norm_s:
            normalized["status"] = norm_s

    if "category" in raw_entities and raw_entities["category"]:
        norm_c = normalize_category(raw_entities["category"])
        if norm_c:
            normalized["category"] = norm_c

    if "deadline" in raw_entities and raw_entities["deadline"]:
        parsed_d = parse_natural_date(raw_entities["deadline"])
        if parsed_d:
            normalized["deadline"] = parsed_d

    if "task_id" in raw_entities and raw_entities["task_id"]:
        extracted_id = extract_task_id(raw_entities["task_id"])
        if extracted_id is not None:
            normalized["task_id"] = extracted_id

    return normalized
