#!/usr/bin/env python3
"""
Test script for the enhanced web browsing capabilities with Selenium WebDriver.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent))

# Import the enhanced agentic assistant
from agentic_assistant_enhanced import EnhancedAgenticAssistant

async def test_enhanced_web_browsing():
    """Test the enhanced web browsing capabilities."""
    print("Initializing Enhanced Agentic Assistant...")
    assistant = EnhancedAgenticAssistant()
    
    # Test cases for different advanced web browsing capabilities
    test_cases = [
        {
            "name": "Screenshot Test",
            "task": "Take a screenshot of https://example.com and save it",
            "expected_capability": "screenshot"
        },
        {
            "name": "Structured Content Test",
            "task": "Extract structured content from https://example.com including headings and links",
            "expected_capability": "structured content"
        },
        {
            "name": "Scrolling Test",
            "task": "Scroll down on https://example.com and extract the content",
            "expected_capability": "scrolling"
        },
        {
            "name": "JavaScript-heavy Site Test",
            "task": "Visit the dynamic SPA at https://www.example.com and extract content",
            "expected_capability": "JavaScript rendering"
        }
    ]
    
    # Run each test case
    for test_case in test_cases:
        print(f"\n\n{'=' * 50}")
        print(f"Running Test: {test_case['name']}")
        print(f"Task: {test_case['task']}")
        print(f"Expected Capability: {test_case['expected_capability']}")
        print(f"{'=' * 50}\n")
        
        # Execute the task
        try:
            result = await assistant.execute_task(test_case['task'])
            
            # Print the result
            print(f"\nTest Result:")
            print(f"Success: {result.get('success', False)}")
            print(f"Message: {result.get('message', 'No message')}")
            
            # Print artifacts if available
            if 'artifacts' in result:
                print("\nArtifacts:")
                for key, value in result['artifacts'].items():
                    if key == 'content':
                        print(f"  {key}: [Content length: {len(str(value))} characters]")
                    elif key == 'screenshot':
                        print(f"  {key}: [Screenshot data available]")
                    elif key == 'structured_data':
                        print(f"  {key}:")
                        for data_key, data_value in value.items():
                            if isinstance(data_value, list):
                                print(f"    {data_key}: [{len(data_value)} items]")
                            else:
                                print(f"    {data_key}: {data_value}")
                    else:
                        if isinstance(value, str) and len(value) > 100:
                            print(f"  {key}: {value[:100]}...")
                        else:
                            print(f"  {key}: {value}")
            
            print(f"\nTest {'PASSED' if result.get('success', False) else 'FAILED'}")
        
        except Exception as e:
            print(f"Error executing task: {str(e)}")
            print("Test FAILED")
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    asyncio.run(test_enhanced_web_browsing())
