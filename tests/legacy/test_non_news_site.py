#!/usr/bin/env python3
"""
Test script for browsing non-news sites to verify the fix for the looping issue.
"""

import os
import sys
import logging
import json
import asyncio
from web_browsing import WebBrowser

# Mock OllamaClient for testing
class MockOllamaClient:
    def __init__(self):
        pass
        
    async def generate(self, prompt, model=None):
        return {"response": "This is a mock response"}

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_non_news_site')

async def run_test():
    """Run the actual test asynchronously."""
    # Create a WebBrowser instance with a mock ollama_client
    ollama_client = MockOllamaClient()
    browser = WebBrowser(ollama_client)
    
    # Test URLs (non-news sites)
    test_urls = [
        "https://www.google.com",
        "https://www.github.com",
        "https://www.stackoverflow.com"
    ]
    
    for url in test_urls:
        logger.info(f"Testing non-news site: {url}")
        try:
            # Use the extract_structured_content_sync method which had the issue
            result = browser.extract_structured_content_sync(url)
            
            # Check if the extraction was successful
            if result:
                logger.info(f"Successfully extracted content from {url}")
                logger.info(f"Is news site? {result.get('is_news_site', False)}")
                
                # Print some basic information about the extracted content
                if 'title' in result:
                    logger.info(f"Title: {result['title']}")
                if 'paragraphs' in result:
                    logger.info(f"Extracted {len(result['paragraphs'])} paragraphs")
                if 'headings' in result:
                    logger.info(f"Extracted {len(result['headings'])} headings")
            else:
                logger.error(f"Failed to extract content from {url}")
        except Exception as e:
            logger.error(f"Error while testing {url}: {str(e)}")
            import traceback
            traceback.print_exc()

def main():
    """Main function to run the test."""
    # Run the async test
    asyncio.run(run_test())

if __name__ == "__main__":
    main()
