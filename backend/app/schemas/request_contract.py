import re
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class RequestFilters(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    search: Optional[str] = None

class StructuredRequest(BaseModel):
    """
    Centralized, validated internal representation of every user request.
    Created before planning and execution to guarantee deterministic validation.
    """
    intent: str
    confidence: float = Field(default=0.0)
    raw_query: str = Field(default="")
    entities: Dict[str, Any] = Field(default_factory=dict)
    task_id: Optional[int] = None
    task_title: Optional[str] = None
    new_title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    deadline: Optional[str] = None
    status: Optional[str] = None
    filters: Optional[RequestFilters] = None
    context_reference: Optional[str] = None
    is_valid: bool = True
    missing_fields: List[str] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    requires_confirmation: bool = False
    error_type: Optional[str] = None

CONTEXT_PRONOUN_PATTERN = re.compile(r"\b(it|its|this task|that task|the task|that one|this one|that|this)\b", re.IGNORECASE)
CONTEXT_ORDINAL_PATTERN = re.compile(r"\b(first|1st|last|latest|previous|prior)\b", re.IGNORECASE)
STATUS_QUERY_PATTERN = re.compile(r"\b(pending|completed|done|finished|open|todo)\b", re.IGNORECASE)
GET_TASK_TITLE_PATTERN = re.compile(
    r"^(?:show|get|view|display|find|fetch)\s+(?:the\s+)?task\s+(?:called\s+|titled\s+)?['\"]?([^'\"]+?)['\"]?$",
    re.IGNORECASE
)

def detect_context_reference(query: str, raw_task_id: Optional[Any] = None) -> Optional[str]:
    """Detect conversational context reference from query or raw entity."""
    if raw_task_id in ("first", "last", "previous"):
        return f"ordinal:{raw_task_id}"
    
    q_lower = query.lower()
    ord_match = CONTEXT_ORDINAL_PATTERN.search(q_lower)
    if ord_match:
        return f"ordinal:{ord_match.group(1)}"
        
    pro_match = CONTEXT_PRONOUN_PATTERN.search(q_lower)
    if pro_match:
        return f"pronoun:{pro_match.group(1)}"
        
    return None

def build_structured_request(
    intent: str,
    confidence: float,
    raw_query: str,
    entities: Dict[str, Any],
    resolved_task_id: Optional[int] = None,
    context_reference: Optional[str] = None,
) -> StructuredRequest:
    """
    Construct a StructuredRequest contract from AI pipeline outputs.
    Does not populate missing fields with arbitrary defaults.
    """
    task_id_val = None
    if resolved_task_id is not None:
        task_id_val = resolved_task_id
    elif isinstance(entities.get("task_id"), int):
        task_id_val = entities.get("task_id")

    ctx_ref = context_reference or detect_context_reference(raw_query, entities.get("task_id"))

    # Resolve title
    title_val = entities.get("title")
    if title_val and isinstance(title_val, str):
        title_val = title_val.strip()
        if CONTEXT_PRONOUN_PATTERN.search(title_val) and len(title_val.split()) <= 2:
            title_val = None
    else:
        title_val = None

    # Fallback title extraction for GET_TASK when classical NER missed the title tokens
    if not title_val and intent == "GET_TASK" and task_id_val is None and not entities.get("task_id"):
        title_match = GET_TASK_TITLE_PATTERN.search(raw_query.strip())
        if title_match:
            candidate = title_match.group(1).strip()
            if not candidate.isdigit() and candidate.lower() not in ("first", "last", "latest", "previous", "it", "its", "this", "that"):
                title_val = candidate

    # Resolve status (fallback to query keywords if classical NER missed the status token)
    status_val = entities.get("status")
    if not status_val and raw_query:
        st_match = STATUS_QUERY_PATTERN.search(raw_query)
        if st_match:
            from ..utils.normalizer import normalize_status
            status_val = normalize_status(st_match.group(1))

    # Build filters only when relevant (e.g. GET_TASKS)
    filters_obj = None
    if intent == "GET_TASKS":
        filters_obj = RequestFilters(
            status=status_val,
            priority=entities.get("priority"),
            category=entities.get("category"),
            search=entities.get("search"),
        )

    new_title_val = entities.get("new_title")
    if new_title_val and isinstance(new_title_val, str):
        new_title_val = new_title_val.strip()
    else:
        new_title_val = None

    return StructuredRequest(
        intent=intent,
        confidence=confidence,
        raw_query=raw_query,
        entities=dict(entities),
        task_id=task_id_val,
        task_title=title_val,
        new_title=new_title_val,
        description=entities.get("description"),
        priority=entities.get("priority"),
        category=entities.get("category"),
        deadline=entities.get("deadline"),
        status=status_val,
        filters=filters_obj,
        context_reference=ctx_ref,
        is_valid=True,
        missing_fields=[],
        validation_errors=[],
        requires_confirmation=False,
        error_type=None,
    )
