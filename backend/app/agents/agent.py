import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

# Add project root to sys.path so ai package is accessible
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.inference.pipeline import AIPipeline
from ..utils.normalizer import normalize_entities
from ..memory.context_memory import ContextMemory
from ..workflows.planner import Planner
from ..workflows.executor import Executor
from ..tools.task_tool import TaskTool
from ..schemas.agent import AgentResponse
from ..core.errors import TaskForgeError

class TaskForgeAgent:
    """
    Core Automation Agent orchestrating the full Natural Language AI Pipeline:
    Input -> Intent -> NER -> Normalization -> Context Resolution -> Planner -> Executor -> Structured Result
    """
    def __init__(self):
        self.ai_pipeline = AIPipeline()
        self.memory = ContextMemory()

    def execute_command(self, goal: str, db: Session) -> AgentResponse:
        goal_clean = (goal or "").strip()
        if not goal_clean:
            return AgentResponse(
                success=False,
                message="Please provide a valid task command.",
                intent="UNKNOWN",
                error_type="EMPTY_INPUT",
            )

        try:
            # 1. AI Inference (Intent Classification & NER Sequence Labeling)
            ai_result = self.ai_pipeline.process(goal_clean)
            intent = ai_result["intent"]
            confidence = ai_result["confidence"]
            raw_entities = ai_result["entities"]

            # 2. Entity Normalization & Validation
            normalized_entities = normalize_entities(raw_entities)

            # 3. Context Resolution
            raw_task_id = normalized_entities.get("task_id")
            resolved_task_id = self.memory.resolve_task_reference(
                query=goal_clean,
                raw_task_id=raw_task_id,
                db=db
            )

            # 4. Planner
            plan = Planner.create_plan(
                intent=intent,
                confidence=confidence,
                entities=normalized_entities,
                resolved_task_id=resolved_task_id,
                raw_query=goal_clean,
            )

            # 5. Tool & Executor
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
