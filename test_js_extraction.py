"""
Test script for the enhanced JavaScript content extraction functionality.
This script tests the js_content_extraction module with various news sites.
"""

import os
import sys
import logging
import argparse
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_js_extraction')

# Import our modules
try:
    from mcp_browser import MCPBrowser, start_mcp_server
    import js_content_extraction
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)

def test_extraction(url, server_url):
    """
    Test the enhanced JavaScript extraction on a specific URL.
    
    Args:
        url: The URL to test
        server_url: The Selenium server URL
    """
    logger.info(f"Testing enhanced JavaScript extraction on: {url}")
    
    # Extract domain from URL
    import re
    domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
    domain = domain_match.group(1) if domain_match else ""
    
    logger.info(f"Extracted domain: {domain}")
    
    # Run the extraction
    result = js_content_extraction.extract_with_enhanced_javascript(url, domain, server_url)
    
    # Check if extraction was successful
    if result.get('success', False):
        logger.info(f"Extraction successful for {url}")
        logger.info(f"Title: {result.get('title', 'No title')}")
        
        # Parse the content with BeautifulSoup
        soup = BeautifulSoup(result.get('content', ''), 'html.parser')
        
        # Extract and log some basic information
        title = soup.title.text if soup.title else "No title found"
        paragraphs = soup.find_all('p')
        headings = soup.find_all(['h1', 'h2', 'h3'])
        
        logger.info(f"Title from HTML: {title}")
        logger.info(f"Found {len(paragraphs)} paragraphs")
        logger.info(f"Found {len(headings)} headings")
        
        # Log the first few paragraphs
        logger.info("First 3 paragraphs:")
        for i, p in enumerate(paragraphs[:3]):
            text = p.get_text().strip()
            if text:
                logger.info(f"  {i+1}. {text[:100]}...")
        
        # Save the HTML content to a file for inspection
        output_file = f"extracted_{domain.replace('.', '_')}.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.get('content', ''))
        logger.info(f"Saved HTML content to {output_file}")
        
        return True
    else:
        logger.error(f"Extraction failed for {url}: {result.get('error', 'Unknown error')}")
        return False

def main():
    """Main function to run the test script."""
    parser = argparse.ArgumentParser(description='Test enhanced JavaScript content extraction')
    parser.add_argument('--url', type=str, help='URL to test')
    parser.add_argument('--site', type=str, choices=['cnn', 'wsj', 'wapo', 'reuters', 'guardian', 'bbc', 'nyt'],
                        help='Predefined news site to test')
    args = parser.parse_args()
    
    # Default test URLs for different news sites
    test_urls = {
        'cnn': 'https://www.cnn.com/world',
        'wsj': 'https://www.wsj.com/news/world',
        'wapo': 'https://www.washingtonpost.com/world/',
        'reuters': 'https://www.reuters.com/world/',
        'guardian': 'https://www.theguardian.com/international',
        'bbc': 'https://www.bbc.com/news/world',
        'nyt': 'https://www.nytimes.com/section/world'
    }
    
    # Start the MCP server if not already running
    server_url = os.environ.get('MCP_SERVER_URL')
    if not server_url:
        logger.info("Starting MCP server...")
        # Create a browser instance to get the server URL
        browser = MCPBrowser()
        server_url = browser.server_url
        logger.info(f"Using MCP server at {server_url}")
    
    # Determine which URL(s) to test
    if args.url:
        # If specific URL is provided, test only that URL
        logger.info(f"Testing user-provided URL: {args.url}")
        test_extraction(args.url, server_url)
    elif args.site:
        # If specific site is selected, test that site
        if args.site in test_urls:
            url = test_urls[args.site]
            logger.info(f"Testing {args.site}: {url}")
            test_extraction(url, server_url)
        else:
            logger.error(f"Unknown site: {args.site}")
    else:
        # Test BBC by default (more reliable than testing all sites)
        site = 'bbc'
        url = test_urls[site]
        logger.info(f"Testing default site {site}: {url}")
        test_extraction(url, server_url)

if __name__ == "__main__":
    main()
