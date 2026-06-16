#!/usr/bin/env python3
"""
Test script to verify web browsing task detection.
This script tests:
1. Detection of web browsing tasks
2. Proper handling of tasks that involve both web browsing and file creation
"""

import os
import sys
import logging
from agentic_assistant_enhanced import EnhancedAgenticAssistant

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_web_browsing_detection():
    """Test the web browsing task detection functionality."""
    print("\n===== Testing Web Browsing Task Detection =====")
    
    # Create an instance of the enhanced assistant
    assistant = EnhancedAgenticAssistant()
    
    # Test cases for web browsing detection
    test_cases = [
        # Clear web browsing tasks
        "Search for the latest news on AI",
        "Find information about climate change online",
        "Browse to cnn.com",
        "Visit https://www.example.com",
        "Look up information about quantum computing",
        "Research the history of artificial intelligence",
        "Find recent papers on machine learning",
        
        # Tasks with domain names
        "Go to google.com",
        "Check out the latest news on bbc.co.uk",
        "Visit stackoverflow.com for programming help",
        "Look at the documentation on python.org",
        
        # Tasks with URLs
        "Browse to https://www.github.com",
        "Visit http://arxiv.org for research papers",
        "Check out https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        
        # Complex tasks (web browsing + file creation)
        "Research the latest AI developments and create a summary named ai_summary",
        "Find information about climate change and save it to a file named climate_report",
        "Analyze the headlines of CNN.com and save the results as cnn_analysis.txt",
        "Search for recent space discoveries and compile them into a report",
        "Look up information about quantum computing on the web and create a summary"
    ]
    
    # Test each case
    for i, task in enumerate(test_cases):
        is_file_creation = assistant._is_direct_file_creation_task(task)
        task_type = "file_creation" if is_file_creation else "web_browsing"
        print(f"Test {i+1}: '{task}'")
        print(f"  Classified as: {task_type}")
        
        # For complex tasks, check if they contain web browsing elements
        if "Research" in task or "Find" in task or "Search" in task or "Look up" in task:
            contains_web = any(domain in task.lower() for domain in [".com", ".org", ".net", ".edu", ".gov", ".io", ".ai", ".co", ".uk"])
            contains_web = contains_web or any(term in task.lower() for term in ["search", "browse", "visit", "look up", "research", "find"])
            print(f"  Contains web browsing elements: {contains_web}")
        
        print()

def main():
    """Main function to run all tests."""
    print("===== Testing Web Browsing Task Detection =====")
    
    # Test web browsing detection
    test_web_browsing_detection()
    
    print("\n===== All Tests Completed =====")

if __name__ == "__main__":
    main()
