import re
from typing import Dict, Any, Optional
from .date_parser import parse_natural_date

PRIORITY_MAP = {
    "high": "High",
    "urgent": "High",
    "critical": "High",
    "asap": "High",
    "important": "High",
    "top priority": "High",
    "medium": "Medium",
    "med": "Medium",
    "normal": "Medium",
    "moderate": "Medium",
    "standard": "Medium",
    "low": "Low",
    "minor": "Low",
    "whenever": "Low",
    "low priority": "Low",
}

STATUS_MAP = {
    "completed": "Completed",
    "complete": "Completed",
    "done": "Completed",
    "finished": "Completed",
    "pending": "Pending",
    "open": "Pending",
    "todo": "Pending",
    "to do": "Pending",
    "not started": "Pending",
    "in_progress": "Pending",
    "in progress": "Pending",
    "in-progress": "Pending",
    "started": "Pending",
    "working on": "Pending",
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

ACRONYMS = {"ai": "AI", "ml": "ML", "ui": "UI", "ux": "UX", "api": "API", "devops": "DevOps"}

DATE_PATTERN = (
    r"\d{4}-\d{2}-\d{2}|"
    r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}(?:,?\s*\d{4})?|"
    r"\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*(?:\s+\d{4})?|"
    r"today|tonight|tomorrow|yesterday|next\s+week|in\s+\d+\s+days?|"
    r"(?:next\s+|this\s+)?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
)

DATE_REGEX = re.compile(rf"\b(?:{DATE_PATTERN})\b", re.IGNORECASE)

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

def normalize_category(raw_category: Optional[str]) -> Optional[str]:
    if not raw_category:
        return None
    val = raw_category.strip()
    # Strip leading 'the ' or trailing ' category' if part of a longer phrase
    val = re.sub(r"^the\s+", "", val, flags=re.IGNORECASE).strip()
    if len(val.split()) > 1:
        val = re.sub(r"\s+(category|project|tag)$", "", val, flags=re.IGNORECASE).strip()

    val_lower = val.lower()
    if val_lower in ACRONYMS:
        return ACRONYMS[val_lower]
    if val_lower in ("category", "general", ""):
        return "General"

    return val.title()

def extract_task_id(raw_val: Optional[Any] = None, raw_text: Optional[str] = None) -> Optional[Any]:
    """
    Extract either an explicit integer ID or an ordinal reference ('first', 'last', 'previous').
    Protects against false positives from dates (e.g. 2026-12-01 or Nov 15).
    """
    if raw_val is not None:
        raw_str = str(raw_val).strip().lower()
        digits = re.findall(r"\d+", raw_str)
        if digits:
            return int(digits[0])
        for k, v in ORDINAL_MAP.items():
            if k in raw_str:
                return v

    if raw_text:
        # Strip date patterns to avoid false positives (e.g. 2026-12-01 or Nov 15)
        stripped = DATE_REGEX.sub(" ", raw_text)
        # Match task 5, task #5, task id 5, id 5, #5
        m = re.search(r"\b(?:task\s+(?:id\s+)?#?|id\s+#?|#)(\d+)\b", stripped, re.IGNORECASE)
        if m:
            return int(m.group(1))

    return None

def extract_priority(raw_priority: Optional[str] = None, raw_text: Optional[str] = None) -> Optional[str]:
    if raw_priority:
        norm = normalize_priority(raw_priority)
        if norm:
            return norm
    if raw_text:
        m_clause = re.search(
            r"\b(?:priority\s+(?:to\s+|is\s+)?|(?:with\s+)?)(top\s+priority|urgent|critical|asap|important|high|medium|normal|moderate|standard|med|low|minor|whenever)(?:\s+priority)?\b",
            raw_text,
            re.IGNORECASE
        )
        if m_clause:
            val = m_clause.group(1).lower().strip()
            if val in PRIORITY_MAP:
                return PRIORITY_MAP[val]
        for k, v in PRIORITY_MAP.items():
            if re.search(rf"\b{re.escape(k)}\b", raw_text, re.IGNORECASE):
                return v
    return None

def extract_status(raw_status: Optional[str] = None, raw_text: Optional[str] = None) -> Optional[str]:
    if raw_status:
        norm = normalize_status(raw_status)
        if norm:
            return norm
    if raw_text:
        m_clause = re.search(
            r"\b(?:(?:mark|set)\s+(?:task\s+)?(?:#?\d+\s+)?(?:as\s+|to\s+)|status\s+(?:to\s+|is\s+)?|(?:as|to)\s+)(completed|complete|done|finished|in\s+progress|in-progress|started|working\s+on|pending|todo|to\s+do|open|not\s+started)\b",
            raw_text,
            re.IGNORECASE
        )
        if m_clause:
            val = m_clause.group(1).lower().strip()
            return STATUS_MAP.get(val)
        for k, v in STATUS_MAP.items():
            if re.search(rf"\b{re.escape(k)}\b", raw_text, re.IGNORECASE):
                return v
    return None

