from typing import Dict, Any, Optional
from ..schemas.agent import ExecutionPlan, PlanStep
from ..schemas.request_contract import StructuredRequest
from ..core.errors import MissingEntityError, InvalidUpdateError, UnknownIntentError

class Planner:
    """
    Deterministic Agent Planner that generates validated, structured Execution Plans
    prior to executing any tool actions.
    Consumes validated StructuredRequest contracts.
    """

    @staticmethod
    def create_plan_from_request(request: StructuredRequest) -> ExecutionPlan:
        steps = []
        resolved = dict(request.entities)
        if request.task_id is not None:
            resolved["task_id"] = request.task_id

        if request.intent == "CREATE_TASK":
            steps.append(PlanStep(
                step_number=1,
                action="VALIDATE_INPUT",
                description="Validate task title, priority, category, and deadline parameters.",
                parameters={"title": request.task_title, "priority": request.priority or "Medium"}
            ))
            steps.append(PlanStep(
                step_number=2,
                action="EXECUTE_TOOL",
                description="Call TaskTool.create_task with validated task payload.",
                target_entity="task",
                parameters={
                    "tool": "create_task",
                    "title": request.task_title,
                    "description": request.description or "",
                    "priority": request.priority or "Medium",
                    "deadline": request.deadline,
                    "category": request.category or "General",
                    "status": request.status or "Pending",
                }
            ))
            steps.append(PlanStep(
                step_number=3,
                action="FORMAT_RESULT",
                description="Format structured creation response for user.",
                parameters={}
            ))

        elif request.intent == "GET_TASK":
            steps.append(PlanStep(
                step_number=1,
                action="VALIDATE_TASK_ID",
                description=f"Validate existence of task ID {request.task_id}.",
                parameters={"task_id": request.task_id}
            ))
            steps.append(PlanStep(
                step_number=2,
                action="EXECUTE_TOOL",
                description=f"Call TaskTool.get_task(task_id={request.task_id}).",
                target_entity="task",
                parameters={"tool": "get_task", "task_id": request.task_id}
            ))
            steps.append(PlanStep(
                step_number=3,
                action="FORMAT_RESULT",
                description="Format task details.",
                parameters={}
            ))

        elif request.intent == "GET_TASKS":
            filter_params = {
                "status": request.filters.status if request.filters else None,
                "priority": request.filters.priority if request.filters else None,
                "category": request.filters.category if request.filters else None,
                "search": request.filters.search if request.filters else None,
            }
            steps.append(PlanStep(
                step_number=1,
                action="PREPARE_FILTERS",
                description="Prepare filter parameters (status, priority, category, search).",
                parameters=filter_params
            ))
            steps.append(PlanStep(
                step_number=2,
                action="EXECUTE_TOOL",
                description="Call TaskTool.get_all_tasks with filter parameters.",
                target_entity="tasks",
                parameters={"tool": "get_all_tasks", **filter_params}
            ))
            steps.append(PlanStep(
                step_number=3,
                action="FORMAT_RESULT",
                description="Format task list and summary counters.",
                parameters={}
            ))

        elif request.intent == "UPDATE_TASK":
            update_fields = {}
            if request.task_title is not None:
                update_fields["title"] = request.task_title
            if request.description is not None:
                update_fields["description"] = request.description
            if request.priority is not None:
                update_fields["priority"] = request.priority
            if request.category is not None:
                update_fields["category"] = request.category
            if request.deadline is not None:
                update_fields["deadline"] = request.deadline
            if request.status is not None:
                update_fields["status"] = request.status

            steps.append(PlanStep(
                step_number=1,
                action="VALIDATE_UPDATE",
                description=f"Validate update parameters for task {request.task_id}.",
                parameters={"task_id": request.task_id, "fields": list(update_fields.keys())}
            ))
            steps.append(PlanStep(
                step_number=2,
                action="EXECUTE_TOOL",
                description=f"Call TaskTool.update_task(task_id={request.task_id}).",
                target_entity="task",
                parameters={"tool": "update_task", "task_id": request.task_id, **update_fields}
            ))
            steps.append(PlanStep(
                step_number=3,
                action="FORMAT_RESULT",
                description="Format updated task response.",
                parameters={}
            ))

        elif request.intent == "DELETE_TASK":
            steps.append(PlanStep(
                step_number=1,
                action="VALIDATE_TASK_ID",
                description=f"Validate existence of task {request.task_id} before deletion.",
                parameters={"task_id": request.task_id}
            ))
            steps.append(PlanStep(
                step_number=2,
                action="EXECUTE_TOOL",
                description=f"Call TaskTool.delete_task(task_id={request.task_id}).",
                target_entity="task",
                parameters={"tool": "delete_task", "task_id": request.task_id}
            ))
            steps.append(PlanStep(
                step_number=3,
                action="FORMAT_RESULT",
                description="Format deletion confirmation response.",
                parameters={}
            ))

        elif request.intent == "DELETE_ALL_TASKS":
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
            raise UnknownIntentError(confidence=request.confidence)

        return ExecutionPlan(
            intent=request.intent,
            steps=steps,
            confidence=request.confidence,
            resolved_entities=resolved,
        )

    @staticmethod
    def create_plan(
        intent: str,
        confidence: float,
        entities: Dict[str, Any],
        resolved_task_id: Optional[int],
        raw_query: str,
    ) -> ExecutionPlan:
        """
        Legacy plan generation method maintained for backwards compatibility.
        """
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
