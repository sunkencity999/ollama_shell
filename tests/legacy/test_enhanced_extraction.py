#!/usr/bin/env python3
"""
Test script for the enhanced news content extraction functionality in the WebBrowser class.
This script tests the extraction of structured content from various news websites,
with a focus on testing the enhanced paywall detection and handling.
"""

import asyncio
import logging
import traceback
import json
from web_browsing import WebBrowser
from agentic_ollama import AgenticOllama

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_news_extraction():
    """Test the enhanced news content extraction functionality on various news sites"""
    print("Initializing WebBrowser...")
    ollama_client = AgenticOllama()
    browser = WebBrowser(ollama_client)
    
    # Test URLs for various news sites, including some with known paywalls
    news_urls = [
        # General news sites
        "https://www.cnn.com/2024/03/24/politics/biden-netanyahu-call-gaza-aid/index.html",
        "https://www.bbc.com/news/world-us-canada-68661019",
        # Sites with known paywalls
        "https://www.nytimes.com/2024/03/24/us/politics/biden-israel-gaza-aid.html",
        "https://www.wsj.com/world/middle-east/biden-netanyahu-speak-amid-pressure-over-gaza-aid-humanitarian-crisis-9a248a4a",
        "https://www.washingtonpost.com/politics/2024/03/24/biden-netanyahu-gaza-aid/",
        # Other news sites to test
        "https://www.reuters.com/world/middle-east/biden-netanyahu-speak-us-pushes-more-gaza-aid-2024-03-24/",
        "https://www.theguardian.com/world/2024/mar/24/biden-netanyahu-gaza-aid-call"
    ]
    
    results = {}
    
    for url in news_urls:
        print(f"\n{'='*50}")
        print(f"Testing news content extraction from {url}...")
        
        try:
            # Extract domain
            domain = browser._extract_domain(url)
            print(f"Extracted domain: {domain}")
            
            # Store the domain for result tracking
            results[url] = {
                "domain": domain,
                "success": False,
                "error": None
            }
            
            # Use the enhanced extract_structured_content_sync method
            print(f"Extracting structured content from {url}...")
            print(f"\nDEBUG: Testing site-specific extraction for {domain}")
            
            # Enable more detailed logging
            logging.getLogger('web_browsing').setLevel(logging.DEBUG)
            
            # Check if we have a site-specific extraction method
            site_specific_method = getattr(browser, f"_extract_{domain.split('.')[0]}_content", None)
            if site_specific_method:
                print(f"Found site-specific extraction method for {domain}")
            else:
                print(f"No site-specific extraction method found for {domain}")
                
            result = browser.extract_structured_content_sync(url)
            
            # Reset logging level
            logging.getLogger('web_browsing').setLevel(logging.INFO)
            
            # Check if news_content is in the result
            if 'news_content' in result:
                print(f"✅ Successfully extracted news content from {url}")
                print(f"News content fields: {list(result['news_content'].keys())}")
                
                # Check for paywall detection
                paywall_detected = result['news_content'].get('paywall_detected', False)
                paywall_bypassed = result['news_content'].get('paywall_bypassed', False)
                
                if paywall_detected:
                    if paywall_bypassed:
                        print(f"🔓 Paywall detected but successfully bypassed for {url}")
                    else:
                        print(f"🔒 Paywall detected for {url}, limited content extracted")
                
                # Store results
                results[url]['success'] = True
                results[url]['fields'] = list(result['news_content'].keys())
                results[url]['headlines_count'] = len(result['news_content'].get('headlines', []))
                results[url]['paywall_detected'] = paywall_detected
                results[url]['paywall_bypassed'] = paywall_bypassed
                
                # Check content quality
                main_content = result['news_content'].get('main_content', '')
                results[url]['content_length'] = len(main_content) if main_content else 0
                results[url]['content_quality'] = 'Good' if len(main_content) > 1000 else 'Limited'
                
                # Print sample of content for debugging
                print(f"\nSample content from {domain}:")
                if main_content:
                    print(f"Main content sample (first 200 chars): {main_content[:200]}...")
                else:
                    print("No main content extracted")
                    
                # Check for specific extraction issues
                if not main_content and not result['news_content'].get('paywall_detected', False):
                    print(f"WARNING: No content extracted but no paywall detected for {domain}")
                    
                # Check HTML structure if available
                html_content = result.get('html_content', '')
                if html_content:
                    print(f"HTML content available: {len(html_content)} bytes")
                    # Check for common paywall indicators in HTML
                    paywall_indicators = ['subscribe', 'subscription', 'paywall', 'premium', 'sign in to read']
                    found_indicators = [ind for ind in paywall_indicators if ind.lower() in html_content.lower()]
                    if found_indicators:
                        print(f"Possible paywall indicators found in HTML: {found_indicators}")
            else:
                print(f"❌ Failed to extract news content from {url}")
                results[url]['success'] = False
                results[url]['error'] = "No news_content in result"
                
        except Exception as e:
            print(f"❌ Error extracting content from {url}: {str(e)}")
            traceback.print_exc()
            results[url]['success'] = False
            results[url]['error'] = str(e)
    
    # Print summary of results
    print("\n" + "="*50)
    print("SUMMARY OF NEWS EXTRACTION TESTS")
    print("="*50)
    
    # Check if we need to improve site-specific extraction
    sites_needing_improvement = []
    for url, data in results.items():
        if data['success'] and data.get('content_length', 0) < 500 and not data.get('paywall_detected', False):
            sites_needing_improvement.append(data['domain'])
    
    if sites_needing_improvement:
        print(f"\nSites needing improved extraction methods: {', '.join(sites_needing_improvement)}")
    
    success_count = sum(1 for url, data in results.items() if data['success'])
    print(f"Successfully extracted news content from {success_count}/{len(news_urls)} sites")
    
    paywall_count = sum(1 for url, data in results.items() if data.get('paywall_detected', False))
    bypass_count = sum(1 for url, data in results.items() if data.get('paywall_bypassed', False))
    print(f"Detected paywalls on {paywall_count} sites, successfully bypassed {bypass_count}")
    
    for url, data in results.items():
        status = "✅ SUCCESS" if data['success'] else "❌ FAILED"
        if data.get('paywall_detected', False):
            if data.get('paywall_bypassed', False):
                status += " 🔓 PAYWALL BYPASSED"
            else:
                status += " 🔒 PAYWALL DETECTED"
                
        print(f"{status}: {url} ({data['domain']})")
        if data['success']:
            print(f"  - Fields: {data.get('fields', [])}")
            print(f"  - Headlines: {data.get('headlines_count', 0)}")
            print(f"  - Content length: {data.get('content_length', 0)} chars")
            print(f"  - Content quality: {data.get('content_quality', 'Unknown')}")
        else:
            print(f"  - Error: {data.get('error', 'Unknown error')}")
    
    # Save results to a JSON file for later analysis
    with open('news_extraction_test_results.json', 'w') as f:
        # Convert results to a serializable format
        serializable_results = {}
        for url, data in results.items():
            serializable_results[url] = {k: v for k, v in data.items() if k != 'error' or v is None or isinstance(v, (str, int, float, bool, list, dict))}
        json.dump(serializable_results, f, indent=2)
    
    print(f"\nTest results saved to news_extraction_test_results.json")
    return results


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_news_extraction())
