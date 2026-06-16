#!/usr/bin/env python3
"""
Test script for the news content extraction functionality in the WebBrowser class.
This script tests the extraction of structured content from various news websites,
with a focus on testing the enhanced paywall detection and handling.
"""

import asyncio
import logging
import traceback
import json
from web_browsing import WebBrowser
from agentic_assistant_enhanced import AgenticOllama

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_news_extraction():
    """Test the news content extraction functionality on various news sites"""
    print("Initializing WebBrowser...")
    ollama_client = AgenticOllama()
    browser = WebBrowser(ollama_client)
    
    # Test URLs for various news sites, including some with known paywalls
    news_urls = [
        # General news sites
        "https://www.cnn.com/2023/03/20/politics/trump-manhattan-da-charges/index.html",
        "https://www.bbc.com/news/world-us-canada-65387787",
        # Sites with known paywalls
        "https://www.nytimes.com/2023/04/20/us/politics/trump-indictment-charges.html",
        "https://www.wsj.com/articles/federal-reserve-meeting-interest-rates-inflation-march-2023-11679433637",
        "https://www.washingtonpost.com/technology/2023/04/18/ai-danger-risks-chatgpt-openai/",
        # Other news sites to test
        "https://www.reuters.com/world/us/trump-faces-formidable-task-winning-presidential-election-2024-2023-04-05/",
        "https://www.theguardian.com/us-news/2023/apr/04/trump-arraignment-charges-what-happens-next"
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
            result = browser.extract_structured_content_sync(url)
            
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
            result = browser.extract_structured_content_sync(url)
            
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
                    'image_url': '',
                    'timeout_error': True
                }
                manual_extraction_success = True
                results[url]['error'] = 'Timeout error'
            except Exception as e:
                print(f"❌ ERROR during manual extraction: {str(e)}")
                import traceback as tb
                tb.print_exc()
                manual_extraction_success = False
                results[url]['error'] = str(e)
            
            # Now test the extract_structured_content method
            print(f"\nTesting extract_structured_content method...")
            result = await browser.extract_structured_content(url)
            
            # Manually add the news content to the result if it's not already there
            if 'news_content' not in result and manual_extraction_success:
                print(f"\nManually adding news content to the result...")
                result['news_content'] = manual_news_content
                print(f"News content added successfully")
            
            # Check if news_content is in the result
            if 'news_content' in result:
                print(f"✅ SUCCESS: News content in final result with {len(result['news_content'].keys())} fields")
                
                # Store the result for this URL
                results[url] = {
                    "success": True,
                    "fields": list(result['news_content'].keys()),
                    "headlines_count": len(result['news_content'].get('headlines', [])),
                    "categories_count": len(result['news_content'].get('categories', [])),
                    "keywords_count": len(result['news_content'].get('keywords', []))
                }
                
                # Print a sample of the extracted content
                print("\nSample extracted content from final result:")
                print(f"  Headlines: {len(result['news_content'].get('headlines', []))} found")
                if result['news_content'].get('headlines', []):
                    for headline in result['news_content']['headlines'][:3]:
                        print(f"    - {headline}")
                
                print(f"  Author: {result['news_content'].get('author', 'Not found')}")
                print(f"  Publication date: {result['news_content'].get('publication_date', 'Not found')}")
                print(f"  Categories: {len(result['news_content'].get('categories', []))} found")
                print(f"  Keywords: {len(result['news_content'].get('keywords', []))} found")
                
            else:
                print(f"❌ FAILURE: No news_content found in final result")
                results[url] = {
                    "success": False,
                    "error": "No news_content found in result"
                }
                
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            results[url] = {
                "success": False,
                "error": str(e)
            }
    
    # Print summary of results
    print(f"\n{'='*50}")
    print("SUMMARY OF RESULTS:")
    for url, result in results.items():
        domain = result.get('domain', browser._extract_domain(url))
        if result.get("success", False):
            headlines_count = result.get('headlines_count', 0)
            categories_count = result.get('categories_count', 0)
            keywords_count = result.get('keywords_count', 0)
            
            # Check for paywall or timeout indicators
            has_paywall = 'paywall_detected' in result.get('fields', [])
            has_timeout = 'timeout_error' in result.get('fields', [])
            
            if has_paywall:
                print(f"⚠️ {domain}: Content behind paywall, extracted {headlines_count} headlines")
            elif has_timeout:
                print(f"⚠️ {domain}: Timeout error, but extracted available content")
            else:
                print(f"✅ {domain}: Successfully extracted {headlines_count} headlines, {categories_count} categories, {keywords_count} keywords")
        else:
            error = result.get('error', 'Unknown error')
            if error and 'timeout' in error.lower():
                print(f"⚠️ {domain}: Timeout error when accessing content")
            elif error and any(term in error.lower() for term in ['401', '403', 'unauthorized', 'forbidden', 'paywall']):
                print(f"⚠️ {domain}: Content behind paywall or requires authentication")
            else:
                print(f"❌ {domain}: {error}")
    
    print("\nDone!")

if __name__ == "__main__":
    asyncio.run(test_news_extraction())
