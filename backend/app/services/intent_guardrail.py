import re
from typing import Tuple

class IntentGuardrail:
    """
    Deterministic Intent Classification Guardrail Layer.
    Corrects misclassifications or low-confidence/UNKNOWN predictions on recognizable
    structural commands and pronoun follow-ups while preserving TF-IDF predictions
    for non-template natural phrasings.
    """

    # 1. BULK DELETE PATTERNS
    BULK_DELETE_PATTERNS = [
        r"^\s*(?:delete|clear|remove|drop|erase)\s+all(?:\s+my)?\s+tasks?\b",
        r"^\s*(?:delete|clear|remove|drop|erase)\s+everything\b",
    ]

    # 2. BULK READ PATTERNS
    BULK_READ_PATTERNS = [
        r"^\s*(?:list|show|get|view|display|fetch)\s+all(?:\s+my)?\s+tasks?\b",
        r"^\s*(?:list|show|view|display)\s+all\b",
        r"^\s*list\s+(?:all\s+)?tasks?\b",
        r"^\s*(?:show|view|display)\s+tasks\b",
        r"^\s*(?:what\s+are\s+my\s+tasks|all\s+tasks)\b",
    ]

    # 3. EXPLICIT SINGLE DELETE PATTERNS
    SINGLE_DELETE_PATTERNS = [
        r"^\s*(?:delete|remove|cancel|drop)\s+task\b",
        r"^\s*(?:delete|remove|cancel|drop)\s+(?:that|this|the)\s+task\b",
        r"^\s*(?:delete|remove|cancel|drop)\s+(?:that|this)\s+one\b",
        r"^\s*(?:delete|remove|cancel|drop)\s+it\b",
    ]

    # 4. EXPLICIT UPDATE PATTERNS
    UPDATE_PATTERNS = [
        r"^\s*rename\s+task\b",
        r"^\s*(?:mark|set)\s+(?:the\s+|that\s+|this\s+)?(?:task\s+|one\s+)?.*?(?:as|to)\s+(?:completed|complete|done|finished|pending|in\s+progress)\b",
        r"^\s*(?:mark|set)\s+(?:it|that\s+one|this\s+one)\s+(?:as|to)?\s*(?:completed|complete|done|finished|pending|in\s+progress)\b",
        r"^\s*(?:complete|finish)\s+(?:it|that\s+task|this\s+task|that\s+one|this\s+one|task\s+\d+|the\s+task)\b",
        r"^\s*(?:set|change|update)\s+priority\s+of\b",
        r"^\s*(?:set|change|update)\s+its\s+priority\b",
        r"^\s*(?:change|update)\s+its\s+category\b",
        r"^\s*(?:change|update)\s+(?:the\s+)?category\s+of\b",
        r"^\s*(?:update|modify|edit|change)\s+task\b",
        r"^\s*(?:update|modify|edit|change)\s+(?:that|this|the)\s+task\b",
        r"^\s*(?:update|modify|edit|change)\s+(?:that|this)\s+one\b",
        r"^\s*(?:update|modify|edit|change)\s+it\b",
    ]

    # 5. EXPLICIT CREATE PATTERNS
    CREATE_PATTERNS = [
        r"^\s*(?:create|add|schedule|set\s+up)\s+(?:a\s+|an\s+)?(?:new\s+)?task\b",
        r"^\s*remind\s+me\s+to\b",
        r"^\s*new\s+task\b",
    ]

    # 6. EXPLICIT SINGLE READ PATTERNS
    SINGLE_READ_PATTERNS = [
        r"^\s*(?:get|show|view|find|display|fetch)\s+task\b",
        r"^\s*(?:get|show|view|find|display|fetch)\s+(?:that|this|the)\s+task\b",
        r"^\s*(?:get|show|view|find|display|fetch)\s+(?:the\s+)?(?:first|last|latest|previous|prior)\s+task\b",
    ]

    @classmethod
    def resolve_intent(
        cls,
        raw_text: str,
        predicted_intent: str,
        confidence: float,
        has_active_context: bool = False,
    ) -> Tuple[str, float]:
        """
        Determines the final intent and confidence.
        Rules:
        - Structural guardrail checks override misclassifications or resolve UNKNOWN.
        - Unambiguous matches assign high confidence (1.0).
        - If no structural pattern matches, preserves the predicted_intent and confidence.
        """
        text = re.sub(r"[.?!]+$", "", (raw_text or "").strip()).strip().lower()

        # 1. Bulk Delete (Highest priority structural check: never mistake bulk delete for single or read)
        for pat in cls.BULK_DELETE_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                return "DELETE_ALL_TASKS", 1.0

        # 2. Bulk Read (Never mistake "list all tasks" for DELETE_ALL_TASKS)
        for pat in cls.BULK_READ_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                return "GET_TASKS", 1.0

        # 3. Explicit Single Delete
        for pat in cls.SINGLE_DELETE_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                return "DELETE_TASK", 1.0

        # 4. Explicit Update
        for pat in cls.UPDATE_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                return "UPDATE_TASK", 1.0

        # 5. Explicit Create
        for pat in cls.CREATE_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                return "CREATE_TASK", 1.0

        # 6. Explicit Single Read
        for pat in cls.SINGLE_READ_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                return "GET_TASK", 1.0

        # 7. Follow-up short commands with active context:
        if has_active_context:
            if re.search(r"^\s*(?:mark\s+)?(?:done|completed|finished)\b", text, re.IGNORECASE):
                return "UPDATE_TASK", 1.0
            if re.search(r"^\s*(?:delete|remove)\b", text, re.IGNORECASE):
                return "DELETE_TASK", 1.0

        # Default: Preserve ML model output untouched
        return predicted_intent, confidence
