#!/usr/bin/env python3
"""
Test script for the enhanced search functionality with DuckDuckGo fallback.
This script tests the WebBrowser class's ability to search for information,
extract search results, and follow links to analyze content.
"""

import asyncio
import sys
import os
import re
from web_browsing import WebBrowser
from bs4 import BeautifulSoup
import requests
import json

async def test_search_with_fallback():
    """Test the search functionality with DuckDuckGo fallback."""
    print("Testing enhanced search functionality with DuckDuckGo fallback...")
    
    # Initialize the WebBrowser
    browser = WebBrowser(None)  # Pass None as we don't need the Ollama client for this test
    
    # Test search query
    search_query = "latest developments in renewable energy technologies"
    print(f"Search query: '{search_query}'")
    
    # Simulate a search task
    task_description = f"Search for information about {search_query} and create a detailed report"
    
    # Extract URLs from the task
    urls = browser._extract_urls(task_description)
    if not urls:
        # Add a default search URL if none found
        urls = ["https://www.google.com"]
    
    # Extract domain from the URL
    domain = browser._extract_domain(urls[0])
    
    # Format the search query for the URL
    formatted_query = search_query.replace(" ", "+")
    
    # Construct the search URL based on the domain
    search_url = f"https://www.google.com/search?q={formatted_query}"
    
    print(f"Fetching content from Google search...")
    print(f"Also trying DuckDuckGo as a backup...")
    
    # Set up headers for requests
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # First try Google
    try:
        response = requests.get(search_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            search_results = browser._extract_search_results(soup, "google.com")
            
            print(f'Found {len(search_results)} results from Google')
            
            # If Google didn't return results, try DuckDuckGo
            if not search_results:
                print("No results from Google. Trying DuckDuckGo...")
                
                # Create DuckDuckGo search URL
                ddg_url = f"https://html.duckduckgo.com/html/?q={formatted_query}"
                
                # Set up headers for DuckDuckGo request
                ddg_headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9'
                }
                
                # Make the request
                ddg_response = requests.get(ddg_url, headers=ddg_headers, timeout=15)
                ddg_response.raise_for_status()
                
                # Parse the HTML content
                ddg_soup = BeautifulSoup(ddg_response.content, 'html.parser')
                
                # Extract search results
                search_results = browser._extract_search_results(ddg_soup, "duckduckgo.com")
                print(f"Found {len(search_results)} results from DuckDuckGo")
        else:
            print(f"Failed to fetch content from Google: {response.status_code}")
            search_results = []
    except Exception as e:
        print(f"Error fetching from Google: {str(e)}")
        search_results = []
    
    # Fix DuckDuckGo URLs if needed
    if search_results:
        for result in search_results:
            if 'url' in result and 'duckduckgo.com/l/' in result['url']:
                try:
                    from urllib.parse import unquote
                    # Extract the actual URL from DuckDuckGo's redirect
                    actual_url = re.search(r'uddg=([^&]+)', result['url'])
                    if actual_url:
                        fixed_url = unquote(actual_url.group(1))
                        print(f"Fixed DuckDuckGo URL: {fixed_url}")
                        result['url'] = fixed_url
                except Exception as e:
                    print(f"Error decoding DuckDuckGo URL: {str(e)}")
    
    # Display results
    if search_results:
        print("\nSearch Results:")
        for i, result in enumerate(search_results[:5], 1):
            print(f'\nResult {i}:')
            print(f'Title: {result.get("title")}')
            print(f'URL: {result.get("url")}')
            print(f'Snippet: {result.get("snippet")[:100]}...' if result.get("snippet") else "No snippet")
        
        # Test following links and analyzing content
        print("\nTesting link following and content analysis...")
        try:
            detailed_analysis = browser._follow_and_analyze_links(search_results, search_query)
            
            # Save the analysis to a file for inspection
            output_file = "search_analysis_results.txt"
            with open(output_file, "w") as f:
                f.write(detailed_analysis)
            
            print(f"\nAnalysis complete! Results saved to {output_file}")
            print(f"Analysis length: {len(detailed_analysis)} characters")
            
            # Print a preview of the analysis
            preview_length = 500
            print(f"\nAnalysis Preview (first {preview_length} characters):")
            print("-" * 80)
            print(detailed_analysis[:preview_length] + "...")
            print("-" * 80)
        except Exception as e:
            print(f"Error during link analysis: {str(e)}")
    else:
        print("No search results found from either Google or DuckDuckGo.")

if __name__ == "__main__":
    asyncio.run(test_search_with_fallback())
