import os
import sys
import re
from pathlib import Path
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

# Add project root to sys.path so ai package is accessible
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.inference.pipeline import AIPipeline
from ..utils.normalizer import normalize_entities, EntityExtractorNormalizer
from ..memory.context_memory import ContextMemory
from ..schemas.request_contract import build_structured_request, detect_context_reference
from ..services.request_validator import RequestValidator
from ..services.intent_guardrail import IntentGuardrail
from ..workflows.planner import Planner
from ..workflows.executor import Executor
from ..tools.task_tool import TaskTool
from ..schemas.agent import AgentResponse
from ..core.errors import TaskForgeError

AFFIRMATIVE_PATTERN = re.compile(
    r"^\s*(?:"
    r"yes|yep|yeah|y|sure|ok|okay|confirm|confirmed|proceed|do\s+it|"
    r"yes\s*,?\s*(?:please|confirm|confirmed|proceed|do\s+it|sure)|"
    r"yes\s+please|"
    r"yes\s*,?\s*delete\s+all(?:\s+tasks)?|"
    r"confirm\s+delete\s+all(?:\s+tasks)?|"
    r"delete\s+all(?:\s+tasks)?\s*,?\s*confirm|"
    r"confirm\s+deletion"
    r")\s*[.!]?$",
    re.IGNORECASE
)

CANCELLATION_PATTERN = re.compile(
    r"^\s*(?:"
    r"no|nope|cancel|cancelled|stop|abort|nevermind|never\s+mind|don't|do\s+not|"
    r"(?:no\s*,?\s*)?(?:don't|do\s+not)\s+delete(?:\s+all)?(?:\s+tasks)?|"
    r"cancel\s+deletion"
    r")\s*[.!]?$",
    re.IGNORECASE
)

