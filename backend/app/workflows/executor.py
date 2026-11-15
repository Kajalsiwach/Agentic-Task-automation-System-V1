from typing import Dict, Any, Optional
from ..schemas.agent import ExecutionPlan, AgentResponse
from ..tools.task_tool import TaskTool
from ..memory.context_memory import ContextMemory
from ..models.task import Task
from ..core.errors import (
    TaskForgeError,
    InvalidPlanError,
    TaskNotFoundError,
    DatabaseError,
    ExecutionVerificationError,
)

class Executor:
    """
    Validates and executes structured Execution Plans via the Tool layer.
    Safely records execution outcomes in conversational memory.
    """
    @staticmethod
    def execute_plan(
        plan: ExecutionPlan,
        tool: TaskTool,
        memory: ContextMemory,
        query: str,
    ) -> AgentResponse:
        if not plan or not plan.steps:
            raise InvalidPlanError("Cannot execute an empty or uninitialized plan.")

        tool_result: Optional[Dict[str, Any]] = None
        executed_task_id: Optional[int] = None
        executed_task_title: Optional[str] = None
        tasks_list_ids: Optional[list] = None

        # Execute steps sequentially
        for step in plan.steps:
            if step.action == "EXECUTE_TOOL":
                params = step.parameters
                tool_name = params.get("tool")

                if tool_name == "create_task":
                    tool_result = tool.create_task(
                        title=params["title"],
                        description=params.get("description", ""),
                        priority=params.get("priority", "Medium"),
                        deadline=params.get("deadline"),
                        category=params.get("category", "General"),
                        status=params.get("status", "Pending"),
                    )
                    executed_task_id = tool_result["task"]["id"]
                    executed_task_title = tool_result["task"]["title"]

                    # Post-execution DB verification
                    tool.db.expire_all()
                    persisted_task = tool.db.query(Task).filter(Task.id == executed_task_id).first()
                    if not persisted_task:
                        raise ExecutionVerificationError(
                            f"Post-execution verification failed: Task {executed_task_id} not found in database."
                        )
                    if persisted_task.title != executed_task_title:
                        raise ExecutionVerificationError(
                            f"Post-execution verification failed: Persisted title '{persisted_task.title}' does not match expected '{executed_task_title}'."
                        )

                    memory.set_active_task(executed_task_id, executed_task_title)

                elif tool_name == "get_task":
                    tool_result = tool.get_task(task_id=params["task_id"])
                    executed_task_id = tool_result["task"]["id"]
                    executed_task_title = tool_result["task"]["title"]
                    memory.set_active_task(executed_task_id, executed_task_title)

                elif tool_name == "get_all_tasks":
                    tool_result = tool.get_all_tasks(
                        status=params.get("status"),
                        priority=params.get("priority"),
                        category=params.get("category"),
                        search=params.get("search"),
                    )
                    tasks_list_ids = [t["id"] for t in tool_result["tasks"]]

                elif tool_name == "update_task":
                    tool_result = tool.update_task(
                        task_id=params["task_id"],
                        title=params.get("title"),
                        description=params.get("description"),
                        priority=params.get("priority"),
                        deadline=params.get("deadline"),
                        category=params.get("category"),
                        status=params.get("status"),
                    )
                    executed_task_id = tool_result["task"]["id"]
                    executed_task_title = tool_result["task"]["title"]

                    # Post-execution DB verification
                    tool.db.expire_all()
                    persisted_task = tool.db.query(Task).filter(Task.id == executed_task_id).first()
                    if not persisted_task:
                        raise ExecutionVerificationError(
                            f"Post-execution verification failed: Updated task {executed_task_id} not found in database."
                        )
                    if params.get("title") is not None and persisted_task.title != params.get("title"):
                        raise ExecutionVerificationError(
                            f"Post-execution verification failed: Task title '{persisted_task.title}' does not match expected '{params.get('title')}'."
                        )
                    if params.get("priority") is not None and persisted_task.priority != params.get("priority"):
                        raise ExecutionVerificationError(
                            f"Post-execution verification failed: Task priority '{persisted_task.priority}' does not match expected '{params.get('priority')}'."
                        )
                    if params.get("status") is not None and persisted_task.status != params.get("status"):
                        raise ExecutionVerificationError(
                            f"Post-execution verification failed: Task status '{persisted_task.status}' does not match expected '{params.get('status')}'."
                        )
                    if params.get("category") is not None and persisted_task.category != params.get("category"):
                        raise ExecutionVerificationError(
                            f"Post-execution verification failed: Task category '{persisted_task.category}' does not match expected '{params.get('category')}'."
                        )
                    if params.get("deadline") is not None and persisted_task.deadline != params.get("deadline"):
                        raise ExecutionVerificationError(
                            f"Post-execution verification failed: Task deadline '{persisted_task.deadline}' does not match expected '{params.get('deadline')}'."
                        )

                    memory.set_active_task(executed_task_id, executed_task_title)

                elif tool_name == "delete_task":
                    tool_result = tool.delete_task(task_id=params["task_id"])
                    executed_task_id = None
                    executed_task_title = None

                    # Post-execution DB verification
                    tool.db.expire_all()
                    persisted_task = tool.db.query(Task).filter(Task.id == params["task_id"]).first()
                    if persisted_task is not None:
                        raise ExecutionVerificationError(
                            f"Post-execution verification failed: Task {params['task_id']} was not deleted from database."
                        )

                    memory.clear_active_task()

                elif tool_name == "delete_all_tasks":
                    tool_result = tool.delete_all_tasks()
                    executed_task_id = None
                    executed_task_title = None
                    tasks_list_ids = []

                    # Post-execution DB verification
                    tool.db.expire_all()
                    remaining_count = tool.db.query(Task).count()
                    if remaining_count != 0:
                        raise ExecutionVerificationError(
                            f"Post-execution verification failed: {remaining_count} tasks remain in database after delete_all_tasks."
                        )

                    memory.reset()

                else:
                    raise InvalidPlanError(f"Unknown tool name: {tool_name}")

        # Update conversational memory on success
        if plan.intent != "DELETE_ALL_TASKS":
            memory.record_turn(
                query=query,
                intent=plan.intent,
                task_id=executed_task_id,
                task_title=executed_task_title,
                tasks_list=tasks_list_ids,
                success=True,
            )

        # Build user-friendly message
        message = ""
        data_payload = None

        if plan.intent == "CREATE_TASK":
            task_data = tool_result["task"]
            message = f"Task created successfully: '{task_data['title']}' (ID: {task_data['id']})."
            data_payload = task_data

        elif plan.intent == "GET_TASK":
            task_data = tool_result["task"]
            message = f"Task {task_data['id']}: '{task_data['title']}' (Priority: {task_data['priority']}, Category: {task_data['category']}, Status: {task_data['status']})."
            data_payload = task_data

        elif plan.intent == "GET_TASKS":
            count = tool_result["count"]
            message = f"Found {count} task{'s' if count != 1 else ''}."
            data_payload = tool_result["tasks"]

        elif plan.intent == "UPDATE_TASK":
            task_data = tool_result["task"]
            message = f"Task {task_data['id']} updated successfully."
            data_payload = task_data

        elif plan.intent == "DELETE_TASK":
            del_id = tool_result["deleted_task_id"]
            message = f"Task {del_id} deleted successfully."
            data_payload = {"deleted_task_id": del_id}

        elif plan.intent == "DELETE_ALL_TASKS":
            del_count = tool_result["deleted_count"]
            message = f"All tasks deleted successfully ({del_count} removed)."
            data_payload = {"deleted_count": del_count}

        return AgentResponse(
            success=True,
            message=message,
            intent=plan.intent,
            confidence=plan.confidence,
            plan=plan,
            data=data_payload,
        )
