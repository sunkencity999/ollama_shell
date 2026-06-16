#!/usr/bin/env python3
import asyncio
import os
import json
import logging
import unittest.mock as mock
from agentic_assistant_enhanced import EnhancedAgenticAssistant
from agentic_ollama import AgenticOllama
from task_manager import TaskManager, TaskPlanner, TaskExecutor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Mock responses for testing
def mock_create_file(*args, **kwargs):
    """Mock the create_file method to return a successful result"""
    request = args[0] if args else kwargs.get('request', '')
    filename = args[1] if len(args) > 1 else kwargs.get('filename', 'test_file.txt')
    
    if not filename:
        # Extract a simple filename from the request
        if 'poem' in request.lower():
            filename = 'poem.txt'
        elif 'story' in request.lower():
            filename = 'story.txt'
        elif 'essay' in request.lower():
            filename = 'essay.txt'
        else:
            filename = 'document.txt'
    
    # Create a mock content based on the request
    content = f"This is a mock content for: {request}"
    content_preview = content[:100] + '...' if len(content) > 100 else content
    
    return {
        "success": True,
        "message": "File created successfully",
        "result": {
            "filename": filename,
            "file_type": filename.split('.')[-1],
            "content": content,
            "content_preview": content_preview
        }
    }

async def test_direct_file_creation():
    """Test direct file creation with the Enhanced Agentic Assistant"""
    print("\n=== Testing Direct File Creation ===\n")
    
    # Initialize the Enhanced Agentic Assistant with mocked AgenticOllama
    assistant = EnhancedAgenticAssistant()
    
    # Mock the create_file method in the agentic_ollama instance
    assistant.agentic_ollama.create_file = mock.AsyncMock(side_effect=mock_create_file)
    
    # Test cases for direct file creation
    test_cases = [
        "Create a file with a short story about a boy who loves ham sandwiches in Africa",
        "Write a poem about the sunset and save it as sunset_poem.txt",
        "Create a document called shopping_list.txt with items I need to buy",
        "Write an essay about artificial intelligence"
    ]
    
    for i, task_description in enumerate(test_cases):
        print(f"\nTest Case {i+1}: {task_description}")
        
        # Execute the task
        result = await assistant.execute_task(task_description)
        
        # Print the result summary
        success = result.get("success", False)
        print(f"Success: {success}")
        
        if success and "result" in result and isinstance(result["result"], dict):
            filename = result["result"].get("filename", "Unknown")
            content_preview = result["result"].get("content_preview", "No preview available")
            print(f"Filename: {filename}")
            print(f"Content Preview: {content_preview[:100]}...")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")

async def test_complex_task_file_creation():
    """Test file creation through the task management system"""
    print("\n=== Testing Complex Task File Creation ===\n")
    
    # Initialize components with mocks
    agentic_ollama = AgenticOllama()
    agentic_ollama.create_file = mock.AsyncMock(side_effect=mock_create_file)
    agentic_ollama._generate_completion = mock.AsyncMock(return_value={
        "success": True,
        "result": json.dumps({
            "main_task": "Create a document about the topic",
            "subtasks": [
                {
                    "id": "1",
                    "description": "Research information about the topic",
                    "task_type": "web_browsing",
                    "dependencies": []
                },
                {
                    "id": "2",
                    "description": "Create a document summarizing the information",
                    "task_type": "file_creation",
                    "dependencies": ["1"]
                }
            ]
        })
    })
    
    assistant = EnhancedAgenticAssistant()
    assistant.agentic_ollama.create_file = mock.AsyncMock(side_effect=mock_create_file)
    assistant.execute_task = mock.AsyncMock(return_value={
        "success": True,
        "task_type": "web_browsing",
        "result": {
            "information": ["Mock information about the topic"],
            "headlines": ["Mock headline 1", "Mock headline 2"],
            "url": "https://example.com"
        }
    })
    
    task_planner = TaskPlanner(agentic_ollama)
    task_executor = TaskExecutor(assistant)
    
    # Test cases for complex tasks that include file creation
    test_cases = [
        "Research the benefits of meditation and create a summary document",
        "Find information about healthy eating habits and write a short guide"
    ]
    
    for i, task_description in enumerate(test_cases):
        print(f"\nComplex Test Case {i+1}: {task_description}")
        
        try:
            # Plan the task
            workflow_id = await task_planner.plan_task(task_description)
            print(f"Created workflow: {workflow_id}")
            
            # Execute the workflow
            result = await task_executor.execute_workflow(workflow_id)
            print(f"Workflow execution completed with {result['completed_tasks']} completed tasks and {result['failed_tasks']} failed tasks")
            
            # Get all tasks and their results
            all_tasks = task_executor.task_manager.get_all_tasks()
            for task in all_tasks:
                print(f"Task: {task.description}")
                print(f"Type: {task.task_type}")
                print(f"Status: {task.status.value}")
                if task.result:
                    print(f"Success: {task.result.success}")
                    if task.result.artifacts:
                        print("Artifacts:")
                        for key, value in task.result.artifacts.items():
                            if key != "full_result":  # Skip the full result to keep output clean
                                if isinstance(value, str) and len(value) > 100:
                                    print(f"  - {key}: {value[:100]}...")
                                else:
                                    print(f"  - {key}: {value}")
                print()
                
        except Exception as e:
            logger.error(f"Error executing complex task: {e}")
            print(f"Error: {str(e)}")

async def test_direct_file_creation_handler():
    """Test the _handle_file_creation method directly"""
    print("\n=== Testing Direct File Creation Handler ===\n")
    
    # Initialize the Enhanced Agentic Assistant
    assistant = EnhancedAgenticAssistant()
    
    # Mock the create_file method in the agentic_ollama instance
    assistant.agentic_ollama.create_file = mock.AsyncMock(side_effect=mock_create_file)
    
    # Test cases for the direct file creation handler
    test_cases = [
        "Write a short story about a girl who discovers a magical tree in her backyard and save it as magical_tree.txt",
        "Create a poem about the ocean and save it as ocean_poem.txt"
    ]
    
    for i, task_description in enumerate(test_cases):
        print(f"\nHandler Test Case {i+1}: {task_description}")
        
        # Call the handler directly
        result = await assistant._handle_file_creation(task_description)
        
        # Print the result summary
        success = result.get("success", False)
        print(f"Success: {success}")
        
        if success and "result" in result and isinstance(result["result"], dict):
            filename = result["result"].get("filename", "Unknown")
            content_preview = result["result"].get("content_preview", "No preview available")
            print(f"Filename: {filename}")
            print(f"Content Preview: {content_preview[:100]}...")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")

async def run_all_tests():
    """Run all test cases"""
    print("Starting file creation tests...\n")
    
    # Run all test functions
    await test_direct_file_creation()
    await test_direct_file_creation_handler()
    await test_complex_task_file_creation()
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
