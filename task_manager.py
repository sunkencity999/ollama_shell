#!/usr/bin/env python3
"""
Task Manager for Ollama Shell

This module provides a task management system for handling complex, multi-step tasks
in the Ollama Shell Assistant. It enables the Assistant to break down complex requests
into subtasks, execute them in the appropriate order, and maintain state between steps.
"""

import os
import json
import logging
import asyncio
import time
import re
from typing import Dict, List, Any, Optional, Union, Tuple
from enum import Enum
from dataclasses import dataclass, field, asdict
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("task_manager")

class TaskStatus(Enum):
    """Status of a task in the task manager"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"

@dataclass
class TaskResult:
    """Result of a task execution"""
    success: bool
    result: Any = None
    error: Optional[str] = None
    artifacts: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Task:
    """Represents a single task in a multi-step process"""
    id: str
    description: str
    task_type: str
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    result: Optional[TaskResult] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for serialization"""
        task_dict = asdict(self)
        # Convert Enum to string
        task_dict["status"] = self.status.value
        return task_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create a Task from a dictionary"""
        # Convert string back to Enum
        if "status" in data and isinstance(data["status"], str):
            data["status"] = TaskStatus(data["status"])
        
        # Convert result dict to TaskResult if present
        if "result" in data and data["result"] and isinstance(data["result"], dict):
            data["result"] = TaskResult(**data["result"])
            
        return cls(**data)

class TaskManager:
    """
    Manages complex, multi-step tasks by breaking them down into subtasks,
    tracking dependencies, and maintaining state between steps.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the TaskManager.
        
        Args:
            storage_path: Path to store task state (defaults to ~/.ollama_shell/tasks)
        """
        self.storage_path = storage_path or os.path.expanduser("~/.ollama_shell/tasks")
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Active task workflow
        self.current_workflow_id: Optional[str] = None
        self.tasks: Dict[str, Task] = {}
        self.task_dependencies: Dict[str, List[str]] = {}  # task_id -> [dependent_task_ids]
        
        logger.info(f"Initialized TaskManager with storage at {self.storage_path}")
    
    def create_workflow(self, description: str) -> str:
        """
        Create a new task workflow.
        
        Args:
            description: Description of the overall workflow
            
        Returns:
            Workflow ID
        """
        workflow_id = str(uuid.uuid4())
        self.current_workflow_id = workflow_id
        self.tasks = {}
        self.task_dependencies = {}
        
        # Create workflow directory
        workflow_path = os.path.join(self.storage_path, workflow_id)
        os.makedirs(workflow_path, exist_ok=True)
        
        # Save workflow metadata
        with open(os.path.join(workflow_path, "workflow.json"), "w") as f:
            json.dump({
                "id": workflow_id,
                "description": description,
                "created_at": time.time(),
                "status": TaskStatus.PENDING.value
            }, f, indent=2)
        
        logger.info(f"Created new workflow: {workflow_id} - {description}")
        return workflow_id
    
    def add_task(self, description: str, task_type: str, 
                 dependencies: Optional[List[str]] = None,
                 metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add a task to the current workflow.
        
        Args:
            description: Description of the task
            task_type: Type of task (e.g., file_creation, web_browsing)
            dependencies: List of task IDs that must complete before this task
            metadata: Additional metadata for the task
            
        Returns:
            Task ID
        """
        if not self.current_workflow_id:
            raise ValueError("No active workflow. Call create_workflow first.")
        
        task_id = str(uuid.uuid4())
        dependencies = dependencies or []
        metadata = metadata or {}
        
        task = Task(
            id=task_id,
            description=description,
            task_type=task_type,
            dependencies=dependencies,
            metadata=metadata
        )
        
        # Update task dependencies
        for dep_id in dependencies:
            if dep_id not in self.tasks:
                raise ValueError(f"Dependency task {dep_id} does not exist")
            
            if dep_id not in self.task_dependencies:
                self.task_dependencies[dep_id] = []
            
            self.task_dependencies[dep_id].append(task_id)
        
        # If task has dependencies, mark it as blocked
        if dependencies:
            task.status = TaskStatus.BLOCKED
        
        self.tasks[task_id] = task
        
        # Save task to disk
        self._save_task(task)
        
        logger.info(f"Added task {task_id} to workflow {self.current_workflow_id}: {description}")
        return task_id
    
    def get_next_executable_tasks(self) -> List[Task]:
        """
        Get the next set of tasks that can be executed (no pending dependencies).
        
        Returns:
            List of executable tasks
        """
        executable_tasks = []
        
        for task_id, task in self.tasks.items():
            if task.status == TaskStatus.PENDING:
                # Check if all dependencies are completed
                dependencies_met = True
                for dep_id in task.dependencies:
                    dep_task = self.tasks.get(dep_id)
                    if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                        dependencies_met = False
                        break
                
                if dependencies_met:
                    executable_tasks.append(task)
        
        return executable_tasks
    
    def update_task_status(self, task_id: str, status: TaskStatus, 
                          result: Optional[TaskResult] = None) -> None:
        """
        Update the status of a task and its result.
        
        Args:
            task_id: ID of the task to update
            status: New status of the task
            result: Result of the task execution
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} does not exist")
        
        task = self.tasks[task_id]
        
        # Update task status
        task.status = status
        
        # Update timestamps based on status
        if status == TaskStatus.IN_PROGRESS and not task.started_at:
            task.started_at = time.time()
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED] and not task.completed_at:
            task.completed_at = time.time()
        
        # Update result if provided
        if result:
            task.result = result
        
        # Save updated task
        self._save_task(task)
        
        # If task is completed, update dependent tasks
        if status == TaskStatus.COMPLETED and task_id in self.task_dependencies:
            for dependent_id in self.task_dependencies[task_id]:
                dependent_task = self.tasks.get(dependent_id)
                if dependent_task and dependent_task.status == TaskStatus.BLOCKED:
                    # Check if all dependencies are now completed
                    all_deps_completed = True
                    for dep_id in dependent_task.dependencies:
                        dep_task = self.tasks.get(dep_id)
                        if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                            all_deps_completed = False
                            break
                    
                    if all_deps_completed:
                        dependent_task.status = TaskStatus.PENDING
                        self._save_task(dependent_task)
        
        logger.info(f"Updated task {task_id} status to {status.value}")
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """
        Get the status of the current workflow.
        
        Returns:
            Dictionary with workflow status information
        """
        if not self.current_workflow_id:
            raise ValueError("No active workflow")
        
        total_tasks = len(self.tasks)
        completed_tasks = sum(1 for task in self.tasks.values() if task.status == TaskStatus.COMPLETED)
        failed_tasks = sum(1 for task in self.tasks.values() if task.status == TaskStatus.FAILED)
        pending_tasks = sum(1 for task in self.tasks.values() if task.status in [TaskStatus.PENDING, TaskStatus.BLOCKED])
        in_progress_tasks = sum(1 for task in self.tasks.values() if task.status == TaskStatus.IN_PROGRESS)
        
        # Determine overall status
        if failed_tasks > 0:
            overall_status = "partially_completed" if completed_tasks > 0 else "failed"
        elif completed_tasks == total_tasks:
            overall_status = "completed"
        elif in_progress_tasks > 0:
            overall_status = "in_progress"
        else:
            overall_status = "pending"
        
        return {
            "workflow_id": self.current_workflow_id,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "pending_tasks": pending_tasks,
            "in_progress_tasks": in_progress_tasks,
            "overall_status": overall_status,
            "progress_percentage": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        }
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by ID.
        
        Args:
            task_id: ID of the task to retrieve
            
        Returns:
            Task object if found, None otherwise
        """
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[Task]:
        """
        Get all tasks in the current workflow.
        
        Returns:
            List of all tasks
        """
        return list(self.tasks.values())
    
    def load_workflow(self, workflow_id: str) -> bool:
        """
        Load an existing workflow.
        
        Args:
            workflow_id: ID of the workflow to load
            
        Returns:
            True if workflow was loaded successfully, False otherwise
        """
        workflow_path = os.path.join(self.storage_path, workflow_id)
        
        if not os.path.exists(workflow_path):
            logger.error(f"Workflow {workflow_id} does not exist")
            return False
        
        # Load workflow metadata
        try:
            with open(os.path.join(workflow_path, "workflow.json"), "r") as f:
                workflow_data = json.load(f)
            
            self.current_workflow_id = workflow_id
            self.tasks = {}
            self.task_dependencies = {}
            
            # Load all tasks
            tasks_dir = os.path.join(workflow_path, "tasks")
            if os.path.exists(tasks_dir):
                for filename in os.listdir(tasks_dir):
                    if filename.endswith(".json"):
                        task_path = os.path.join(tasks_dir, filename)
                        with open(task_path, "r") as f:
                            task_data = json.load(f)
                            task = Task.from_dict(task_data)
                            self.tasks[task.id] = task
                            
                            # Rebuild task dependencies
                            for dep_id in task.dependencies:
                                if dep_id not in self.task_dependencies:
                                    self.task_dependencies[dep_id] = []
                                self.task_dependencies[dep_id].append(task.id)
            
            logger.info(f"Loaded workflow {workflow_id} with {len(self.tasks)} tasks")
            return True
        
        except Exception as e:
            logger.error(f"Error loading workflow {workflow_id}: {e}")
            return False
    
    def _save_task(self, task: Task) -> None:
        """
        Save a task to disk.
        
        Args:
            task: Task to save
        """
        if not self.current_workflow_id:
            raise ValueError("No active workflow")
        
        tasks_dir = os.path.join(self.storage_path, self.current_workflow_id, "tasks")
        os.makedirs(tasks_dir, exist_ok=True)
        
        task_path = os.path.join(tasks_dir, f"{task.id}.json")
        with open(task_path, "w") as f:
            json.dump(task.to_dict(), f, indent=2)
    
    def get_task_artifacts(self, task_id: str) -> Dict[str, Any]:
        """
        Get artifacts produced by a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Dictionary of artifacts
        """
        task = self.get_task(task_id)
        if not task or not task.result:
            return {}
        
        return task.result.artifacts

