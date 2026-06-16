import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
import os
import logging
from glama_mcp_integration import LocalWebIntegration

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def gather_cyberdeck_info():
    # Specialized websites that might have information about cyberdecks
    cyberdeck_websites = [
        "https://cyberdeck.cafe",
        "https://hackaday.com/tag/cyberdeck/",
        "https://www.reddit.com/r/cyberdeck/",
        "https://www.instructables.com/search/?q=cyberdeck",
        "https://www.raspberrypi.org/search/cyberdeck/"
    ]
    
    lwi = LocalWebIntegration()
    
    # Create a more specific query about cyberdecks
    query = "What are cyberdecks, their origins, uses, and how people build them"
    
    # Gather information from specialized websites
    result = await lwi.gather_information(cyberdeck_websites, query)
    
    if result.get('success'):
        # Save the content to the specified file
        output_path = os.path.expanduser("~/Documents/cyberdecks.txt")
        with open(output_path, "w") as f:
            f.write(result.get('content', 'No content found'))
        
        print(f"Successfully saved cyberdeck information to {output_path}")
        print("\nPreview of content:")
        print("-" * 50)
        content = result.get('content', '')
        print(content[:500] + "..." if len(content) > 500 else content)
        print("-" * 50)
    else:
        print(f"Failed to gather information: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(gather_cyberdeck_info())
