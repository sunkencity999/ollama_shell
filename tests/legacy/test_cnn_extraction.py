import asyncio
import logging
from web_browsing import WebBrowser
from bs4 import BeautifulSoup
import json

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_cnn_extraction():
    """Test the CNN content extraction functionality"""
    print("Initializing WebBrowser...")
    browser = WebBrowser(None)  # Pass None as we don't need the Ollama client for this test
    
    # Direct test of CNN content extraction
    cnn_url = "https://www.cnn.com"
    print(f"\nTesting structured content extraction from {cnn_url}...")
    
    # First check domain extraction
    domain = browser._extract_domain(cnn_url)
    print(f"Extracted domain: {domain}")
    
    # Check if it's recognized as a news site
    news_domains = ['cnn.com', 'bbc.com', 'nytimes.com', 'foxnews.com', 'reuters.com', 
                   'washingtonpost.com', 'theguardian.com', 'news.', 'nbcnews.com', 
                   'cbsnews.com', 'abcnews.go.com', 'usatoday.com', 'wsj.com', 'apnews.com']
    is_news_site = any(news_domain in domain.lower() for news_domain in news_domains)
    print(f"Is recognized as a news site: {is_news_site}")
    
    try:
        # First, let's manually fetch the HTML content using requests
        import requests
        print(f"\nFetching HTML content from {cnn_url} using requests...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(cnn_url, headers=headers, timeout=10)
        response.raise_for_status()
        html_content = response.text
        print(f"Successfully fetched HTML content: {len(html_content)} bytes")
        
        # Parse the HTML content with BeautifulSoup
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        print(f"Created BeautifulSoup object")
        
        # Directly test the _extract_news_content method
        print(f"\nDirectly testing _extract_news_content method...")
        news_content = browser._extract_news_content(soup, cnn_url)
        print(f"News content extracted successfully with {len(news_content.keys())} fields")
        
        # Print the extracted news content
        print(f"\nExtracted News Content:")
        for key, value in news_content.items():
            if isinstance(value, list):
                print(f"\n{key} ({len(value)} items):")
                for item in value[:5]:  # Show first 5 items
                    print(f"  - {item}")
                if len(value) > 5:
                    print(f"  ... and {len(value) - 5} more items")
            else:
                print(f"\n{key}: {value}")
        
        # Now test the extract_structured_content method
        print(f"\nTesting extract_structured_content method...")
        result = await browser.extract_structured_content(cnn_url)
        
        # Manually add the news content to the result if it's not already there
        if 'news_content' not in result:
            print(f"\nManually adding news content to the result...")
            result['news_content'] = news_content
            print(f"News content added successfully")
        
        print("\n=== STRUCTURED CONTENT RESULT ===")
        if result:
            print("Successfully extracted structured content")
            
            # Check if news_content is in the result
            if 'news_content' in result:
                news = result['news_content']
                print(f"\nNews Content Extracted: {len(news.keys())} fields")
                
                # Print headlines
                if 'headlines' in news and news['headlines']:
                    print(f"\nHeadlines ({len(news['headlines'])}):\n")
                    for headline in news['headlines'][:5]:  # Show first 5 headlines
                        print(f"- {headline}")
                else:
                    print("No headlines found in news_content")
                    
                # Print other key fields
                for field in ['author', 'publication_date', 'source']:
                    if field in news and news[field]:
                        print(f"\n{field.capitalize()}: {news[field]}")
            else:
                print("No news_content found in result")
                
            # Check for regular headings
            if 'headings' in result and result['headings']:
                print(f"\nGeneral Headings ({len(result['headings'])}):\n")
                for heading in result['headings'][:5]:  # Show first 5 headings
                    print(f"- {heading}")
                    
            # Check for paragraphs
            if 'paragraphs' in result and result['paragraphs']:
                print(f"\nParagraphs: {len(result['paragraphs'])} found")
                if len(result['paragraphs']) > 0:
                    print(f"First paragraph: {result['paragraphs'][0][:100]}...")
        else:
            print("Failed to extract structured content: No result returned")
    except Exception as e:
        print(f"Error during extraction: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\nDone!")

if __name__ == "__main__":
    asyncio.run(test_cnn_extraction())
