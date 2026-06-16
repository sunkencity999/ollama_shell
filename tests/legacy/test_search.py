from web_browsing import WebBrowser
import asyncio
import requests
from bs4 import BeautifulSoup

class MockOllamaClient:
    async def _generate_completion(self, prompt):
        return {"success": True, "result": "This is a mock response"}

async def test():
    # Create a mock Ollama client since we don't need it for search_web
    mock_client = MockOllamaClient()
    browser = WebBrowser(mock_client)
    
    # Use the _extract_search_results method directly since we can't call search_web without a real client
    print("Fetching content from Google search...")
    url = "https://www.google.com/search?q=latest+developments+in+renewable+energy+technologies"
    
    # Use more realistic browser headers to bypass anti-scraping measures
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.google.com/",
        "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }
    
    # Try to use DuckDuckGo instead as it's more scraper-friendly
    print("Also trying DuckDuckGo as a backup...")
    ddg_url = "https://html.duckduckgo.com/html/?q=latest+developments+in+renewable+energy+technologies"
    
    # First try Google
    results = []
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        results = browser._extract_search_results(soup, "google.com")
        
        print(f'Found {len(results)} results from Google')
    else:
        print(f"Failed to fetch content from Google: {response.status_code}")
    
    # If Google didn't return results, try DuckDuckGo
    if not results:
        print("Trying DuckDuckGo instead...")
        try:
            ddg_response = requests.get(ddg_url, headers=headers)
            
            if ddg_response.status_code == 200:
                ddg_soup = BeautifulSoup(ddg_response.text, 'html.parser')
                results = browser._extract_search_results(ddg_soup, "duckduckgo.com")
                print(f'Found {len(results)} results from DuckDuckGo')
            else:
                print(f"Failed to fetch content from DuckDuckGo: {ddg_response.status_code}")
        except Exception as e:
            print(f"Error fetching from DuckDuckGo: {str(e)}")
    
    # Display results
    if results:
        for i, result in enumerate(results[:5], 1):
            print(f'\nResult {i}:')
            print(f'Title: {result.get("title")}')
            print(f'URL: {result.get("url")}')
            print(f'Snippet: {result.get("snippet")[:100]}...' if result.get("snippet") else "No snippet")
    else:
        print("No search results found from either Google or DuckDuckGo.")

if __name__ == "__main__":
    asyncio.run(test())
