#!/usr/bin/env python3
"""
Test script to verify CNN content extraction and proper file creation.
This script extracts content from CNN and saves it to a single file named 'cnnTest'.
"""

import os
import logging
from web_browsing import WebBrowser
from agentic_ollama import AgenticOllama

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_cnn_extraction_and_file_creation():
    """Test CNN content extraction and file creation with specific filename"""
    print("\n=== Testing CNN Content Extraction and File Creation ===")
    
    # Initialize components
    print("Initializing components...")
    ollama_client = AgenticOllama()
    browser = WebBrowser(ollama_client)
    
    # Test URL - CNN front page
    url = "https://www.cnn.com"
    print(f"Target URL: {url}")
    
    # Extract content from CNN
    print("\nExtracting content from CNN...")
    result = browser.extract_structured_content_sync(url)
    
    # Check if news_content is in the result
    if 'news_content' not in result:
        print("❌ Failed to extract news content from CNN")
        return
    
    print("✅ Successfully extracted news content from CNN")
    
    # Prepare content for file
    headlines = result['news_content'].get('headlines', [])
    main_content = result['news_content'].get('main_content', '')
    
    # Create a formatted content string
    content = "# CNN Latest News\n\n"
    
    # Add headlines
    if headlines:
        content += "## Top Headlines\n\n"
        for headline in headlines[:10]:  # Limit to top 10 headlines
            content += f"- {headline}\n"
        content += "\n"
    
    # Add main content
    if main_content:
        content += "## Content\n\n"
        content += main_content
    
    # Define the specific filename we want
    filename = "cnnTest"
    
    # Create the file with the specific filename
    print(f"\nSaving content to file '{filename}'...")
    
    # Create the task description with explicit filename
    task_description = f"Save the following CNN content to a file named '{filename}': {content[:100]}..."
    
    # Create the file
    result = await ollama_client.create_file(task_description)
    
    # Check if file was created successfully
    if result.get('success', False):
        print(f"✅ Successfully created file: {result.get('filename', 'unknown')}")
        
        # Verify the file exists and has content
        file_path = os.path.join(os.getcwd(), filename)
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"File exists at: {file_path}")
            print(f"File size: {file_size} bytes")
            
            # Read and display a preview of the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read(500)  # Read first 500 chars
                print("\nFile content preview:")
                print("-" * 40)
                print(file_content)
                print("-" * 40)
                if len(file_content) >= 500:
                    print("... (content truncated)")
        else:
            print(f"❌ File not found at expected path: {file_path}")
            
            # Check if file was created with a different name or extension
            directory = os.getcwd()
            files = os.listdir(directory)
            possible_matches = [f for f in files if f.startswith(filename) or f.endswith(filename)]
            
            if possible_matches:
                print(f"Found possible matches: {possible_matches}")
    else:
        print(f"❌ Failed to create file: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_cnn_extraction_and_file_creation())
