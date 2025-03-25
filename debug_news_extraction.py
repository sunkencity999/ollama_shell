#!/usr/bin/env python3
"""
Debug script for news content extraction in the WebBrowser class.
This script focuses on testing the extract_structured_content method with detailed debugging.
"""

import asyncio
import sys
import logging
from web_browsing import WebBrowser

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def debug_news_extraction():
    """Debug the news content extraction functionality"""
    print("Initializing WebBrowser...")
    browser = WebBrowser(None)  # Pass None as we don't need the Ollama client for this test
    
    # Test URL (CNN)
    cnn_url = "https://www.cnn.com"
    print(f"\nDebugging news content extraction from {cnn_url}...")
    
    # First, let's manually fetch the HTML content using requests
    import requests
    from bs4 import BeautifulSoup
    
    print(f"\nManually fetching HTML content from {cnn_url} using requests...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(cnn_url, headers=headers, timeout=10)
    response.raise_for_status()
    html_content = response.text
    print(f"Successfully fetched HTML content: {len(html_content)} bytes")
    
    # Parse the HTML content with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    print(f"Created BeautifulSoup object")
    
    # Extract domain
    domain = browser._extract_domain(cnn_url)
    print(f"Extracted domain: {domain}")
    
    # Check if it's recognized as a news site
    news_domains = ['cnn.com', 'bbc.com', 'nytimes.com', 'foxnews.com', 'reuters.com', 
                   'washingtonpost.com', 'theguardian.com', 'news.', 'nbcnews.com', 
                   'cbsnews.com', 'abcnews.go.com', 'usatoday.com', 'wsj.com', 'apnews.com']
    is_news_site = any(news_domain in domain.lower() for news_domain in news_domains)
    print(f"Is recognized as a news site: {is_news_site}")
    
    # Directly test the _extract_news_content method
    print(f"\nDirectly testing _extract_news_content method...")
    try:
        news_content = browser._extract_news_content(soup, cnn_url)
        print(f"News content extracted successfully with {len(news_content.keys())} fields")
        
        # Create a structured content result with the news content
        result = {
            'success': True,
            'title': soup.title.string if soup.title else '',
            'headings': browser._extract_headings(soup),
            'paragraphs': browser._extract_paragraphs(soup),
            'links': browser._extract_links_from_html(soup),
            'images': browser._extract_images(soup),
            'tables': browser._extract_tables(soup),
            'metadata': browser._extract_metadata(soup),
            'raw_text': soup.get_text(separator='\n', strip=True),
            'news_content': news_content,
            'url': cnn_url
        }
    except Exception as e:
        print(f"Error extracting news content: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Try the extract_structured_content method
        print("\nFalling back to extract_structured_content method...")
        result = await browser.extract_structured_content(cnn_url)
        
        print("\n=== STRUCTURED CONTENT RESULT ===")
        print(f"Result type: {type(result)}")
        print(f"Result keys: {result.keys()}")
        
        # Check if news_content is in the result
        if 'news_content' in result:
            print("\nNews content was successfully extracted!")
            print(f"News content keys: {result['news_content'].keys()}")
            
            # Print some sample news content
            print("\nSample news content:")
            for key, value in result['news_content'].items():
                if isinstance(value, list):
                    print(f"\n{key} ({len(value)} items):")
                    for item in value[:3]:  # Show first 3 items
                        print(f"  - {item}")
                    if len(value) > 3:
                        print(f"  ... and {len(value) - 3} more items")
                else:
                    print(f"\n{key}: {value}")
        else:
            print("\nNo news_content found in result")
            
            # Print the result structure to help debug
            print("\nResult structure:")
            for key, value in result.items():
                if isinstance(value, dict):
                    print(f"{key}: {type(value)} with keys {value.keys()}")
                elif isinstance(value, list):
                    print(f"{key}: List with {len(value)} items")
                else:
                    print(f"{key}: {value}")
    
    except Exception as e:
        print(f"Error during extraction: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\nDone!")

if __name__ == "__main__":
    asyncio.run(debug_news_extraction())
