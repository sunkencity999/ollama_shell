import asyncio
import logging
from web_browsing import WebBrowser

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_cnn_extraction():
    """Test the CNN content extraction functionality"""
    print("Initializing WebBrowser...")
    browser = WebBrowser(None)  # Pass None as we don't need the Ollama client for this test
    
    print("Testing CNN headline extraction...")
    result = await browser.browse_web('Get headlines from CNN')
    
    print("\n=== RESULT ===")
    if result.get('success', False):
        print("Successfully extracted content from CNN")
        if 'headlines' in result:
            print(f"\nHeadlines ({len(result['headlines'])}):")
            for headline in result['headlines']:
                print(f"- {headline}")
        else:
            print("No headlines found")
    else:
        print(f"Failed to extract content: {result.get('error', 'Unknown error')}")
    
    print("\nDone!")

if __name__ == "__main__":
    asyncio.run(test_cnn_extraction())
