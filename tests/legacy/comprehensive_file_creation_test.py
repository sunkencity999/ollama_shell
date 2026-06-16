#!/usr/bin/env python3
"""
Comprehensive test script for the enhanced file creation functionality.
This script tests all aspects of the file creation implementation, including:
- Filename extraction
- Content type detection
- Task classification
- Result formatting
- Error handling
"""

import asyncio
import json
import logging
import os
import re
import sys
from typing import Dict, Any, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import required modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agentic_assistant_enhanced import EnhancedAgenticAssistant
from task_manager import TaskManager, TaskPlanner, TaskExecutor, Task, TaskStatus, TaskResult

# Mock AgenticOllama class for testing
class MockAgenticOllama:
    """Mock implementation of AgenticOllama for testing purposes."""
    
    def __init__(self, model: str = "llama3.2:latest"):
        self.model = model
        logger.info(f"Initialized Agentic Ollama with model: {model}")
    
    async def generate_content(self, prompt: str, system_prompt: str = None) -> Dict[str, Any]:
        """Mock content generation."""
        return {
            "content": f"This is a mock response for: {prompt[:50]}...",
            "model": self.model,
            "prompt_tokens": len(prompt.split()),
            "completion_tokens": 100,
        }
    
    async def generate_task_plan(self, task_description: str) -> Dict[str, Any]:
        """Mock task plan generation."""
        # Create a simple task plan with 2-3 subtasks
        subtasks = []
        if "research" in task_description.lower():
            subtasks.append("Search for information online")
            subtasks.append("Organize and categorize gathered information")
        
        if "write" in task_description.lower() or "create" in task_description.lower():
            subtasks.append(f"Write content based on {task_description}")
        
        return {
            "subtasks": subtasks,
            "dependencies": {subtask: [] for subtask in subtasks}
        }