class TaskForgeAgent:
    """
    Core Automation Agent orchestrating the full Natural Language AI Pipeline:
    Input -> Intent & NER -> Normalization & Context Resolution -> Structured Request -> Centralized Validation -> Planner -> Executor -> Structured Result
    """
    def __init__(self):
        self.ai_pipeline = AIPipeline()
        self.memory = ContextMemory()

    def execute_command(self, goal: str, db: Session, confirmed: bool = False) -> AgentResponse:
        goal_clean = (goal or "").strip()
        if not goal_clean:
            return AgentResponse(
                success=False,
                message="Please provide a valid task command.",
                intent="UNKNOWN",
                error_type="EMPTY_INPUT",
            )

        try:
            # Check for follow-up confirmation of pending dangerous action
            pending_action = getattr(self.memory, "pending_action", None)
            is_confirmation_turn = False
            intent = None
            confidence = 0.0
            raw_entities = {}

            if pending_action == "DELETE_ALL_TASKS":
                # Check 1: Explicit standalone affirmative response
                if confirmed or AFFIRMATIVE_PATTERN.match(goal_clean):
                    is_confirmation_turn = True
                    confirmed = True
                    intent = "DELETE_ALL_TASKS"
                    confidence = 1.0
                    raw_entities = {}
                    # Clear pending action immediately as confirmation is consumed
                    self.memory.pending_action = None

                # Check 2: Explicit standalone cancellation response
                elif CANCELLATION_PATTERN.match(goal_clean):
                    self.memory.pending_action = None
                    self.memory.record_turn(
                        query=goal_clean,
                        intent="DELETE_ALL_TASKS",
                        success=True,
                    )
                    return AgentResponse(
                        success=True,
                        message="Bulk deletion has been cancelled. No tasks were deleted.",
                        intent="DELETE_ALL_TASKS",
                        confidence=1.0,
                        data={"cancelled": True},
                    )

                # Check 3: Process input through AI pipeline to detect unrelated task command vs ambiguous
                else:
                    ai_result = self.ai_pipeline.process(goal_clean)
                    candidate_intent = ai_result["intent"]
                    candidate_confidence = ai_result["confidence"]
                    has_ctx = self.memory.last_task_id is not None
                    candidate_intent, candidate_confidence = IntentGuardrail.resolve_intent(
                        raw_text=goal_clean,
                        predicted_intent=candidate_intent,
                        confidence=candidate_confidence,
                        has_active_context=has_ctx,
                    )

                    if candidate_intent in ("CREATE_TASK", "UPDATE_TASK", "GET_TASK", "GET_TASKS", "DELETE_TASK"):
                        # Unrelated task command replaces and clears the pending deletion
                        self.memory.pending_action = None
                        intent = candidate_intent
                        confidence = candidate_confidence
                        raw_entities = ai_result["entities"]
                        confirmed = False  # NEVER inherits confirmation!

                    elif candidate_intent == "DELETE_ALL_TASKS":
                        # A new DELETE_ALL request requires its own confirmation
                        self.memory.pending_action = None
                        intent = "DELETE_ALL_TASKS"
                        confidence = candidate_confidence
                        raw_entities = ai_result["entities"]
                        confirmed = False

                    else:
                        # Ambiguous response - ask for clarification without executing anything
                        return AgentResponse(
                            success=False,
                            message="Your response was not clear. A bulk deletion request is pending. Please confirm with 'yes' to proceed with deleting all tasks, or 'no' to cancel.",
                            intent="UNKNOWN",
                            confidence=candidate_confidence,
                            error_type="AMBIGUOUS_CONFIRMATION",
                            data={"pending_action": "DELETE_ALL_TASKS", "requires_confirmation": True},
                        )

            if not is_confirmation_turn and intent is None:
                # 1. AI Inference (Intent Classification & NER Sequence Labeling)
                ai_result = self.ai_pipeline.process(goal_clean)
                intent = ai_result["intent"]
                confidence = ai_result["confidence"]
                raw_entities = ai_result["entities"]

                # Apply Deterministic Intent Guardrails
                has_active_context = self.memory.last_task_id is not None
                intent, confidence = IntentGuardrail.resolve_intent(
                    raw_text=goal_clean,
                    predicted_intent=intent,
                    confidence=confidence,
                    has_active_context=has_active_context,
                )

            # 2. Deterministic Entity Extraction & Normalization
            normalized_entities = EntityExtractorNormalizer.extract_and_normalize(
                raw_text=goal_clean,
                intent=intent,
                ner_entities=raw_entities,
            )

            # 3. Context Resolution
            raw_task_id = normalized_entities.get("task_id")
            task_title = normalized_entities.get("title")
            has_concrete_title = bool(task_title and task_title.strip())

            resolved_task_id = self.memory.resolve_task_reference(
                query=goal_clean,
                raw_task_id=raw_task_id,
                db=db,
                has_title=has_concrete_title,
                intent=intent,
            )
            context_ref = detect_context_reference(goal_clean, raw_task_id)

            # 4. Structured Request Construction
            structured_req = build_structured_request(
                intent=intent,
                confidence=confidence,
                raw_query=goal_clean,
                entities=normalized_entities,
                resolved_task_id=resolved_task_id,
                context_reference=context_ref,
            )

            # 5. Centralized Request Validation
            validated_req = RequestValidator.validate(
                request=structured_req,
                db=db,
                memory=self.memory,
                confirmed=confirmed,
            )

            # If validation fails: stop immediately, do not execute tools or mutations
            if not validated_req.is_valid:
                if validated_req.requires_confirmation:
                    self.memory.pending_action = validated_req.intent
                else:
                    self.memory.pending_action = None

                self.memory.record_turn(
                    query=goal_clean,
                    intent=validated_req.intent,
                    task_id=validated_req.task_id,
                    success=False,
                )

                error_msg = (
                    validated_req.validation_errors[0]
                    if validated_req.validation_errors
                    else "Request validation failed."
                )
                return AgentResponse(
                    success=False,
                    message=error_msg,
                    intent=validated_req.intent,
                    confidence=validated_req.confidence,
                    error_type=validated_req.error_type or "VALIDATION_FAILED",
                    data={
                        "missing_fields": validated_req.missing_fields,
                        "validation_errors": validated_req.validation_errors,
                        "requires_confirmation": validated_req.requires_confirmation,
                    },
                )

            # If valid, clear pending action
            self.memory.pending_action = None

            # 6. Planner (Consuming Validated Structured Request)
            plan = Planner.create_plan_from_request(validated_req)

            # 7. Tool & Executor
            tool = TaskTool(db=db)
            response = Executor.execute_plan(
                plan=plan,
                tool=tool,
                memory=self.memory,
                query=goal_clean,
            )
            return response

        except TaskForgeError as e:
            # Safe domain error handling
            return AgentResponse(
                success=False,
                message=e.message,
                intent=locals().get("intent", "UNKNOWN"),
                confidence=locals().get("confidence", 0.0),
                error_type=e.error_type,
            )
        except Exception as ex:
            # Unexpected system error fallback
            return AgentResponse(
                success=False,
                message=f"An unexpected error occurred while processing your command.",
                intent="UNKNOWN",
                error_type="SYSTEM_ERROR",
            )

    def get_context_state(self) -> Dict[str, Any]:
        return self.memory.get_state()

    def reset_context(self):
        self.memory.reset()