def extract_date(raw_date: Optional[str] = None, raw_text: Optional[str] = None) -> Optional[str]:
    if raw_date:
        parsed = parse_natural_date(raw_date)
        if parsed:
            return parsed
    if raw_text:
        m_pref = re.search(r"\b(?:due(?:\s+date)?(?:\s+on)?|by|before|on)\s+(" + DATE_PATTERN + r")\b", raw_text, re.IGNORECASE)
        if m_pref:
            parsed = parse_natural_date(m_pref.group(1))
            if parsed:
                return parsed
        m_direct = DATE_REGEX.search(raw_text)
        if m_direct:
            parsed = parse_natural_date(m_direct.group(0))
            if parsed:
                return parsed
    return None

def extract_category(raw_category: Optional[str] = None, raw_text: Optional[str] = None) -> Optional[str]:
    if raw_category:
        norm = normalize_category(raw_category)
        if norm:
            return norm
    if raw_text:
        m = re.search(r"\b(?:category\s+(?:to\s+|is\s+)?|in\s+(?:the\s+)?(?:category\s+)?)([\w\-]+)(?:\s+category)?\b", raw_text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if val.lower() not in ("task", "high", "medium", "low", "urgent", "completed", "pending", "the", "a"):
                return normalize_category(val)
    return None

REFERENCE_PHRASE_PATTERN = re.compile(
    r"^(?:"
    r"it|its|"
    r"tasks?|"
    r"(?:that|this|the|a|an)\s+tasks?(?:'s)?|"
    r"(?:that|this)\s+one|"
    r"that|this|one|"
    r"(?:the\s+)?previous\s+task(?:'s)?|"
    r"(?:the\s+)?prior\s+task(?:'s)?|"
    r"(?:the\s+)?last\s+task(?:'s)?|"
    r"(?:the\s+)?latest\s+task(?:'s)?|"
    r"(?:the\s+)?first\s+task(?:'s)?|"
    r"(?:the\s+)?1st\s+task(?:'s)?|"
    r"it\s+(?:as\s+)?(?:completed|complete|done|pending)|"
    r"(?:that|this|the)\s+(?:task|one)\s+(?:as\s+)?(?:completed|complete|done|pending)"
    r")$",
    re.IGNORECASE
)

STATUS_METADATA_PATTERN = re.compile(
    r"^(?:status\s+(?:to\s+|is\s+)?|as\s+|to\s+)?(?:completed|complete|done|finished|pending|in\s+progress)$",
    re.IGNORECASE
)

PRIORITY_METADATA_PATTERN = re.compile(
    r"^(?:priority\s+(?:to\s+|is\s+)?|with\s+)?(?:high|urgent|critical|asap|medium|normal|low|minor|top)(?:\s+priority)?$",
    re.IGNORECASE
)

CATEGORY_METADATA_PATTERN = re.compile(
    r"^(?:category\s+(?:to\s+|is\s+)?|in\s+(?:the\s+)?category\s+)[\w\-]+$",
    re.IGNORECASE
)

class EntityExtractorNormalizer:
    """
    Deterministic Entity Extraction and Normalization Layer.
    Merges NER-proposed entities with deterministic rule-based extractions from raw text,
    normalizing all values into canonical schema formats before validation.
    """
    @classmethod
    def extract_and_normalize(
        cls,
        raw_text: str,
        intent: str,
        ner_entities: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        entities: Dict[str, Any] = dict(ner_entities or {})
        text = re.sub(r"[.?!]+$", "", (raw_text or "").strip()).strip()

        # 1. Normalize existing NER entities
        if "priority" in entities and entities["priority"]:
            entities["priority"] = normalize_priority(entities["priority"])
        if "status" in entities and entities["status"]:
            entities["status"] = normalize_status(entities["status"])
        if "category" in entities and entities["category"]:
            entities["category"] = normalize_category(entities["category"])
        if "deadline" in entities and entities["deadline"]:
            d_norm = parse_natural_date(entities["deadline"])
            if d_norm:
                entities["deadline"] = d_norm
                entities["due_date"] = d_norm
        if "due_date" in entities and entities["due_date"]:
            d_norm = parse_natural_date(entities["due_date"])
            if d_norm:
                entities["deadline"] = d_norm
                entities["due_date"] = d_norm
        if "task_id" in entities and entities["task_id"]:
            tid = extract_task_id(entities["task_id"])
            if tid is not None:
                entities["task_id"] = tid

        # 2. Extract quotes
        quotes = re.findall(r'["\']([^"\']+)["\']', text)

        # 3. Rename Commands (new_title & title)
        if intent == "UPDATE_TASK" and re.search(r"\b(rename|change title|update title)\b", text, re.IGNORECASE):
            # Pattern A: Rename task <id> to "<new_title>" or to <new_title>
            m_id_rename = re.search(
                r"\b(?:rename|change title of|update title of)\s+task\s+(?:#?(\d+)|id\s+(\d+))\s+to\s+['\"]?([^'\"]+?)['\"]?$",
                text,
                re.IGNORECASE
            )
            if m_id_rename:
                tid = int(m_id_rename.group(1) or m_id_rename.group(2))
                new_title = m_id_rename.group(3).strip()
                entities["task_id"] = tid
                entities["new_title"] = new_title
                entities["title"] = new_title
            # Pattern B: Rename task "Old Title" to "New Title"
            elif len(quotes) >= 2:
                entities["title"] = quotes[0].strip()
                entities["new_title"] = quotes[1].strip()
            else:
                m_title_rename = re.search(
                    r"\b(?:rename|change title of)\s+task\s+['\"]?(.+?)['\"]?\s+to\s+['\"]?([^'\"]+?)['\"]?$",
                    text,
                    re.IGNORECASE
                )
                if m_title_rename:
                    entities["title"] = m_title_rename.group(1).strip()
                    entities["new_title"] = m_title_rename.group(2).strip()

        # 4. Deterministic Task ID Fallback
        if "task_id" not in entities or entities["task_id"] is None:
            tid = extract_task_id(raw_text=text)
            if tid is not None:
                entities["task_id"] = tid

        # 5. Deterministic Priority Fallback
        if "priority" not in entities or entities["priority"] is None:
            p = extract_priority(raw_text=text)
            if p:
                entities["priority"] = p

        # 6. Deterministic Status Fallback
        if "status" not in entities or entities["status"] is None:
            s = extract_status(raw_text=text)
            if s:
                entities["status"] = s

        # 7. Deterministic Due Date / Deadline Fallback
        if "deadline" not in entities and "due_date" not in entities:
            d = extract_date(raw_text=text)
            if d:
                entities["deadline"] = d
                entities["due_date"] = d

        # 8. Deterministic Category Fallback
        if "category" not in entities or entities["category"] is None:
            c = extract_category(raw_text=text)
            if c:
                entities["category"] = c

        # 9. Deterministic Title Fallback (for CREATE_TASK, GET_TASK, DELETE_TASK, UPDATE_TASK)
        det_title = None
        if quotes:
            det_title = quotes[0].strip()
        else:
            # Check for "Set priority of task <title> to <priority>"
            m_set_p = re.search(
                r"\b(?:set|change|update)\s+priority\s+of\s+task\s+(.+?)\s+to\s+(?:high|urgent|critical|asap|medium|normal|moderate|standard|low|minor)\b",
                text,
                re.IGNORECASE
            )
            if m_set_p:
                det_title = m_set_p.group(1).strip()
            else:
                remainder = text
                leading_patterns = [
                    r"^\s*(?:create|add|schedule|set\s+up)\s+(?:a\s+|an\s+)?(?:new\s+)?(?:task\b)?\s*(?:to\s+|called\s+|named\s+|titled\s+)?",
                    r"^\s*remind\s+me\s+to\s+",
                    r"^\s*(?:new\s+task|task)\s+(?:to\s+|called\s+|named\s+|titled\s+)?",
                    r"^\s*(?:show|find|get|view|display|fetch)\s+(?:the\s+|that\s+|this\s+)?(?:task\b|one\b)?\s*(?:called\s+|named\s+|titled\s+)?",
                    r"^\s*(?:delete|remove|cancel|drop)\s+(?:the\s+|that\s+|this\s+)?(?:task\b|one\b)?\s*(?:called\s+|named\s+|titled\s+)?",
                    r"^\s*(?:update|modify|edit|change)\s+(?:the\s+|that\s+|this\s+)?(?:task\b|one\b)?\s*(?:called\s+|named\s+|titled\s+)?",
                    r"^\s*(?:mark|set)\s+(?:the\s+|that\s+|this\s+)?(?:task\b|one\b)?\s*(?:called\s+|named\s+|titled\s+)?",
                    r"^\s*(?:complete|finish|done)\s+(?:the\s+|that\s+|this\s+)?(?:task\b|one\b)?\s*(?:called\s+|named\s+|titled\s+)?",
                ]
                for pat in leading_patterns:
                    remainder = re.sub(pat, "", remainder, flags=re.IGNORECASE).strip()

                trailing_patterns = [
                    r"(?:\s+(?:with\s+)?|^\s*(?:with\s+)?)(?:high|urgent|critical|asap|medium|normal|low|minor|top)\s+priority\b.*$",
                    r"(?:\s+priority\s+(?:to\s+|is\s+)?|^\s*priority\s+(?:to\s+|is\s+)?)(?:high|urgent|critical|medium|low|minor)\b.*$",
                    r"(?:\s+(?:due(?:\s+date)?(?:\s+on)?|by|before)\s+|^\s*(?:due(?:\s+date)?(?:\s+on)?|by|before)\s+)(" + DATE_PATTERN + r")\b.*$",
                    r"(?:\s+(?:status\s+(?:to\s+|is\s+)?|as\s+|to\s+)|^\s*(?:status\s+(?:to\s+|is\s+)?|as\s+|to\s+))(?:completed|complete|done|finished|pending|in\s+progress)\b.*$",
                    r"(?:\s+category\s+(?:to\s+|is\s+)?|^\s*category\s+(?:to\s+|is\s+)?)(?:[\w\-]+)\b.*$",
                    r"(?:\s+in\s+(?:the\s+)?|^\s*in\s+(?:the\s+)?)[\w\-]+\s+category\b.*$",
                ]
                for pat in trailing_patterns:
                    remainder = re.sub(pat, "", remainder, flags=re.IGNORECASE).strip()

                # Clean leading prepositions
                remainder = re.sub(r"^(?:to|called|named|titled|for|a|the)\s+", "", remainder, flags=re.IGNORECASE).strip()

                # If remainder is just status, priority, category metadata or reference phrase, discard it as title
                if remainder:
                    if (
                        not re.match(r"^(?:#|id\s+|task\s+|task\s+id\s+)?\d+$", remainder, re.IGNORECASE)
                        and not REFERENCE_PHRASE_PATTERN.match(remainder.strip())
                        and not STATUS_METADATA_PATTERN.match(remainder.strip())
                        and not PRIORITY_METADATA_PATTERN.match(remainder.strip())
                        and not CATEGORY_METADATA_PATTERN.match(remainder.strip())
                    ):
                        det_title = remainder

        if "title" not in entities or not entities["title"]:
            if det_title:
                entities["title"] = det_title
        elif det_title and quotes:
            entities["title"] = quotes[0].strip()
        elif det_title and "new_title" not in entities:
            curr_title = entities["title"].strip()
            # If NER truncated the title (e.g. 'prepare sprint' instead of 'prepare sprint demo'), refine it
            if curr_title.lower() in det_title.lower() and len(det_title) > len(curr_title):
                entities["title"] = det_title

        # Double check that no pronoun/reference or pure metadata was erroneously set as title
        if "title" in entities and entities["title"]:
            t_strip = entities["title"].strip()
            if (
                REFERENCE_PHRASE_PATTERN.match(t_strip)
                or STATUS_METADATA_PATTERN.match(t_strip)
                or PRIORITY_METADATA_PATTERN.match(t_strip)
                or CATEGORY_METADATA_PATTERN.match(t_strip)
            ):
                entities["title"] = None

        return entities

def normalize_entities(raw_entities: Dict[str, Any]) -> Dict[str, Any]:
    """
    Backwards-compatible entity normalization function.
    """
    normalized: Dict[str, Any] = {}

    if "title" in raw_entities and raw_entities["title"]:
        title_val = raw_entities["title"].strip()
        title_val = re.sub(r"^(to|for|a|the)\s+", "", title_val, flags=re.IGNORECASE).strip()
        if title_val and not REFERENCE_PHRASE_PATTERN.match(title_val):
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
            normalized["due_date"] = parsed_d

    if "due_date" in raw_entities and raw_entities["due_date"]:
        parsed_d = parse_natural_date(raw_entities["due_date"])
        if parsed_d:
            normalized["deadline"] = parsed_d
            normalized["due_date"] = parsed_d

    if "task_id" in raw_entities and raw_entities["task_id"]:
        extracted_id = extract_task_id(raw_entities["task_id"])
        if extracted_id is not None:
            normalized["task_id"] = extracted_id

    if "new_title" in raw_entities and raw_entities["new_title"]:
        normalized["new_title"] = raw_entities["new_title"].strip()

    return normalized