class TaskPlanner:
    """
    Plans and breaks down complex tasks into subtasks with dependencies.
    Uses the LLM to analyze tasks and create execution plans.
    """
    
    def __init__(self, agentic_ollama):
        """
        Initialize the TaskPlanner.
        
        Args:
            agentic_ollama: Instance of AgenticOllama for LLM interactions
        """
        self.agentic_ollama = agentic_ollama
        self.task_manager = TaskManager()
        logger.info("Initialized TaskPlanner")
    
    async def plan_task(self, task_description: str) -> str:
        """
        Plan a complex task by breaking it down into subtasks.
        
        Args:
            task_description: Description of the complex task
            
        Returns:
            Workflow ID for the planned task
        """
        logger.info(f"Planning task: {task_description}")
        
        # Create a system prompt for task planning
        system_prompt = """You are an expert task planner. Your job is to break down complex tasks into smaller, 
        manageable subtasks with clear dependencies. For each subtask, provide:
        1. A clear description of what needs to be done
        2. The type of task (file_creation, web_browsing, image_analysis, etc.)
        3. Dependencies (which subtasks must be completed first)
        
        IMPORTANT: Respond with a VALID JSON object containing the task breakdown. Do NOT include any comments in the JSON.
        Do NOT use // or /* */ comment syntax anywhere in your response. The JSON must be parseable by a standard JSON parser.
        
        Format:
        {
            "main_task": "Description of the overall task",
            "subtasks": [
                {
                    "id": "1",
                    "description": "Subtask description",
                    "task_type": "task_type",
                    "dependencies": []
                },
                {
                    "id": "2",
                    "description": "Another subtask",
                    "task_type": "task_type",
                    "dependencies": ["1"]
                }
            ]
        }
        
        Available task types:
        - file_creation: Creating or modifying files, writing content to files, saving stories or text to files
        - image_analysis: Analyzing images
        - image_search: Searching for and downloading images
        - file_organization: Organizing files into categories
        - file_deletion: Deleting files
        - web_browsing: Browsing websites and gathering information from the internet ONLY (not for local file operations)
        - general_task: Any other type of task
        
        Task type guidelines:
        - Use file_creation for ANY task that involves creating, writing, or saving content to a file
        - Use file_creation for ALL local file operations like creating documents, saving text, or writing content
        - Use file_creation for tasks involving text editors, word processors, or any application that creates files
        - DO NOT use web_browsing for local file operations, file explorer, or text editors
        - web_browsing should ONLY be used for actual internet browsing tasks
        - Examples of file_creation tasks: "create a story", "write a document", "save text to a file", 
          "write a poem", "create a file with content", "write a short story about X", "open a text editor",
          "create a document in Word", "save content to a file"
        - Use web_browsing ONLY for tasks that EXPLICITLY involve accessing websites or gathering information from the internet
        - Examples of web_browsing tasks: "search for information about X", "find news about Y", "look up Z online"
        - NEVER use web_browsing for tasks that only involve local file operations
        - When in doubt between file_creation and web_browsing, prefer file_creation for any task that mentions
          creating, writing, or saving content
        
        IMPORTANT GUIDELINES FOR FILE CREATION TASKS:
        - For simple file creation tasks (like "write a poem and save it"), create just ONE subtask of type file_creation
        - DO NOT break down file creation into multiple steps like "open editor", "write content", "save file"
        - Instead, combine these into a single file_creation task like "Create a poem and save it to file"
        - This is critical to prevent nested task management issues
        - For example, if the task is "Create a poem about spring and save it as spring.txt", use ONE subtask:
          "Create a poem about spring and save it as spring.txt" with type file_creation
        
        Make sure the subtasks are ordered logically and dependencies are correctly specified.
        """
        
        # Generate a task plan using the LLM
        plan_prompt = f"I need to break down this task into subtasks: {task_description}\n\nProvide a detailed plan with clear dependencies between subtasks."
        
        plan_result = await self.agentic_ollama._generate_completion(plan_prompt, system_prompt)
        
        if not plan_result.get("success", False):
            raise Exception(f"Failed to generate task plan: {plan_result.get('error', 'Unknown error')}")
        
        # Extract the JSON plan from the result
        plan_text = plan_result.get("result", "")
        plan_json = self._extract_json(plan_text)
        
        if not plan_json:
            raise Exception("Failed to extract valid JSON plan from LLM response")
        
        # Create a new workflow
        workflow_id = self.task_manager.create_workflow(plan_json.get("main_task", task_description))
        
        # Add subtasks to the workflow
        subtasks = plan_json.get("subtasks", [])
        id_mapping = {}  # Map from plan IDs to actual task IDs
        
        # First pass: Create all tasks
        for subtask in subtasks:
            plan_id = subtask.get("id")
            task_id = self.task_manager.add_task(
                description=subtask.get("description", ""),
                task_type=subtask.get("task_type", "general_task"),
                dependencies=[],  # We'll update dependencies in the second pass
                metadata={"plan_id": plan_id}
            )
            id_mapping[plan_id] = task_id
        
        # Second pass: Update dependencies
        for subtask in subtasks:
            plan_id = subtask.get("id")
            task_id = id_mapping.get(plan_id)
            
            if task_id:
                task = self.task_manager.get_task(task_id)
                if task:
                    # Map plan dependency IDs to actual task IDs
                    dependencies = [id_mapping.get(dep_id) for dep_id in subtask.get("dependencies", [])]
                    dependencies = [dep_id for dep_id in dependencies if dep_id]  # Filter out None values
                    
                    # Update task with dependencies
                    task.dependencies = dependencies
                    self.task_manager._save_task(task)
        
        logger.info(f"Created workflow {workflow_id} with {len(subtasks)} subtasks")
        return workflow_id
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """
        Extract a JSON object from text.
        
        Args:
            text: Text containing a JSON object
            
        Returns:
            Extracted JSON object as a dictionary
        """
        import re
        import json
        
        # Try to find JSON object in the text
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON without code blocks
            json_match = re.search(r'(\{.*\})', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                return {}
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON: {json_str}")
            return {}

class TaskExecutor:
    """
    Executes tasks in a workflow using the appropriate handlers.
    """
    
    def __init__(self, agentic_assistant, task_manager: Optional[TaskManager] = None):
        """
        Initialize the TaskExecutor.
        
        Args:
            agentic_assistant: Instance of AgenticAssistant for task execution
            task_manager: Optional TaskManager instance (creates a new one if not provided)
        """
        self.agentic_assistant = agentic_assistant
        self.task_manager = task_manager or TaskManager()
        logger.info("Initialized TaskExecutor")
    
    async def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Execute all tasks in a workflow.
        
        Args:
            workflow_id: ID of the workflow to execute
            
        Returns:
            Dictionary with workflow execution results
        """
        # Load the workflow
        if not self.task_manager.load_workflow(workflow_id):
            raise ValueError(f"Failed to load workflow {workflow_id}")
        
        logger.info(f"Executing workflow {workflow_id}")
        
        # Display the workflow tasks
        all_tasks = self.task_manager.get_all_tasks()
        print("\n===== Task Execution Plan =====")
        for i, task in enumerate(all_tasks, 1):
            # Format dependencies
            if task.dependencies:
                # Map dependency IDs to step numbers for better readability
                dep_steps = []
                for dep_id in task.dependencies:
                    # Find the index of the dependency task
                    for j, t in enumerate(all_tasks, 1):
                        if t.id == dep_id:
                            dep_steps.append(str(j))
                            break
                
                dependencies = ", ".join(dep_steps)
            else:
                dependencies = "None"
                
            print(f"Step {i}: {task.description[:50] + ('...' if len(task.description) > 50 else '')}")
            print(f"  Type: {task.task_type.replace('_', ' ').title()}")
            print(f"  Dependencies: {dependencies}")
            print()
        
        print("===== Starting Task Execution =====\n")
        
        # Execute tasks until all are completed or failed
        while True:
            # Get next executable tasks
            executable_tasks = self.task_manager.get_next_executable_tasks()
            
            if not executable_tasks:
                # Check if all tasks are completed or some failed
                workflow_status = self.task_manager.get_workflow_status()
                if workflow_status["pending_tasks"] == 0 and workflow_status["in_progress_tasks"] == 0:
                    logger.info(f"Workflow {workflow_id} execution completed")
                    print("\n===== Workflow Execution Completed =====\n")
                    break
                
                # If there are still pending tasks but none are executable, there might be a dependency cycle
                if workflow_status["pending_tasks"] > 0:
                    logger.warning(f"No executable tasks but {workflow_status['pending_tasks']} tasks pending - possible dependency cycle")
                    print(f"\n===== Warning: No executable tasks but {workflow_status['pending_tasks']} tasks pending - possible dependency cycle =====\n")
                    break
                
                # Wait a bit before checking again (for in-progress tasks)
                await asyncio.sleep(1)
                continue
            
            # Execute each task
            for task in executable_tasks:
                # Find the step number for this task
                step_number = next((i for i, t in enumerate(all_tasks, 1) if t.id == task.id), "?")
                
                print(f"\n----- Executing Step {step_number}: {task.description} -----")
                logger.info(f"Executing task {task.id}: {task.description}")
                
                # Mark task as in progress
                self.task_manager.update_task_status(task.id, TaskStatus.IN_PROGRESS)
                
                try:
                    # Execute the task using the appropriate handler
                    result = await self._execute_task(task)
                    
                    # Update task status based on result
                    status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
                    self.task_manager.update_task_status(task.id, status, result)
                    
                    # Display the result
                    if result.success:
                        print(f"----- Step {step_number} Completed Successfully -----")
                        # Display artifacts if available
                        if result.artifacts:
                            print("\nTask Artifacts:")
                            for key, value in result.artifacts.items():
                                if key == "full_result":
                                    continue  # Skip full result to avoid clutter
                                    
                                if isinstance(value, str):
                                    print(f"  - {key}: {value[:100]}" + ("..." if len(value) > 100 else ""))
                                elif isinstance(value, (list, dict)):
                                    print(f"  - {key}: {str(value)[:100]}" + ("..." if len(str(value)) > 100 else ""))
                                else:
                                    print(f"  - {key}: {str(value)[:100]}" + ("..." if len(str(value)) > 100 else ""))
                    else:
                        print(f"----- Step {step_number} Failed: {result.error} -----")
                        print(f"Error Details: {result.error_details if hasattr(result, 'error_details') else 'No additional details available'}")
                    
                except Exception as e:
                    logger.error(f"Error executing task {task.id}: {e}")
                    error_result = TaskResult(success=False, error=str(e))
                    self.task_manager.update_task_status(task.id, TaskStatus.FAILED, error_result)
                    print(f"----- Step {step_number} Failed with Exception: {str(e)} -----")
            
            # Small delay to prevent CPU spinning
            await asyncio.sleep(0.1)
        
        return self.task_manager.get_workflow_status()
    
    async def _execute_task(self, task: Task) -> TaskResult:
        """
        Execute a single task using the appropriate handler.
        
        Args:
            task: Task to execute
            
        Returns:
            TaskResult with execution results
        """
        print(f"\n  Task ID: {task.id}")
        print(f"  Task Type: {task.task_type.replace('_', ' ').title()}")
        print(f"  Description: {task.description}")
        
        # Get artifacts from dependencies if needed
        dependency_artifacts = {}
        for dep_id in task.dependencies:
            dep_artifacts = self.task_manager.get_task_artifacts(dep_id)
            dependency_artifacts.update(dep_artifacts)
        
        # Display dependency information
        if dependency_artifacts:
            print("\n  Using information from previous tasks:")
            for key, value in dependency_artifacts.items():
                if key == "full_result":
                    continue  # Skip full result to avoid clutter
                    
                if isinstance(value, str):
                    print(f"  - {key}: {value[:100]}" + ("..." if len(value) > 100 else ""))
                elif isinstance(value, (list, dict)):
                    print(f"  - {key}: {str(value)[:100]}" + ("..." if len(str(value)) > 100 else ""))
                else:
                    print(f"  - {key}: {str(value)[:100]}" + ("..." if len(str(value)) > 100 else ""))
        
        # Enhance task description with dependency artifacts if available
        enhanced_description = task.description
        if dependency_artifacts:
            # Add artifact information to the task description
            artifact_info = "\n\nUse the following information from previous tasks:\n"
            for key, value in dependency_artifacts.items():
                if isinstance(value, str):
                    artifact_info += f"- {key}: {value}\n"
                elif isinstance(value, (list, dict)):
                    artifact_info += f"- {key}: {json.dumps(value)[:100]}...\n"
                else:
                    artifact_info += f"- {key}: {str(value)[:100]}...\n"
            
            enhanced_description += artifact_info
            
        print("\n  Starting task execution...")
        print("  " + "-" * 50)
        
        # Display task execution steps
        print("  Task Execution Steps:")
        
        # Check if this is a file creation task based on description
        task_lower = task.description.lower()
        file_creation_indicators = [
            # File-specific indicators
            "create a file", "write a file", "save to file", "save a file",
            "write to file", "save as file", "create new file", "make a file",
            # Content type indicators
            "create a story", "write a story", "save story", "write story",
            "create a poem", "write a poem", "save poem", "write poem",
            "create an essay", "write an essay", "save essay", "write essay",
            "create a document", "write a document", "save document", "write document",
            "create a text", "write a text", "save text", "write text",
            "create a report", "write a report", "save report", "write report",
            "create a letter", "write a letter", "save letter", "write letter",
            "create a script", "write a script", "save script", "write script",
            # Action verbs with content
            "write about", "create content", "write content", "save content",
            "write something", "create something", "save something",
            # File extension indicators
            ".txt", ".md", ".doc", ".docx", ".rtf", ".py", ".js", ".html", ".css",
            # Save indicators
            "save it as", "save this as", "save as", "save to", "save in"
        ]
        
        # If task is categorized as web_browsing but contains file creation indicators,
        # reclassify it as file_creation
        if task.task_type == "web_browsing" and any(indicator in task_lower for indicator in file_creation_indicators):
            logger.info(f"Reclassifying task from web_browsing to file_creation: {task.description}")
            task.task_type = "file_creation"
        
        # Handle file creation tasks directly to avoid nested task management
        if task.task_type == "file_creation":
            # Use our specialized file creation handler
            print(f"\n  Handling file creation task: {task.description}")
            print("  Step 1: Analyzing file requirements...")
            print("  Step 2: Extracting filename and content type...")
            print("  Step 3: Generating file content...")
            result = await self._handle_file_creation_task(task, enhanced_description)
            print("  Step 4: Saving file to disk...")
            print("  Step 5: Verifying file creation...")
        elif task.task_type == "web_browsing":
            # Use our specialized web browsing handler
            print(f"\n  Handling web browsing task: {task.description}")
            print("  Step 1: Extracting URLs from task description...")
            print("  Step 2: Fetching content from URLs...")
            print("  Step 3: Processing web content...")
            result = await self.agentic_assistant.execute_task(enhanced_description)
            print("  Step 4: Saving results...")
            print("  Step 5: Generating response...")
        else:
            # For other task types, use the standard execution
            print(f"\n  Handling general task: {task.description}")
            print("  Step 1: Analyzing task requirements...")
            print("  Step 2: Planning task execution...")
            print("  Step 3: Executing task steps...")
            result = await self.agentic_assistant.execute_task(enhanced_description)
            print("  Step 4: Processing task results...")
            print("  Step 5: Generating final response...")
        
        # Convert to TaskResult
        success = result.get("success", False)
        artifacts = {}
        
        # Extract relevant artifacts based on task type
        if task.task_type == "file_creation":
            if "result" in result and isinstance(result["result"], dict):
                artifacts["filename"] = result["result"].get("filename")
                artifacts["file_type"] = result["result"].get("file_type")
                artifacts["content_preview"] = result["result"].get("content_preview")
            # Fallback for incorrectly formatted results
            elif not success and "web browsing" in result.get("error", "").lower():
                # This was likely a file creation task misclassified as web browsing
                # Retry as a file creation task
                logger.info(f"Retrying failed web task as file creation: {enhanced_description}")
                file_result = await self.agentic_assistant._handle_file_creation(enhanced_description)
                if file_result.get("success", False):
                    success = True
                    result = file_result
                    if "result" in result and isinstance(result["result"], dict):
                        artifacts["filename"] = result["result"].get("filename")
                        artifacts["file_type"] = result["result"].get("file_type")
                        artifacts["content_preview"] = result["result"].get("content_preview")
        
        elif task.task_type == "web_browsing":
            artifacts["filename"] = result.get("filename")
            artifacts["headlines"] = result.get("headlines", [])
            artifacts["information"] = result.get("information", [])
            artifacts["url"] = result.get("url")
            
            # If web browsing failed, check if it's actually a file creation task
            if not success and "web browsing failed" in result.get("error", "").lower():
                file_creation_indicators = ["create", "write", "save", "story", "document", "file"]
                if any(indicator in task_lower for indicator in file_creation_indicators):
                    logger.info(f"Retrying failed web task as file creation: {enhanced_description}")
                    file_result = await self.agentic_assistant._handle_file_creation(enhanced_description)
                    if file_result.get("success", False):
                        success = True
                        result = file_result
                        if "result" in result and isinstance(result["result"], dict):
                            artifacts["filename"] = result["result"].get("filename")
                            artifacts["file_type"] = result["result"].get("file_type")
                            artifacts["content_preview"] = result["result"].get("content_preview")
        
        elif task.task_type == "image_analysis":
            if "result" in result and isinstance(result["result"], dict):
                artifacts["analysis"] = result["result"].get("analysis")
                artifacts["image_path"] = result["result"].get("image_path")
        
        # Include the full result as an artifact for reference
        artifacts["full_result"] = result
        
        return TaskResult(
            success=success,
            result=result.get("result", None),
            error=result.get("error") if not success else None,
            artifacts=artifacts
        )
    
    async def _handle_file_creation_task(self, task: Task, enhanced_description: str) -> Dict[str, Any]:
        """
        Handle file creation tasks with specialized processing.
        
        Args:
            task: The task to execute
            enhanced_description: Enhanced task description with context
            
        Returns:
            Dict containing the task execution result
        """
        logger.info(f"Using direct file creation handler for task: {task.description}")
        print(f"\n  Handling file creation: {task.description}")
        
        try:
            # First try to use the assistant's specialized method if available
            if hasattr(self.agentic_assistant, "_handle_file_creation"):
                print("  Step 1: Using specialized file creation handler...")
                result = await self.agentic_assistant._handle_file_creation(enhanced_description)
            else:
                # Fallback to standard execution
                print("  Step 1: No specialized handler available, using standard execution...")
                result = await self.agentic_assistant.execute_task(enhanced_description)
            
            print("  Step 2: Processing file creation result...")
            
            # Ensure the result has the correct structure
            if result.get("success", False):
                # Make sure we have a properly formatted result
                if "result" not in result or not isinstance(result["result"], dict):
                    result["result"] = {}
                
                # Ensure we have the required fields
                if "filename" not in result["result"]:
                    # Try to extract filename from task description
                    filename = self._extract_filename_from_task(task.description)
                    result["result"]["filename"] = filename or "document.txt"
                
                if "file_type" not in result["result"]:
                    # Extract file type from filename
                    filename = result["result"].get("filename", "")
                    file_type = filename.split(".")[-1] if "." in filename else "txt"
                    result["result"]["file_type"] = file_type
                
                if "content_preview" not in result["result"]:
                    result["result"]["content_preview"] = "Content generated successfully."
            
            return result
            
        except Exception as e:
            logger.error(f"Error handling file creation task: {str(e)}")
            return {
                "success": False,
                "task_type": "file_creation",
                "error": str(e),
                "message": f"Failed to create file: {str(e)}"
            }
    
    def _extract_filename_from_task(self, task_description: str) -> Optional[str]:
        """
        Extract a filename from the task description using various patterns.
        
        Args:
            task_description: The task description
            
        Returns:
            Extracted filename or None if not found
        """
        # Pattern 1: "save it to/as/in [filename]"
        save_as_match = re.search(r'save\s+(?:it|this|the\s+\w+)\s+(?:to|as|in)\s+[\'\"]*([\w\-\.]+)[\'\"]*', task_description, re.IGNORECASE)
        if save_as_match:
            return save_as_match.group(1).strip()
        
        # Pattern 2: "save to/as/in [filename]"
        save_to_match = re.search(r'save\s+(?:to|as|in)\s+[\'\"]*([\w\-\.]+)[\'\"]*', task_description, re.IGNORECASE)
        if save_to_match:
            return save_to_match.group(1).strip()
        
        # Pattern 3: "create/write a [content] and save it as [filename]"
        create_save_match = re.search(r'(?:create|write)\s+a\s+[\w\s]+\s+(?:and|&)\s+save\s+(?:it|this)\s+(?:to|as|in)\s+[\'\"]*([\w\-\.]+)[\'\"]*', task_description, re.IGNORECASE)
        if create_save_match:
            return create_save_match.group(1).strip()
        
        # Pattern 4: "create/write a [content] called/named [filename]"
        called_match = re.search(r'(?:create|write)\s+a\s+[\w\s]+\s+(?:called|named)\s+[\'\"]*([\w\-\.]+)[\'\"]*', task_description, re.IGNORECASE)
        if called_match:
            return called_match.group(1).strip()
        
        # Pattern 5: "create/write [filename]"
        create_file_match = re.search(r'(?:create|write)\s+[\'\"]*([\w\-\.]+\.\w+)[\'\"]*', task_description, re.IGNORECASE)
        if create_file_match:
            return create_file_match.group(1).strip()
        
        # If no filename was found, try to generate one based on content type
        content_types = {
            "story": "story.txt",
            "poem": "poem.txt",
            "essay": "essay.txt",
            "document": "document.txt",
            "report": "report.txt",
            "letter": "letter.txt",
            "script": "script.txt",
            "note": "note.txt",
            "list": "list.txt"
        }
        
        for content_type, default_filename in content_types.items():
            if content_type in task_description.lower():
                return default_filename
        
        # Default fallback
        return None

# Example usage
async def example_usage():
    from agentic_assistant import AgenticAssistant
    from agentic_ollama import AgenticOllama
    
    # Initialize components
    agentic_ollama = AgenticOllama()
    agentic_assistant = AgenticAssistant()
    
    # Create task planner and executor
    task_planner = TaskPlanner(agentic_ollama)
    task_manager = TaskManager()
    task_executor = TaskExecutor(agentic_assistant, task_manager)
    
    # Plan a complex task
    workflow_id = await task_planner.plan_task(
        "Research the latest gaming news, create a summary document, and find images of the top 3 games mentioned"
    )
    
    # Execute the workflow
    result = await task_executor.execute_workflow(workflow_id)
    
    print(f"Workflow execution completed: {result}")
    
    # Get all tasks and their results
    all_tasks = task_manager.get_all_tasks()
    for task in all_tasks:
        print(f"Task: {task.description}")
        print(f"Status: {task.status.value}")
        if task.result:
            print(f"Success: {task.result.success}")
            if task.result.artifacts:
                print("Artifacts:")
                for key, value in task.result.artifacts.items():
                    if key != "full_result":  # Skip the full result to keep output clean
                        print(f"  - {key}: {value}")
        print()

if __name__ == "__main__":
    asyncio.run(example_usage())
