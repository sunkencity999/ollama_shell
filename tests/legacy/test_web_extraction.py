#!/usr/bin/env python3
"""
Test script to verify web content extraction and proper file creation.
This script extracts content from multiple news sites and saves it to properly named files.
"""

import os
import logging
import asyncio
import time
from typing import List, Dict, Any
from web_browsing import WebBrowser
from agentic_ollama import AgenticOllama

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# List of news sites to test
TEST_SITES = [
    {"name": "CNN", "url": "https://www.cnn.com", "filename": "cnnTest"},
    {"name": "BBC", "url": "https://www.bbc.com", "filename": "bbcTest"},
    {"name": "Reuters", "url": "https://www.reuters.com", "filename": "reutersTest"},
    {"name": "The Guardian", "url": "https://www.theguardian.com", "filename": "guardianTest"},
    {"name": "Fox News", "url": "https://www.foxnews.com", "filename": "foxNewsTest"}
]

async def test_site_extraction(site: Dict[str, str], browser: WebBrowser, ollama_client: AgenticOllama) -> Dict[str, Any]:
    """Test content extraction and file creation for a specific site"""
    site_name = site["name"]
    url = site["url"]
    filename = site["filename"]
    
    print(f"\n=== Testing {site_name} Content Extraction and File Creation ===")
    print(f"Target URL: {url}")
    print(f"Target filename: {filename}")
    
    # Check for existing files with the target filename before extraction
    directory = os.getcwd()
    files_before = set([f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))])
    
    # Extract content from the site
    print(f"\nExtracting content from {site_name}...")
    start_time = time.time()
    result = browser.extract_structured_content_sync(url)
    extraction_time = time.time() - start_time
    print(f"Extraction completed in {extraction_time:.2f} seconds")
    
    # Check if news_content is in the result
    if 'news_content' not in result:
        print(f"❌ Failed to extract news content from {site_name}")
        return {"site": site_name, "success": False, "error": "No news content extracted"}
    
    print(f"✅ Successfully extracted news content from {site_name}")
    
    # Prepare content for file
    headlines = result['news_content'].get('headlines', [])
    main_content = result['news_content'].get('main_content', '')
    
    # Create a formatted content string
    content = f"# {site_name} Latest News\n\n"
    
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
    
    # Create the file with the specific filename
    print(f"\nSaving content to file '{filename}'...")
    
    # Create the task description with explicit filename
    task_description = f"Save the following {site_name} content to a file named '{filename}': {content[:100]}..."
    
    # Create the file
    start_time = time.time()
    result = await ollama_client.create_file(task_description, filename=filename, is_direct_content=True)
    file_creation_time = time.time() - start_time
    print(f"File creation completed in {file_creation_time:.2f} seconds")
    
    # Check if file was created successfully
    if result.get('success', False):
        print(f"✅ Successfully created file: {result.get('filename', 'unknown')}")
        
        # Check for new files after creation
        files_after = set([f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))])
        new_files = files_after - files_before
        
        # Verify the file exists and has content
        file_path = result.get('filename')
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
            
            return {
                "site": site_name, 
                "success": True, 
                "filename": file_path, 
                "file_size": file_size,
                "new_files": list(new_files)
            }
        else:
            print(f"❌ File not found at expected path: {file_path}")
            
            # Check if file was created with a different name or extension
            possible_matches = [f for f in new_files if filename in f]
            
            if possible_matches:
                print(f"Found possible matches: {possible_matches}")
                return {
                    "site": site_name, 
                    "success": False, 
                    "error": f"File created with different name",
                    "possible_matches": possible_matches,
                    "new_files": list(new_files)
                }
            else:
                return {
                    "site": site_name, 
                    "success": False, 
                    "error": "File not found",
                    "new_files": list(new_files)
                }
    else:
        print(f"❌ Failed to create file: {result.get('error', 'Unknown error')}")
        return {
            "site": site_name, 
            "success": False, 
            "error": result.get('error', 'Unknown error')
        }

async def run_tests():
    """Run tests for all sites"""
    # Initialize components
    print("Initializing components...")
    ollama_client = AgenticOllama()
    browser = WebBrowser(ollama_client)
    
    results = []
    
    # Test each site
    for site in TEST_SITES:
        result = await test_site_extraction(site, browser, ollama_client)
        results.append(result)
        
        # Small delay between tests
        await asyncio.sleep(2)
    
    # Print summary
    print("\n=== Test Summary ===")
    for result in results:
        site = result["site"]
        success = result["success"]
        status = "✅ Success" if success else f"❌ Failed: {result.get('error', 'Unknown error')}"
        print(f"{site}: {status}")
        
        if success:
            print(f"  - File: {result['filename']}")
            print(f"  - Size: {result['file_size']} bytes")
            if result.get('new_files'):
                if len(result['new_files']) > 1:
                    print(f"  - WARNING: Created {len(result['new_files'])} files: {result['new_files']}")
                else:
                    print(f"  - Created 1 file: {result['new_files'][0]}")
        elif result.get('possible_matches'):
            print(f"  - Possible matches: {result['possible_matches']}")
        
        if result.get('new_files') and len(result['new_files']) > 1:
            print(f"  - Multiple files created: {result['new_files']}")
    
    # Overall success/failure
    success_count = sum(1 for r in results if r["success"])
    print(f"\nOverall: {success_count}/{len(results)} tests passed")

if __name__ == "__main__":
    asyncio.run(run_tests())
