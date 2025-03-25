import asyncio
import os
from web_browsing import WebBrowser
from unittest.mock import MagicMock

async def test_search():
    """Test the web browsing functionality with a search query."""
    print("Testing web browsing with search query...")
    
    # Create a mock Ollama client
    mock_ollama_client = MagicMock()
    
    # Initialize the WebBrowser with the mock client
    browser = WebBrowser(ollama_client=mock_ollama_client)
    
    # Execute the browse_web method with a search query
    result = await browser.browse_web(
        task_description="search for current facts about George Foreman and save to george.doc"
    )
    
    # Check for the file in the user's Documents directory
    documents_dir = os.path.expanduser("~/Documents")
    expected_file = os.path.join(documents_dir, "george.doc")
    
    if os.path.exists(expected_file):
        print(f"Success! Found the file at: {expected_file}")
        print(f"File size: {os.path.getsize(expected_file)} bytes")
        # Print the first few lines of the file
        with open(expected_file, 'r') as f:
            content = f.read(500)  # Read first 500 bytes
            print(f"File preview: {content[:200]}...")
    else:
        print(f"File not found at expected location: {expected_file}")
        print("Looking for alternative files that might contain George Foreman information...")
        for filename in os.listdir(documents_dir):
            if "george" in filename.lower() or "foreman" in filename.lower():
                found_file = os.path.join(documents_dir, filename)
                print(f"Found potential file: {found_file}")
    
    # Print the result
    print(f"Success: {result['success']}")
    if not result['success']:
        print(f"Error: {result['message']}")
    else:
        print(f"Message: {result['message']}")
        print(f"Artifacts: {list(result['artifacts'].keys())}")
        
        # Check if the file was created in the Documents directory
        documents_dir = os.path.expanduser("~/Documents")
        expected_file = os.path.join(documents_dir, "george.doc")
        if os.path.exists(expected_file):
            print(f"File created: {expected_file}")
            with open(expected_file, "r") as f:
                content = f.read()
                print(f"File content preview: {content[:200]}...")
        else:
            print("File was not created in the expected location.")

if __name__ == "__main__":
    asyncio.run(test_search())
