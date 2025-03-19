#!/usr/bin/env python3
"""
Comprehensive test script to verify both task classification and filename extraction.
"""

import re
import logging
from agentic_assistant_enhanced import EnhancedAgenticAssistant

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_task_classification_and_filename_extraction():
    """Test both task classification and filename extraction together."""
    print("\n===== Testing Task Classification and Filename Extraction =====")
    
    # Create an instance of the enhanced assistant
    assistant = EnhancedAgenticAssistant()
    
    # Test cases for both task classification and filename extraction
    test_cases = [
        # Complex tasks with both web browsing and file creation
        "Please analyze the headlines of CNN.com, save them in a file, and then create a report about the broad concerns of humanity based on the content of those headlines named \"CNNReport\".",
        "Visit nytimes.com, read the top stories, and create a summary named \"NYTimesSummary\".",
        "Go to bbc.co.uk and write a report on the current events named \"BBCReport\".",
        
        # Web browsing tasks with domain names
        "Browse to github.com and find popular Python repositories",
        "Visit cnn.com and check the latest news",
        
        # Web browsing tasks with URLs
        "Go to https://www.example.com and read the documentation",
        "Check out https://www.github.com/microsoft/vscode",
        
        # File creation tasks with explicit filenames
        "Write a story about dragons and save it as \"DragonTale.txt\"",
        "Create a poem about the ocean and save it in a file named \"OceanPoem\"",
        
        # File creation tasks without explicit filenames
        "Write a short story about a detective solving a mystery",
        "Create a list of the best movies of all time"
    ]
    
    # Test each case
    for i, task in enumerate(test_cases):
        is_file_creation = assistant._is_direct_file_creation_task(task)
        task_type = "file_creation" if is_file_creation else "web_browsing"
        
        # Extract filename if it's a file creation task
        filename = assistant._extract_filename(task) if is_file_creation else "N/A"
        
        # Check for URLs and domains
        url_pattern = r'https?://[^\s]+'
        # More precise domain pattern to avoid false positives
        domain_pattern = r'\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:com|org|net|edu|gov|io|ai|co\.uk|co)\b'
        
        has_url = bool(re.search(url_pattern, task, re.IGNORECASE))
        has_domain = bool(re.search(domain_pattern, task, re.IGNORECASE))
        
        print(f"Test {i+1}: '{task}'")
        print(f"  Classified as: {task_type}")
        print(f"  Extracted filename: '{filename}'")
        print(f"  Contains URL: {has_url}")
        print(f"  Contains domain: {has_domain}")
        print()

def main():
    """Main function to run all tests."""
    print("===== Comprehensive Testing =====")
    
    # Test task classification and filename extraction
    test_task_classification_and_filename_extraction()
    
    print("\n===== All Tests Completed =====")

if __name__ == "__main__":
    main()
