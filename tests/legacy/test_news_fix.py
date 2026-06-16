#!/usr/bin/env python3
"""
Simple test script to verify the fix for news content extraction.
"""

from web_browsing import WebBrowser
from agentic_ollama import AgenticOllama

def main():
    """Test the news content extraction functionality"""
    print("Initializing components...")
    ollama_client = AgenticOllama()
    browser = WebBrowser(ollama_client)
    
    # Test URL
    url = "https://www.cnn.com"
    
    print(f"\nTesting news content extraction from {url}...")
    
    # Extract domain
    domain = browser._extract_domain(url)
    print(f"Extracted domain: {domain}")
    
    # Use the fixed extract_structured_content_sync method
    print(f"Extracting structured content...")
    result = browser.extract_structured_content_sync(url)
    
    # Check if news_content is in the result
    if 'news_content' in result:
        print(f"\n✅ SUCCESS: Successfully extracted news content from {url}")
        print(f"News content fields: {list(result['news_content'].keys())}")
        headlines = result['news_content'].get('headlines', [])
        print(f"Headlines count: {len(headlines)}")
        
        # Print a few headlines as examples
        if headlines:
            print("\nSample headlines:")
            for i, headline in enumerate(headlines[:5]):
                print(f"  {i+1}. {headline}")
    else:
        print(f"\n❌ FAILED: Could not extract news content from {url}")
        print(f"Available fields in result: {list(result.keys())}")

if __name__ == "__main__":
    main()