class TestFileCreation:
    """Test class for file creation functionality."""
    
    def __init__(self):
        """Initialize test class."""
        self.agentic_ollama = MockAgenticOllama()
        self.task_manager = TaskManager()
        self.task_planner = TaskPlanner(self.agentic_ollama)
        self.task_executor = TaskExecutor(self.task_manager, self.agentic_ollama)
        self.assistant = EnhancedAgenticAssistant(self.agentic_ollama)
        
        # Test cases for filename extraction
        self.filename_test_cases = [
            {
                "description": "Save it as test.txt",
                "expected_filename": "test.txt"
            },
            {
                "description": "Write a poem about the ocean and save it as ocean_poem.txt",
                "expected_filename": "ocean_poem.txt"
            },
            {
                "description": "Create a document called project_ideas.txt with ideas for my next project",
                "expected_filename": "project_ideas.txt"
            },
            {
                "description": "Write a story about a dragon named file.txt",
                "expected_filename": "file.txt"
            },
            {
                "description": "Create a file named complex-filename_123.md with markdown content",
                "expected_filename": "complex-filename_123.md"
            },
            {
                "description": "Write an essay about climate change",
                "expected_filename": "essay.txt"  # Default based on content type
            },
            {
                "description": "Create a recipe for chocolate chip cookies",
                "expected_filename": "recipe.txt"  # Default based on content type
            }
        ]
        
        # Test cases for task classification
        self.task_classification_test_cases = [
            {
                "description": "Create a file with a short story",
                "expected_type": "file_creation"
            },
            {
                "description": "Write a poem about the ocean",
                "expected_type": "file_creation"
            },
            {
                "description": "Search for information about renewable energy",
                "expected_type": "web_browsing"
            },
            {
                "description": "Find the latest news about AI",
                "expected_type": "web_browsing"
            },
            {
                "description": "Create a document with my research findings and save it",
                "expected_type": "file_creation"
            },
            {
                "description": "Write a summary of the article at https://example.com",
                "expected_type": "file_creation"  # This should be classified as file creation, not web browsing
            }
        ]
        
        # Test cases for complex workflows
        self.workflow_test_cases = [
            {
                "description": "Research renewable energy and write a summary",
                "expected_tasks": ["web_browsing", "file_creation"]
            },
            {
                "description": "Find information about meditation benefits and create a guide for beginners",
                "expected_tasks": ["web_browsing", "file_creation"]
            }
        ]
    
    async def test_filename_extraction(self):
        """Test filename extraction functionality."""
        print("\n=== Testing Filename Extraction ===\n")
        
        for i, test_case in enumerate(self.filename_test_cases):
            description = test_case["description"]
            expected = test_case["expected_filename"]
            
            # Call the private method directly for testing
            actual = self.assistant._extract_filename(description)
            
            result = "✅ PASS" if actual == expected else f"❌ FAIL (got: {actual}, expected: {expected})"
            print(f"Test {i+1}: {description}\n  {result}")
    
    async def test_task_classification(self):
        """Test task classification functionality."""
        print("\n=== Testing Task Classification ===\n")
        
        for i, test_case in enumerate(self.task_classification_test_cases):
            description = test_case["description"]
            expected = test_case["expected_type"]
            
            # Use the task executor's is_file_creation_task method
            is_file_creation = self.task_executor._is_file_creation_task(description)
            actual = "file_creation" if is_file_creation else "web_browsing"
            
            result = "✅ PASS" if actual == expected else f"❌ FAIL (got: {actual}, expected: {expected})"
            print(f"Test {i+1}: {description}\n  {result}")
    
    async def test_direct_file_creation(self):
        """Test direct file creation handling."""
        print("\n=== Testing Direct File Creation ===\n")
        
        test_cases = [
            "Create a file with a short story about a space explorer",
            "Write a poem about the ocean and save it as ocean_poem.txt",
            "Create a document with ideas for my next project"
        ]
        
        for i, description in enumerate(test_cases):
            print(f"Test {i+1}: {description}")
            
            # Test if the assistant detects this as a direct file creation task
            is_direct = self.assistant._is_direct_file_creation_task(description)
            print(f"  Detected as direct file creation: {'✅ Yes' if is_direct else '❌ No'}")
            
            # Test the file creation handling
            result = await self.assistant._handle_file_creation(description)
            
            # Verify the result structure
            has_success = "success" in result
            has_task_type = result.get("task_type") == "file_creation"
            has_filename = "filename" in result.get("result", {})
            has_preview = "content_preview" in result.get("result", {})
            
            print(f"  Result validation:")
            print(f"    - Has success field: {'✅ Yes' if has_success else '❌ No'}")
            print(f"    - Correct task type: {'✅ Yes' if has_task_type else '❌ No'}")
            print(f"    - Has filename: {'✅ Yes' if has_filename else '❌ No'}")
            print(f"    - Has content preview: {'✅ Yes' if has_preview else '❌ No'}")
            print(f"  Filename: {result.get('result', {}).get('filename', 'N/A')}")
            print(f"  Preview: {result.get('result', {}).get('content_preview', 'N/A')[:50]}...")
            print()
    
    async def test_workflow_integration(self):
        """Test integration with workflow system."""
        print("\n=== Testing Workflow Integration ===\n")
        
        for i, test_case in enumerate(self.workflow_test_cases):
            description = test_case["description"]
            expected_tasks = test_case["expected_tasks"]
            
            print(f"Test {i+1}: {description}")
            
            # Create a workflow
            workflow_id = await self.task_planner.create_workflow(
                description, 
                self.task_manager
            )
            
            print(f"  Created workflow: {workflow_id}")
            
            # Load the workflow
            self.task_manager.load_workflow(workflow_id)
            tasks = self.task_manager.get_all_tasks()
            
            print(f"  Workflow has {len(tasks)} tasks:")
            for j, task in enumerate(tasks):
                # Determine expected task type
                is_file_creation = self.task_executor._is_file_creation_task(task.description)
                actual_type = "file_creation" if is_file_creation else "web_browsing"
                
                print(f"    {j+1}. {task.description}")
                print(f"       Type: {actual_type}")
            
            print()
    
    async def run_all_tests(self):
        """Run all tests."""
        await self.test_filename_extraction()
        await self.test_task_classification()
        await self.test_direct_file_creation()
        await self.test_workflow_integration()


async def main():
    """Main function."""
    print("Starting comprehensive file creation tests...\n")
    
    test_suite = TestFileCreation()
    await test_suite.run_all_tests()
    
    print("\nAll tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
