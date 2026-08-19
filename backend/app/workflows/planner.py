from typing import Dict, Any, Optional
from ..schemas.agent import ExecutionPlan, PlanStep
from ..core.errors import MissingEntityError, InvalidUpdateError, UnknownIntentError

class Planner:
    """
    Deterministic Agent Planner that generates validated, structured Execution Plans
    prior to executing any tool actions.
    """
    @staticmethod
    def create_plan(
        intent: str,
        confidence: float,
        entities: Dict[str, Any],
        resolved_task_id: Optional[int],
        raw_query: str,
    ) -> ExecutionPlan:
        steps = []
        resolved = dict(entities)
        if resolved_task_id is not None:
            resolved["task_id"] = resolved_task_id

        if intent == "CREATE_TASK":
            title = entities.get("title")
            if not title:
                raise MissingEntityError("title", "A task cannot be created without a title.")

            steps.append(PlanStep(
                step_number=1,
                action="VALIDATE_INPUT",
                description="Validate task title, priority, category, and deadline parameters.",
                parameters={"title": title, "priority": entities.get("priority", "Medium")}
            ))
            steps.append(PlanStep(
                step_number=2,
                action="EXECUTE_TOOL",
                description="Call TaskTool.create_task with validated task payload.",
                target_entity="task",
                parameters={
                    "tool": "create_task",
                    "title": title,
                    "description": entities.get("description", ""),
                    "priority": entities.get("priority", "Medium"),
                    "deadline": entities.get("deadline"),
                    "category": entities.get("category", "General"),
                    "status": entities.get("status", "Pending"),
                }
            ))
            steps.append(PlanStep(
                step_number=3,
                action="FORMAT_RESULT",
                description="Format structured creation response for user.",
                parameters={}
            ))

        elif intent == "GET_TASK":
            if resolved_task_id is None:
                raise MissingEntityError("task_id", "Please specify which task ID you would like to view.")

            steps.append(PlanStep(
                step_number=1,
                action="VALIDATE_TASK_ID",
                description=f"Validate existence of task ID {resolved_task_id}.",
                parameters={"task_id": resolved_task_id}
            ))
            steps.append(PlanStep(
                step_number=2,
                action="EXECUTE_TOOL",
                description=f"Call TaskTool.get_task(task_id={resolved_task_id}).",
                target_entity="task",
                parameters={"tool": "get_task", "task_id": resolved_task_id}
            ))
            steps.append(PlanStep(
                step_number=3,
                action="FORMAT_RESULT",
                description="Format task details.",
                parameters={}
            ))

        elif intent == "GET_TASKS":
            steps.append(PlanStep(
                step_number=1,
                action="PREPARE_FILTERS",
                description="Prepare filter parameters (status, priority, category, search).",
                parameters={
                    "status": entities.get("status"),
                    "priority": entities.get("priority"),
                    "category": entities.get("category"),
                }
            ))
            steps.append(PlanStep(
                step_number=2,
                action="EXECUTE_TOOL",
                description="Call TaskTool.get_all_tasks with filter parameters.",
                target_entity="tasks",
                parameters={
                    "tool": "get_all_tasks",
                    "status": entities.get("status"),
                    "priority": entities.get("priority"),
                    "category": entities.get("category"),
                }
            ))
            steps.append(PlanStep(
                step_number=3,
                action="FORMAT_RESULT",
                description="Format task list and summary counters.",
                parameters={}
            ))

        elif intent == "UPDATE_TASK":
            if resolved_task_id is None:
                raise MissingEntityError("task_id", "Please specify which task you would like to update.")

            update_fields = {
                k: v for k, v in entities.items()
                if k in ("title", "priority", "status", "category", "deadline", "description") and v is not None
            }
            if not update_fields:
                raise InvalidUpdateError("No fields to update were specified in your request.")

            steps.append(PlanStep(
                step_number=1,
                action="VALIDATE_UPDATE",
                description=f"Validate update parameters for task {resolved_task_id}.",
                parameters={"task_id": resolved_task_id, "fields": list(update_fields.keys())}
            ))
            steps.append(PlanStep(
                step_number=2,
                action="EXECUTE_TOOL",
                description=f"Call TaskTool.update_task(task_id={resolved_task_id}).",
                target_entity="task",
                parameters={"tool": "update_task", "task_id": resolved_task_id, **update_fields}
            ))
            steps.append(PlanStep(
                step_number=3,
                action="FORMAT_RESULT",
                description="Format updated task response.",
                parameters={}
            ))

        elif intent == "DELETE_TASK":
            if resolved_task_id is None:
                raise MissingEntityError("task_id", "Please specify which task you would like to delete.")

            steps.append(PlanStep(
                step_number=1,
                action="VALIDATE_TASK_ID",
                description=f"Validate existence of task {resolved_task_id} before deletion.",
                parameters={"task_id": resolved_task_id}
            ))
            steps.append(PlanStep(
                step_number=2,
                action="EXECUTE_TOOL",
                description=f"Call TaskTool.delete_task(task_id={resolved_task_id}).",
                target_entity="task",
                parameters={"tool": "delete_task", "task_id": resolved_task_id}
            ))
            steps.append(PlanStep(
                step_number=3,
                action="FORMAT_RESULT",
                description="Format deletion confirmation response.",
                parameters={}
            ))

        elif intent == "DELETE_ALL_TASKS":
            steps.append(PlanStep(
                step_number=1,
                action="VALIDATE_BULK_DELETE",
                description="Prepare to delete all tasks from the database.",
                parameters={}
            ))
            steps.append(PlanStep(
                step_number=2,
                action="EXECUTE_TOOL",
                description="Call TaskTool.delete_all_tasks().",
                target_entity="tasks",
                parameters={"tool": "delete_all_tasks"}
            ))
            steps.append(PlanStep(
                step_number=3,
                action="FORMAT_RESULT",
                description="Format bulk deletion confirmation response.",
                parameters={}
            ))

        else:
            raise UnknownIntentError(confidence=confidence)

        return ExecutionPlan(
            intent=intent,
            steps=steps,
            confidence=confidence,
            resolved_entities=resolved,
        )
