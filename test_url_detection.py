#!/usr/bin/env python3
"""
Test script to verify URL detection in web browsing tasks.
"""

import re
import logging
from agentic_assistant_enhanced import EnhancedAgenticAssistant

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_url_detection():
    """Test the URL detection functionality."""
    print("\n===== Testing URL Detection =====")
    
    # Create an instance of the enhanced assistant
    assistant = EnhancedAgenticAssistant()
    
    # Test cases for URL detection
    test_cases = [
        # Clear URL tasks
        "Visit https://www.cnn.com",
        "Browse to https://www.example.com",
        "Go to http://www.bbc.co.uk",
        "Check out https://www.github.com/microsoft/vscode",
        "Open the URL https://www.python.org/downloads/",
        
        # Domain name tasks
        "Visit cnn.com",
        "Browse to example.com",
        "Go to bbc.co.uk",
        "Check out github.com",
        "Open python.org",
        
        # Tasks with URLs in the middle
        "Research information on https://www.wikipedia.org about quantum physics",
        "Find data from cnn.com about recent elections",
        "Look for articles on nytimes.com about climate change",
        
        # Complex tasks with URLs
        "Analyze the headlines on CNN.com and create a summary",
        "Visit https://www.bbc.co.uk and summarize the top stories",
        "Browse to github.com and find popular Python repositories"
    ]
    
    # Test each case
    for i, task in enumerate(test_cases):
        is_file_creation = assistant._is_direct_file_creation_task(task)
        task_type = "file_creation" if is_file_creation else "web_browsing"
        
        # Check if the task contains a URL
        url_pattern = r'https?://[^\s]+'
        domain_pattern = r'\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]\b'
        
        has_url = bool(re.search(url_pattern, task, re.IGNORECASE))
        has_domain = bool(re.search(domain_pattern, task, re.IGNORECASE))
        
        print(f"Test {i+1}: '{task}'")
        print(f"  Classified as: {task_type}")
        print(f"  Contains URL: {has_url}")
        print(f"  Contains domain: {has_domain}")
        print()

def main():
    """Main function to run all tests."""
    print("===== Testing URL Detection =====")
    
    # Test URL detection
    test_url_detection()
    
    print("\n===== All Tests Completed =====")

if __name__ == "__main__":
    main()
