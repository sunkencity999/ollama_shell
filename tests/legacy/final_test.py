import asyncio
import logging
import os
from glama_mcp_integration import LocalWebIntegration

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_full_workflow():
    print("\n" + "="*80)
    print("TESTING COMPLETE WEB SEARCH WORKFLOW")
    print("="*80)
    
    lwi = LocalWebIntegration()
    
    # Test query
    query = "Find information about the best fishing spots in California"
    print(f"\nOriginal query: {query}")
    
    # Execute the web task
    result = await lwi.execute_web_task(query)
    
    # Display results
    print("\n" + "="*80)
    print("EXECUTION RESULTS")
    print("="*80)
    print(f"\nSuccess: {result.get('success', False)}")
    
    # The file path might be in different places depending on the implementation
    file_path = None
    
    # Check direct file_path attribute
    if 'file_path' in result:
        file_path = result['file_path']
    
    # Check message for file path
    elif 'message' in result and isinstance(result['message'], str):
        import re
        match = re.search(r'saved to ([^\s]+)', result['message'])
        if match:
            file_path = match.group(1)
    
    # Hardcode the expected path as fallback
    if not file_path:
        file_path = "/Users/christopher.bradford/Documents/fishing_guide.txt"
        # Verify it exists
        import os
        if not os.path.exists(file_path):
            file_path = None
    
    print(f"\nFile path: {file_path or 'No file created'}")
    
    if file_path:
        print("\nFile content preview:")
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                preview = content[:500] + "..." if len(content) > 500 else content
                print("-"*50)
                print(preview)
                print("-"*50)
        except Exception as e:
            print(f"Error reading file: {e}")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_full_workflow())
