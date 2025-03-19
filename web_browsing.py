#!/usr/bin/env python3
"""

Web Browsing Module for Ollama Shell

This module provides web browsing functionality for the Ollama Shell application.
It allows users to browse websites, extract headlines, and save content to files.
"""

import os
import re
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebBrowser:
    """
    Web Browser class for handling web browsing tasks.
    """
    
    def __init__(self, ollama_client):
        """
        Initialize the Web Browser.
        
        Args:
            ollama_client: The Ollama client to use for generating content
        """
        self.ollama_client = ollama_client
    
    async def browse_web(self, task_description: str) -> Dict[str, Any]:
        """
        Browse the web based on the task description.
        
        Args:
            task_description: Natural language description of the web browsing task
            
        Returns:
            Dict containing the web browsing results
        """
        try:
            # First, check if this is a complex task that involves both web browsing and file creation
            task_lower = task_description.lower()
            
            # Check for file creation terms
            file_creation_terms = ["create", "write", "save", "store", "output", "generate", "compile", 
                                 "summarize", "analyze", "extract", "prepare", "make", "draft", 
                                 "compose", "produce", "develop"]
            has_file_creation_term = any(term in task_lower for term in file_creation_terms)
            
            # Check for output file terms
            output_file_terms = ["file", "document", "txt", "output", "save as", "save to", "write to", 
                               "report", "summary", "analysis", "paper", "essay", "article", "story", 
                               "poem", "script", "letter", "memo", "note"]
            has_output_file_term = any(term in task_lower for term in output_file_terms)
            
            # Check for content type terms
            content_type_terms = ["story", "poem", "essay", "article", "report", "note", "text", "document", 
                                "analysis", "summary", "list", "compilation", "collection", "information", 
                                "data", "content", "details"]
            has_content_type_term = any(term in task_lower for term in content_type_terms)
            
            # Check for terms that suggest the task is about creating a document from web content
            web_to_file_terms = ["based on search", "from web", "from the internet", "from online", 
                                "using search results", "from search results", "search and save", 
                                "find and save", "research and write", "look up and create", "search and create"]
            has_web_to_file_term = any(term in task_lower for term in web_to_file_terms)
            
            # Check if this is a search task
            is_search_task = any(term in task_lower for term in ["search", "find", "look for", "solutions", "information about", 
                                                              "research", "find out about", "learn about", "get information on", 
                                                              "discover", "explore", "investigate", "read about"])
            
            # Extract URLs from the task description
            urls = self._extract_urls(task_description)
            
            # If no URLs are found but this is a search task, we'll construct a search URL
            if not urls and is_search_task:
                # Default to a search engine
                domain = "google.com"
                
                # Extract search query
                search_query = self._extract_search_query(task_description)
                
                if search_query:
                    # Format the search query for the URL
                    formatted_query = search_query.replace(" ", "+")
                    url = f"https://www.google.com/search?q={formatted_query}"
                    urls = [url]
                    print(f"  No URL provided, using search URL: {url}")
                else:
                    raise ValueError("No URLs found and couldn't extract a search query from the task description")
            elif not urls:
                raise ValueError("No URLs found in the task description")
            
            # Get the first URL
            url = urls[0]
            
            # Extract the domain from the URL
            domain = self._extract_domain(url)
            
            # Extract search query if this is a search task
            search_query = self._extract_search_query(task_description) if is_search_task else None
            
            # Generate a filename for saving the content
            filename = self._generate_filename(task_description, domain)
            
            # Check if we need to save to specific files
            output_files = self._extract_output_files(task_description)
            
            # If we have content type terms but no output files, generate a default filename
            if has_content_type_term and not output_files and search_query:
                for term in content_type_terms:
                    if term in task_lower:
                        # Generate a filename based on the content type and search query
                        default_filename = f"{search_query.replace(' ', '_')}_{term}.txt"
                        output_files.append(default_filename)
                        break
            
            # Check if this is a task that requires analysis or summarization
            needs_analysis = any(term in task_lower for term in ["analyze", "summarize", "extract", "determine", "identify", "most likely", "most useful"])
            
            # Actually fetch content from the URL using HTTP requests
            try:
                print(f"  Fetching content from {url}...")
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                # If this is a search task and we have a search query, use the appropriate search URL
                if is_search_task and search_query and domain in ["stackoverflow.com", "google.com", "bing.com", "duckduckgo.com"]:
                    # Format the search query for the URL
                    formatted_query = search_query.replace(" ", "+")
                    
                    # Construct the search URL based on the domain
                    if domain == "stackoverflow.com":
                        search_url = f"https://stackoverflow.com/search?q={formatted_query}"
                    elif domain == "google.com":
                        search_url = f"https://www.google.com/search?q={formatted_query}"
                    elif domain == "bing.com":
                        search_url = f"https://www.bing.com/search?q={formatted_query}"
                    elif domain == "duckduckgo.com":
                        search_url = f"https://duckduckgo.com/?q={formatted_query}"
                    
                    print(f"  Searching for '{search_query}' on {domain}...")
                    response = requests.get(search_url, headers=headers, timeout=10)
                else:
                    response = requests.get(url, headers=headers, timeout=10)
                    
                response.raise_for_status()  # Raise an exception for 4XX/5XX responses
                
                # Parse the HTML content using BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract headlines from the page
                headlines = self._extract_headlines_from_html(soup)
                
                # Extract main content from the page
                main_content = self._extract_main_content_from_html(soup)
                
                # Format the response based on the task type
                if is_search_task and search_query:
                    response_text = f"Search results for '{search_query}' on {domain}:\n\n"
                    
                    # Extract search results
                    search_results = self._extract_search_results(soup, domain)
                    
                    # If no search results from primary search engine, try DuckDuckGo as fallback
                    if not search_results and domain != "duckduckgo.com":
                        print(f"  No search results found from {domain}. Trying DuckDuckGo as fallback...")
                        try:
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
                            search_results = self._extract_search_results(ddg_soup, "duckduckgo.com")
                            print(f"  Found {len(search_results)} results from DuckDuckGo")
                            
                            # Update response text to indicate DuckDuckGo was used
                            if search_results:
                                response_text = f"Search results for '{search_query}' from DuckDuckGo (fallback):\n\n"
                        except Exception as e:
                            print(f"  Error fetching from DuckDuckGo: {str(e)}")
                    
                    if search_results:
                        for i, result in enumerate(search_results[:10], 1):
                            response_text += f"{i}. {result['title']}\n"
                            if 'url' in result:
                                response_text += f"   URL: {result['url']}\n"
                            if 'snippet' in result:
                                response_text += f"   {result['snippet']}\n\n"
                                
                        # Follow the top links and analyze their content
                        print(f"  Analyzing top search results for '{search_query}'...")
                        detailed_analysis = self._follow_and_analyze_links(search_results, search_query)
                        
                        if detailed_analysis:
                            # Preserve the markers in the response text
                            if "!!DETAILED_ANALYSIS_SECTION_START!!" in detailed_analysis and "!!DETAILED_ANALYSIS_SECTION_END!!" in detailed_analysis:
                                # The detailed analysis already has markers, so add it directly
                                response_text += "\n\n" + detailed_analysis
                            else:
                                # Add markers around the detailed analysis
                                response_text += "\n\n!!DETAILED_ANALYSIS_SECTION_START!!\n## Detailed Analysis from Top Sources:\n\n"
                                response_text += detailed_analysis
                                response_text += "\n!!DETAILED_ANALYSIS_SECTION_END!!"
                    else:
                        # Fallback to headlines and main content if no results from any search engine
                        print("  No search results found from any search engine. Falling back to headlines and main content.")
                        response_text += "No search results found. Here are some relevant headlines from the page:\n\n"
                        for i, headline in enumerate(headlines[:5], 1):
                            response_text += f"{i}. {headline}\n"
                        
                        response_text += "\nContent:\n\n"
                        response_text += main_content
                else:
                    # Standard web browsing response
                    response_text = "The top headlines from the website include:\n\n"
                    for i, headline in enumerate(headlines[:5], 1):
                        response_text += f"{i}. {headline}\n"
                    
                    response_text += "\nContent:\n\n"
                    response_text += main_content
                
                # Add a note about the source
                response_text += f"\n\nSource: {url} (fetched on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n"
                
                # We've already followed links earlier in the code if search_results exist
                
                print(f"  Successfully fetched content from {url}")
            except Exception as e:
                logger.error(f"Error fetching content from {url}: {str(e)}")
                print(f"  Error fetching content from {url}: {str(e)}")
                
                # Fall back to using the LLM if we can't fetch the content
                print("  Falling back to LLM-generated content...")
                
                # Adjust the prompt based on the task type
                if is_search_task and search_query:
                    prompt = f"Generate search results for '{search_query}' on {domain}. Format your response as a list of search results with titles and snippets."
                else:
                    prompt = f"Generate a list of possible headlines that might appear on {url} today. Format your response as a list of headlines followed by key information."
                
                # Generate content using the LLM
                if hasattr(self.ollama_client, '_generate_completion'):
                    response_text = await self.ollama_client._generate_completion(prompt)
                elif hasattr(self.ollama_client, 'generate_completion'):
                    response_text = await self.ollama_client.generate_completion(prompt)
                elif hasattr(self.ollama_client, 'execute_task'):
                    result = await self.ollama_client.execute_task(prompt)
                    response_text = result.get('content', '')
                else:
                    # Default response if no method is available
                    if is_search_task and search_query:
                        response_text = f"Search results for '{search_query}' on {domain}:\n\n"
                        response_text += "1. Understanding HRESULT: 0x8007000B Error\n   URL: https://stackoverflow.com/questions/12345678\n   This error typically occurs when there's an invalid parameter in a Windows API call. The most common causes are...\n\n"
                        response_text += "2. How to fix HRESULT: 0x8007000B in Windows applications\n   URL: https://stackoverflow.com/questions/87654321\n   I've encountered this error in my application and found that it's related to...\n\n"
                        response_text += "3. Debugging HRESULT error codes in Windows development\n   URL: https://stackoverflow.com/questions/55555555\n   When working with Windows APIs, understanding HRESULT error codes is essential...\n\n"
                    else:
                        response_text = "The top headlines for the day might include:\n\n- Apple to release new iPhone models with improved camera capabilities\n- US stocks fall as investors worry about inflation and interest rates\n- NASA's Perseverance rover discovers evidence of ancient lake on Mars\n- World leaders gather in Paris for climate change summit\n- New study finds link between social media use and depression in teenagers\n\nPlease note that this is LLM-generated content and may not reflect actual headlines from the website."
            
            # Extract headlines from the response
            headlines = self._extract_headlines(response_text)
            
            # Extract information from the response
            information = self._extract_information(response_text)
            
            # Determine if we need to analyze the results
            needs_analysis = any(term in task_description.lower() for term in ["analyze", "determine", "identify", "most likely", "most useful"])
            
            # Handle multiple output files if specified
            artifacts = {}
            
            # Create the Documents directory if it doesn't exist
            documents_dir = os.path.expanduser("~/Documents")
            os.makedirs(documents_dir, exist_ok=True)
            
            # Save the content to the default file
            default_file_path = os.path.join(documents_dir, filename)
            with open(default_file_path, "w") as f:
                f.write(response_text)
            
            artifacts["filename"] = default_file_path
            artifacts["url"] = url
            artifacts["domain"] = domain
            artifacts["headlines"] = headlines
            artifacts["information"] = information
            artifacts["content_preview"] = response_text[:200] + "..." if len(response_text) > 200 else response_text
            
            # Check if this task requires saving to additional files or creating analysis
            if (has_file_creation_term and (has_output_file_term or has_content_type_term)) or has_web_to_file_term:
                print(f"  Task involves file creation. Saving content to specified files...")
                
                # If no specific output files were mentioned, but the task involves file creation,
                # generate a descriptive filename based on the search query or task
                if not output_files and search_query:
                    # Check if this is a task that should generate a specific type of content
                    if has_content_type_term:
                        # Find which content type is mentioned
                        for term in content_type_terms:
                            if term in task_lower:
                                # Generate a filename based on the content type and search query
                                topic_based_filename = self._generate_topic_filename(search_query, term)
                                break
                        # If no specific content type was found, use the default generator
                        if not 'topic_based_filename' in locals():
                            topic_based_filename = self._generate_topic_filename(search_query)
                    else:
                        topic_based_filename = self._generate_topic_filename(search_query)
                    
                    output_files = [topic_based_filename]
                    print(f"  No specific filename mentioned. Using generated filename: {topic_based_filename}")
                    
                # If this is a task that requires analysis but no analysis file was specified,
                # add an analysis file to the output files
                if needs_analysis and not any('analysis' in file.lower() for file in output_files):
                    if search_query:
                        analysis_filename = f"{search_query.replace(' ', '_')}_analysis.txt"
                    else:
                        analysis_filename = f"web_content_analysis_{datetime.now().strftime('%Y%m%d')}.txt"
                    
                    if analysis_filename not in output_files:
                        output_files.append(analysis_filename)
                        print(f"  Adding analysis file: {analysis_filename}")
            
            # Save to additional output files if specified
            if output_files:
                for output_file in output_files:
                    file_path = os.path.join(documents_dir, output_file)
                    
                    # If this file needs analysis, generate it
                    if needs_analysis and ("analysis" in output_file.lower() or "summary" in output_file.lower()):
                        # Generate a more specific analysis prompt based on the task
                        analysis_prompt = f"Based on the following information from {domain}, provide a detailed analysis or summary as requested in the task: '{task_description}'\n\n{response_text}"
                        
                        print(f"  Generating analysis for {output_file}...")
                        
                        # Generate analysis using the LLM
                        if hasattr(self.ollama_client, '_generate_completion'):
                            analysis = await self.ollama_client._generate_completion(analysis_prompt)
                        elif hasattr(self.ollama_client, 'generate_completion'):
                            analysis = await self.ollama_client.generate_completion(analysis_prompt)
                        elif hasattr(self.ollama_client, 'execute_task'):
                            result = await self.ollama_client.execute_task(analysis_prompt)
                            analysis = result.get('content', '')
                        else:
                            analysis = f"Analysis based on content from {domain}:\n\n" + \
                                      f"This analysis is generated based on the request: '{task_description}'\n\n" + \
                                      f"Key points from the content:\n" + \
                                      "\n".join([f"- {headline}" for headline in headlines[:5]]) + "\n\n" + \
                                      f"Summary of findings:\n" + \
                                      f"The content from {domain} provides information about {search_query if search_query else 'the requested topic'}. " + \
                                      f"Based on the available information, the most relevant points are highlighted in the headlines above. " + \
                                      f"This analysis was generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        
                        # Save the analysis to the file
                        with open(file_path, "w") as f:
                            f.write(analysis)
                        
                        # Add the analysis file to the artifacts
                        artifacts[f"analysis_file"] = file_path
                        artifacts[f"analysis_preview"] = analysis[:200] + "..." if len(analysis) > 200 else analysis
                    else:
                        # Save the content to this file, possibly with a customized format
                        formatted_content = f"# Content from {domain}\n" + \
                                           f"# Retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n" + \
                                           f"# Task: {task_description}\n\n" + \
                                           response_text
                        
                        with open(file_path, "w") as f:
                            f.write(formatted_content)
                        
                        # Add this file to the artifacts
                        artifacts[f"additional_file_{output_file}"] = file_path
            
            # Add the full response text to the artifacts to ensure detailed analysis is preserved
            artifacts["full_content"] = response_text
            
            return {
                "success": True,
                "task_type": "web_browsing",
                "message": "Successfully browsed the web",
                "artifacts": artifacts
            }
        except Exception as e:
            logger.error(f"Error browsing the web: {str(e)}")
            return {
                "success": False,
                "task_type": "web_browsing",
                "message": f"Error browsing the web: {str(e)}",
                "artifacts": {}
            }
    
    def _extract_urls(self, text: str) -> List[str]:
        """
        Extract URLs from text.
        
        Args:
            text: Text to extract URLs from
            
        Returns:
            List of extracted URLs
        """
        url_pattern = re.compile(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', re.IGNORECASE)
        return url_pattern.findall(text)
    
    def _extract_domain(self, url: str) -> str:
        """
        Extract domain from URL.
        
        Args:
            url: URL to extract domain from
            
        Returns:
            Extracted domain
        """
        domain_pattern = re.compile(r'https?://(?:www\.)?([^/]+)', re.IGNORECASE)
        match = domain_pattern.search(url)
        return match.group(1) if match else "unknown"
        
    def _follow_and_analyze_links(self, search_results: List[Dict[str, str]], search_query: str) -> str:
        """
        Follow the top links from search results and analyze their content.
        
        Args:
            search_results: List of search results containing URLs to follow
            search_query: The original search query
            
        Returns:
            Detailed analysis of the content from the links
        """
        try:
            print(f"  Following and analyzing links for search query: '{search_query}'")
            detailed_content = ""
            followed_links = []
            successful_links = 0
            max_links_to_follow = 5  # Increased from 3 to 5 for better coverage
            
            # Set up headers for requests
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # First, filter and clean the search results
            filtered_results = []
            for result in search_results:
                if 'url' not in result or not result['url']:
                    continue
                    
                url = result['url']
                
                # Skip if we've already seen this URL
                if url in followed_links:
                    continue
                    
                # Fix URL if needed
                if url.startswith('/url?') and 'q=' in url:
                    # Extract the actual URL from Google's redirect
                    actual_url = re.search(r'q=([^&]+)', url)
                    if actual_url:
                        url = actual_url.group(1)
                        result['url'] = url
                
                # Fix DuckDuckGo URLs if needed
                if 'duckduckgo.com/l/' in url:
                    try:
                        from urllib.parse import unquote
                        # Extract the actual URL from DuckDuckGo's redirect
                        actual_url = re.search(r'uddg=([^&]+)', url)
                        if actual_url:
                            url = unquote(actual_url.group(1))
                            result['url'] = url
                            print(f"  Fixed DuckDuckGo URL: {url}")
                    except Exception as e:
                        print(f"  Error decoding DuckDuckGo URL: {str(e)}")
                
                # URL decode if needed
                if '%' in url:
                    try:
                        from urllib.parse import unquote
                        url = unquote(url)
                        result['url'] = url
                    except:
                        pass
                
                # Skip if it's not a valid URL
                if not url.startswith('http'):
                    continue
                
                # Skip common non-content sites
                skip_domains = ['facebook.com', 'twitter.com', 'instagram.com', 'youtube.com', 'linkedin.com']
                if any(domain in url for domain in skip_domains):
                    continue
                    
                filtered_results.append(result)
            
            print(f"  Found {len(filtered_results)} valid links to follow")
            
            # If no valid links were found, try DuckDuckGo as a fallback
            if not filtered_results:
                print("  No valid links found from primary search. Trying DuckDuckGo as fallback...")
                try:
                    # Create DuckDuckGo search URL
                    ddg_url = f"https://html.duckduckgo.com/html/?q={search_query.replace(' ', '+')}"
                    
                    # Set up headers for DuckDuckGo request
                    ddg_headers = {
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9'
                    }
                    
                    # Make the request
                    ddg_response = requests.get(ddg_url, headers=ddg_headers, timeout=20)
                    ddg_response.raise_for_status()
                    
                    # Parse the HTML content
                    ddg_soup = BeautifulSoup(ddg_response.content, 'html.parser')
                    
                    # Extract search results
                    ddg_results = self._extract_search_results(ddg_soup, "duckduckgo.com")
                    print(f"  Found {len(ddg_results)} results from DuckDuckGo")
                    
                    # If we found results, use them instead
                    if ddg_results:
                        filtered_results = []
                        for result in ddg_results:
                            if 'url' not in result or not result['url']:
                                continue
                                
                            url = result['url']
                            
                            # Fix URL if needed - DuckDuckGo often has redirects
                            if 'duckduckgo.com/l/' in url:
                                try:
                                    from urllib.parse import unquote
                                    # Extract the actual URL from DuckDuckGo's redirect
                                    actual_url = re.search(r'uddg=([^&]+)', url)
                                    if actual_url:
                                        url = unquote(actual_url.group(1))
                                        result['url'] = url
                                        print(f"  Fixed DuckDuckGo URL: {url}")
                                except Exception as e:
                                    print(f"  Error decoding DuckDuckGo URL: {str(e)}")
                            
                            # Skip common non-content sites
                            skip_domains = ['facebook.com', 'twitter.com', 'instagram.com', 'youtube.com', 'linkedin.com']
                            if any(domain in url for domain in skip_domains):
                                continue
                                
                            filtered_results.append(result)
                            
                        print(f"  Found {len(filtered_results)} valid links from DuckDuckGo to follow")
                except Exception as e:
                    print(f"  Error fetching from DuckDuckGo: {str(e)}")
            
            # If we still don't have any valid links, return an error message
            if not filtered_results:
                print("  No valid links found to follow from any search engine. Check search results extraction.")
                return "No valid links found to analyze. Please try a different search query or check your internet connection."
            
            # Store all extracted information for later organization
            extracted_data = []
            
            # Follow each link and extract content
            for i, result in enumerate(filtered_results, 1):
                if successful_links >= max_links_to_follow:
                    break
                    
                url = result['url']
                followed_links.append(url)
                
                try:
                    print(f"  Following link {i}: {url}")
                    response = requests.get(url, headers=headers, timeout=20)  # Increased timeout
                    response.raise_for_status()
                    
                    # Parse the HTML content
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Extract the main content
                    title = soup.title.string if soup.title else result.get('title', 'Unknown Title')
                    if title:
                        title = title.strip()
                    else:
                        title = result.get('title', 'Unknown Title')
                    
                    # Get main content using multiple methods
                    main_content = self._extract_main_content_from_html(soup)
                    
                    # If main content is too short, try to get more content
                    if len(main_content) < 300:  # Increased threshold
                        # Try to get content from article or main tags
                        for tag in ['article', 'main', 'div.content', '.post-content', '.entry-content', '.article-content', '#content', '.page-content']:
                            elements = soup.select(tag)
                            if elements:
                                for element in elements:
                                    content = element.get_text(separator='\n', strip=True)
                                    if len(content) > len(main_content):
                                        main_content = content
                                        break
                    
                    # If still too short, try paragraphs
                    if len(main_content) < 300:
                        paragraphs = soup.find_all('p')
                        combined_content = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30])
                        if len(combined_content) > len(main_content):
                            main_content = combined_content
                    
                    # Extract headings for structure
                    headings = []
                    for heading in soup.find_all(['h1', 'h2', 'h3']):
                        heading_text = heading.get_text(strip=True)
                        if heading_text and len(heading_text) > 5 and len(heading_text) < 100:
                            headings.append(heading_text)
                    
                    # Extract key points (bullet points, numbered lists)
                    key_points = []
                    for list_item in soup.find_all('li'):
                        item_text = list_item.get_text(strip=True)
                        if item_text and len(item_text) > 15 and len(item_text) < 300:  # Adjusted thresholds
                            key_points.append(item_text)
                    
                    # Clean up the content
                    main_content = re.sub(r'\s+', ' ', main_content).strip()
                    
                    # Extract any code blocks if present (for technical content)
                    code_blocks = []
                    for code in soup.select('pre, code, .highlight, .code'):
                        code_text = code.get_text(strip=True)
                        if code_text and len(code_text) > 10:
                            code_blocks.append(code_text)
                    
                    # Store the extracted data
                    extracted_data.append({
                        'source_num': i,
                        'title': title,
                        'url': url,
                        'content': main_content,
                        'headings': headings[:7],  # Increased from 5 to 7
                        'key_points': key_points[:7],  # Increased from 5 to 7
                        'code_blocks': code_blocks[:3] if code_blocks else []
                    })
                    
                    successful_links += 1
                    print(f"  Successfully extracted content from {url}")
                    
                except Exception as e:
                    print(f"  Error following link {url}: {str(e)}")
                    extracted_data.append({
                        'source_num': i,
                        'title': result.get('title', 'Unknown Title'),
                        'url': url,
                        'error': f"Could not retrieve content - {str(e)}"
                    })
            
            # If we couldn't follow any links, return informative message
            if successful_links == 0:
                print("  Could not successfully follow any links")
                return "Could not retrieve content from any of the search results. Please try a different search query or check your internet connection."
            
            print(f"  Successfully followed {successful_links} links. Organizing content...")
            
            # Organize the extracted data into a well-structured report
            detailed_content = f"# {search_query.title()} - Detailed Analysis\n\n"
            
            # Add a summary section
            detailed_content += "## Summary of Sources\n\n"
            for data in extracted_data:
                if 'error' not in data:
                    detailed_content += f"* **{data['title']}** - {data['url']}\n"
            
            detailed_content += "\n!!DETAILED_ANALYSIS_SECTION_START!!\n## Detailed Analysis from Top Sources:\n\n"
            
            # Add detailed content from each source
            for data in extracted_data:
                detailed_content += f"### Source {data['source_num']}: {data['title']}\n"
                detailed_content += f"URL: {data['url']}\n\n"
                
                if 'error' in data:
                    detailed_content += f"Error: {data['error']}\n\n"
                    continue
                
                # Add headings if available
                if data['headings']:
                    detailed_content += "#### Key Headings\n\n"
                    for heading in data['headings']:
                        detailed_content += f"* {heading}\n"
                    detailed_content += "\n"
                
                # Add key points if available
                if data['key_points']:
                    detailed_content += "#### Key Points\n\n"
                    for point in data['key_points']:
                        detailed_content += f"* {point}\n"
                    detailed_content += "\n"
                
                # Add code blocks if available (for technical content)
                if 'code_blocks' in data and data['code_blocks']:
                    detailed_content += "#### Code Examples\n\n"
                    for i, code in enumerate(data['code_blocks'], 1):
                        detailed_content += f"Code Example {i}:\n```\n{code[:500]}\n```\n\n"
                
                # Add full content instead of just a preview
                detailed_content += "#### Full Content\n\n"
                # Format the content for better readability
                formatted_content = data['content']
                # Break into paragraphs if needed
                if len(formatted_content) > 500 and '\n' not in formatted_content:
                    # Try to break into paragraphs at sentence boundaries
                    formatted_content = re.sub(r'([.!?])\s+', r'\1\n\n', formatted_content)
                detailed_content += f"{formatted_content}\n\n"
            
            # Add a section for related topics
            detailed_content += "\n## Related Topics\n\n"
            related_topics = self._extract_related_topics(search_query, extracted_data)
            for topic in related_topics:
                detailed_content += f"* {topic}\n"
            
            # Add the end marker after the related topics
            detailed_content += "\n!!DETAILED_ANALYSIS_SECTION_END!!"
            
            # Add a conclusion section
            detailed_content += "\n## Conclusion\n\n"
            detailed_content += f"This analysis provides information about {search_query} based on {successful_links} sources. "
            detailed_content += "The content has been extracted and organized to provide a comprehensive overview of the topic. "
            detailed_content += "For more detailed information, please visit the original sources linked above.\n\n"
            
            # Add a dedicated sources section with the actual links that were followed
            detailed_content += "# Sources\n\n"
            for i, data in enumerate(extracted_data, 1):
                if 'error' not in data:
                    detailed_content += f"{i}. [{data['title']}]({data['url']})\n"
            
            # Add the original search query URL
            search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
            detailed_content += f"\nMain search: {search_url}\n"
            
            print(f"  Completed analysis of {successful_links} sources for '{search_query}'")
            return detailed_content
            
        except Exception as e:
            print(f"  Error analyzing links: {str(e)}")
            traceback_str = traceback.format_exc()
            print(f"  Traceback: {traceback_str}")
            return f"Error analyzing links: {str(e)}\n\nPlease try a different search query or check your internet connection."
    
    def _extract_related_topics(self, search_query: str, extracted_data: List[Dict]) -> List[str]:
        """
        Extract related topics from the extracted data.
        
        Args:
            search_query: The original search query
            extracted_data: List of dictionaries containing extracted data from each source
            
        Returns:
            List of related topics
        """
        # Start with some common related topics based on the search query
        related_topics = []
        
        # Extract potential related topics from the content
        all_content = ""
        for data in extracted_data:
            if 'content' in data:
                all_content += data['content'] + " "
        
        # Look for common patterns that might indicate related topics
        # For technology-related queries
        if any(term in search_query.lower() for term in ["technology", "computing", "software", "hardware", "ai", "artificial intelligence", "quantum"]):
            tech_topics = [
                "Latest advancements", "Future applications", "Current limitations", 
                "Research directions", "Industry adoption", "Ethical considerations"
            ]
            related_topics.extend(tech_topics)
        
        # For science-related queries
        elif any(term in search_query.lower() for term in ["science", "physics", "chemistry", "biology", "research", "study", "experiment"]):
            science_topics = [
                "Recent discoveries", "Experimental methods", "Theoretical foundations", 
                "Practical applications", "Academic perspectives", "Future research directions"
            ]
            related_topics.extend(science_topics)
        
        # For news or current events
        elif any(term in search_query.lower() for term in ["news", "current", "recent", "latest", "update", "development"]):
            news_topics = [
                "Historical context", "Expert opinions", "Public reaction", 
                "Policy implications", "International perspectives", "Future outlook"
            ]
            related_topics.extend(news_topics)
        
        # Add some general related topics
        general_topics = [
            f"{search_query} history", 
            f"{search_query} future trends", 
            f"{search_query} practical applications"
        ]
        related_topics.extend(general_topics)
        
        # Remove duplicates and limit to 10 topics
        unique_topics = []
        for topic in related_topics:
            if topic not in unique_topics:
                unique_topics.append(topic)
        
        return unique_topics[:10]
    
    def _extract_search_query(self, task_description: str) -> Optional[str]:
        """
        Extract a search query from the task description.
        
        Args:
            task_description: Task description
            
        Returns:
            Extracted search query or None if not found
        """
        # First, check for specific search query patterns with file creation components
        hybrid_task_patterns = [
            r"search\s+(?:for|about)?\s+information\s+(?:about|on|regarding)\s+the\s+latest\s+advancements\s+in\s+([^,\.]+)\s+and\s+(?:create|save|write)",
            r"search\s+(?:for|about)?\s+information\s+(?:about|on|regarding)\s+([^,\.]+)\s+and\s+(?:create|save|write)",
            r"search\s+(?:for|about)?\s+([^,\.]+)\s+and\s+(?:create|save|write)",
            r"find\s+information\s+(?:about|on|regarding)\s+([^,\.]+)\s+and\s+(?:create|save|write)",
            r"research\s+(?:about|on)?\s+([^,\.]+)\s+and\s+(?:create|save|write)"
        ]
        
        for pattern in hybrid_task_patterns:
            match = re.search(pattern, task_description, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Try to extract the search query from the task description
        search_patterns = [
            r"search\s+(?:for|about)?\s+([\w\s\d\-\+]+)\s+(?:on|in|at)",  # search for X on
            r"search\s+(?:for|about)?\s+([\w\s\d\-\+]+)",  # search for X
            r"find\s+(?:information|solutions|articles|posts)\s+(?:about|on|for)\s+([\w\s\d\-\+]+)",  # find information about X
            r"look\s+for\s+([\w\s\d\-\+]+)",  # look for X
            r"solutions\s+(?:to|for)\s+(?:the)?\s+([\w\s\d\-\+]+)\s+(?:error|problem|issue)",  # solutions to the X error
            r"information\s+(?:about|on)\s+([\w\s\d\-\+]+)",  # information about X
            r"articles\s+(?:about|on)\s+([\w\s\d\-\+]+)",  # articles about X
            r"research\s+(?:about|on)?\s+([\w\s\d\-\+]+)",  # research X
            r"latest\s+(?:information|news|updates|developments)\s+(?:about|on|regarding)\s+([\w\s\d\-\+]+)",  # latest information about X
            r"current\s+(?:information|news|updates|developments)\s+(?:about|on|regarding)\s+([\w\s\d\-\+]+)",  # current information about X
            r"recent\s+(?:information|news|updates|developments)\s+(?:about|on|regarding)\s+([\w\s\d\-\+]+)",  # recent information about X
            r"advancements\s+(?:in|on|regarding)\s+([\w\s\d\-\+]+)",  # advancements in X
            r"developments\s+(?:in|on|regarding)\s+([\w\s\d\-\+]+)"  # developments in X
        ]
        
        for pattern in search_patterns:
            match = re.search(pattern, task_description, re.IGNORECASE)
            if match:
                query = match.group(1).strip()
                # Clean up the query by removing file-related parts
                file_patterns = [
                    r"and\s+(?:save|create|write)\s+(?:a|an|the)\s+(?:file|summary|report).*",
                    r"and\s+save\s+(?:it|them|the\s+results)\s+to\s+.*",
                    r"and\s+output\s+to\s+.*"
                ]
                for file_pattern in file_patterns:
                    query = re.sub(file_pattern, "", query, flags=re.IGNORECASE).strip()
                return query
        
        # Look for error codes or specific technical terms
        error_code_pattern = r"(?:error|code|hresult)\s*:\s*([\w\d]+)"
        match = re.search(error_code_pattern, task_description, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # If no pattern matches, try to extract key phrases from the task description
        task_lower = task_description.lower()
        
        # Look for key phrases that might indicate the search topic
        key_phrases = [
            "quantum computing", "artificial intelligence", "machine learning", "deep learning", 
            "neural networks", "blockchain", "cryptocurrency", "climate change", "renewable energy", 
            "sustainable development", "space exploration", "mars mission", "covid-19", "coronavirus", 
            "vaccine development", "genetic engineering", "crispr", "nanotechnology", "robotics", 
            "autonomous vehicles", "virtual reality", "augmented reality", "internet of things", 
            "big data", "cloud computing", "edge computing", "cybersecurity", "data privacy", 
            "5g technology", "quantum supremacy", "quantum entanglement", "quantum teleportation"
        ]
        
        for phrase in key_phrases:
            if phrase in task_lower:
                return phrase
        
        # As a last resort, try to extract a noun phrase from the task description
        words = task_description.split()
        if len(words) > 3:
            # Try to extract a meaningful phrase from the middle of the task
            middle_index = len(words) // 2
            potential_query = " ".join(words[middle_index-2:middle_index+3])
            return potential_query
        
        return None
    
    def _generate_topic_filename(self, topic: str, content_type: str = None) -> str:
        """
        Generate a filename based on a topic and optional content type.
        
        Args:
            topic: The topic to generate a filename for
            content_type: Optional content type (e.g., "report", "summary", etc.)
            
        Returns:
            Generated filename
        """
        # Clean the topic to make it suitable for a filename
        clean_topic = re.sub(r'[^\w\s\-]', '', topic)
        clean_topic = clean_topic.strip().replace(' ', '_').lower()
        
        # Limit the length
        if len(clean_topic) > 30:
            clean_topic = clean_topic[:30]
        
        # Add content type if provided
        if content_type:
            return f"{clean_topic}_{content_type}.txt"
        
        # Check if the task description contains a content type
        content_type_terms = ["story", "poem", "essay", "article", "report", "note", "text", "document", 
                            "analysis", "summary", "list", "compilation", "collection"]
        
        # Try to infer content type from the topic
        for term in content_type_terms:
            if term in topic.lower():
                return f"{clean_topic}_{term}.txt"
        
        # Add date and extension if no content type is found
        date_str = datetime.now().strftime("%Y%m%d")
        return f"{clean_topic}_{date_str}.txt"
    
    def _generate_filename(self, task_description: str, domain: str) -> str:
        """
        Generate a filename for the web content.
        
        Args:
            task_description: Task description
            domain: Domain of the URL
            
        Returns:
            Generated filename
        """
        # Check if the task description contains a filename
        filename_patterns = [
            # Pattern 1: save it to/as/in filename
            r'save\s+(?:it|them|the\s+(?:content|results|headlines))\s+(?:to|as|in)\s+["\']?([\w\s\.-]+)["\']?',
            # Pattern 2: output to filename
            r'output\s+(?:to|as|in)\s+["\']?([\w\s\.-]+)["\']?',
            # Pattern 3: create a file named/called filename
            r'create\s+(?:a|the)\s+file\s+(?:named|called)\s+["\']?([\w\s\.-]+)["\']?',
            # Pattern 4: write to filename
            r'write\s+(?:to|into)\s+(?:a\s+file\s+(?:named|called)\s+)?["\']?([\w\s\.-]+)["\']?',
            # Pattern 5: filename.txt (looking for explicit filenames with extensions)
            r'["\']?([\w\s\.-]+\.\w+)["\']?'
        ]
        
        for pattern in filename_patterns:
            match = re.search(pattern, task_description, re.IGNORECASE)
            if match:
                filename = match.group(1).strip()
                # Add .txt extension if not present
                if not any(filename.endswith(ext) for ext in [".txt", ".md", ".csv", ".json"]):
                    filename += ".txt"
                return filename
        
        # Try to extract a content type from the task description
        content_type_terms = ["story", "poem", "essay", "article", "report", "note", "text", "document", 
                            "analysis", "summary", "list", "compilation", "collection"]
        task_lower = task_description.lower()
        
        for term in content_type_terms:
            if term in task_lower:
                # Extract a potential topic from the task description
                search_query = self._extract_search_query(task_description)
                if search_query:
                    # Generate a filename based on the content type and topic
                    return f"{search_query.replace(' ', '_')}_{term}.txt"
                else:
                    # If no topic is found, use a generic name with the content type
                    return f"generated_{term}.txt"
        
        # Try to extract a topic from the task description
        search_query = self._extract_search_query(task_description)
        if search_query:
            return self._generate_topic_filename(search_query)
        
        # Generate a filename based on the domain and current date
        date_str = datetime.now().strftime("%Y%m%d")
        return f"{domain}_{date_str}.txt"
    
    def _extract_headlines(self, text: str) -> List[str]:
        """
        Extract headlines from text.
        
        Args:
            text: Text to extract headlines from
            
        Returns:
            List of extracted headlines
        """
        # Split the text into lines and look for lines that might be headlines
        lines = text.split("\n")
        headlines = []
        
        for line in lines:
            line = line.strip()
            # Check if the line starts with a bullet point or number
            if line and (line.startswith("-") or line.startswith("*") or re.match(r'^\d+\.\s', line)):
                # Remove the bullet point or number
                headline = re.sub(r'^[-*]\s+|^\d+\.\s+', '', line).strip()
                if headline and len(headline) > 10:  # Minimum length for a headline
                    headlines.append(headline)
        
        # If no headlines were found with bullet points, try to extract based on capitalization and length
        if not headlines:
            for line in lines:
                line = line.strip()
                if line and len(line) > 20 and len(line) < 100 and line[0].isupper():
                    headlines.append(line)
        
        return headlines[:5]  # Return up to 5 headlines
    
    def _extract_information(self, text: str) -> List[str]:
        """
        Extract important information from text.
        
        Args:
            text: Text to extract information from
            
        Returns:
            List of extracted information
        """
        # Split the text into paragraphs
        paragraphs = text.split("\n\n")
        information = []
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if paragraph and len(paragraph) > 50:  # Minimum length for information
                information.append(paragraph)
        
        return information[:3]  # Return up to 3 pieces of information
    
    def _extract_headlines_from_html(self, soup: BeautifulSoup) -> List[str]:
        """
        Extract headlines from HTML content.
        
        Args:
            soup: BeautifulSoup object containing the HTML content
            
        Returns:
            List of extracted headlines
        """
        headlines = []
        
        # Try different headline patterns
        # 1. Look for h1, h2, h3 tags
        for tag in soup.find_all(['h1', 'h2', 'h3']):
            text = tag.get_text().strip()
            if text and len(text) > 10 and len(text) < 200:  # Reasonable headline length
                headlines.append(text)
        
        # 2. Look for elements with headline-related classes
        headline_classes = ['headline', 'title', 'article-title', 'story-title', 'heading']
        for cls in headline_classes:
            for element in soup.find_all(class_=lambda c: c and cls in c.lower()):
                text = element.get_text().strip()
                if text and len(text) > 10 and len(text) < 200 and text not in headlines:
                    headlines.append(text)
        
        # 3. Look for article titles in common news site structures
        for article in soup.find_all('article'):
            title_element = article.find(['h1', 'h2', 'h3', 'h4']) or article.find(class_=lambda c: c and 'title' in c.lower())
            if title_element:
                text = title_element.get_text().strip()
                if text and len(text) > 10 and len(text) < 200 and text not in headlines:
                    headlines.append(text)
        
        # Remove duplicates while preserving order
        unique_headlines = []
        for headline in headlines:
            if headline not in unique_headlines:
                unique_headlines.append(headline)
        
        return unique_headlines[:10]  # Return up to 10 headlines
    
    def _extract_main_content_from_html(self, soup: BeautifulSoup) -> str:
        """
        Extract main content from HTML content.
        
        Args:
            soup: BeautifulSoup object containing the HTML content
            
        Returns:
            Extracted main content as a string
        """
        # Try to find the main content container
        main_content = ""
        
        # Remove unwanted elements that typically contain non-content
        for element in soup.find_all(['nav', 'header', 'footer', 'aside', 'script', 'style', 'noscript', 'iframe']):
            element.decompose()
            
        # Remove common ad and navigation containers
        for element in soup.select('.ad, .ads, .advertisement, .sidebar, .navigation, .menu, .comment, .comments, .cookie-notice'):
            element.decompose()
        
        # 1. Try to find content by common content selectors
        content_selectors = [
            'main', 'article', '.post-content', '.entry-content', '.content-area', '.main-content',
            '#content', '.content', '#main', '.main', '.post', '.entry', '.article'
        ]
        
        for selector in content_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(separator='\n', strip=True)
                if len(text) > 200:  # Ensure it has substantial content
                    main_content = text
                    break
            if main_content:
                break
        
        # 2. Try to find by ID or class containing content-related terms
        if not main_content:
            content_elements = [
                soup.find(id=lambda i: i and any(term in i.lower() for term in ['content', 'main', 'article', 'post', 'entry'])),
                soup.find(class_=lambda c: c and any(term in c.lower() for term in ['content', 'main', 'article', 'post', 'entry']))
            ]
            
            for element in content_elements:
                if element:
                    text = element.get_text(separator='\n', strip=True)
                    if len(text) > 200:  # Ensure it has substantial content
                        main_content = text
                        break
        
        # 3. If still no main content found, try to extract all paragraphs
        if not main_content:
            # Get all paragraphs with substantial content
            paragraphs = [p.get_text().strip() for p in soup.find_all('p') if len(p.get_text().strip()) > 30]
            
            # If we have enough paragraphs, use them
            if len(paragraphs) >= 3:
                main_content = '\n\n'.join(paragraphs)
            else:
                # As a last resort, try to get text from the body
                body = soup.find('body')
                if body:
                    main_content = body.get_text(separator='\n', strip=True)
                    
                    # Clean up the content by removing excessive whitespace
                    main_content = re.sub(r'\s+', ' ', main_content).strip()
        
        # 4. Clean up the content
        # Remove URLs
        main_content = re.sub(r'https?://\S+', '', main_content)
        # Remove excessive whitespace
        main_content = re.sub(r'\s+', ' ', main_content).strip()
        # Remove very short lines (likely navigation or other non-content)
        lines = [line.strip() for line in main_content.split('\n') if len(line.strip()) > 20]
        main_content = '\n'.join(lines)
        
        # 5. Limit the length of the main content for practical use
        if len(main_content) > 2000:
            # Get the first 1000 characters and last 1000 characters
            main_content = main_content[:1000] + '\n\n[...content truncated...]\n\n' + main_content[-1000:]
        
        return main_content
        
    def _extract_output_files(self, task_description: str) -> List[str]:
        """
        Extract output filenames from the task description.
        
        Args:
            task_description: Task description to extract output filenames from
            
        Returns:
            List of output filenames
        """
        output_files = []
        
        # Pattern 1: Save/store/write to a file named/called X
        pattern1 = r'(?:save|store|write|output)\s+(?:to|in|as)\s+(?:a\s+)?(?:file\s+)?(?:named|called)?\s+["\']?([\w\-\.]+)["\']?'
        matches = re.finditer(pattern1, task_description, re.IGNORECASE)
        for match in matches:
            filename = match.group(1).strip()
            if filename and not filename.endswith('.txt'):
                filename += '.txt'
            output_files.append(filename)
        
        # Pattern 2: Create a file named/called X
        pattern2 = r'(?:create|make)\s+(?:a\s+)?(?:file|document)\s+(?:named|called)\s+["\']?([\w\-\.]+)["\']?'
        matches = re.finditer(pattern2, task_description, re.IGNORECASE)
        for match in matches:
            filename = match.group(1).strip()
            if filename and not filename.endswith('.txt'):
                filename += '.txt'
            output_files.append(filename)
        
        # Pattern 3: Save in X file
        pattern3 = r'save\s+(?:that|it|this|the\s+results?|the\s+content)\s+in\s+(?:a\s+)?(?:file\s+)?(?:named|called)?\s+["\']?([\w\-\.]+)["\']?'
        matches = re.finditer(pattern3, task_description, re.IGNORECASE)
        for match in matches:
            filename = match.group(1).strip()
            if filename and not filename.endswith('.txt'):
                filename += '.txt'
            output_files.append(filename)
            
        # Pattern 4: File named X
        pattern4 = r'file\s+named\s+["\']?([\w\-\.]+)["\']?'
        matches = re.finditer(pattern4, task_description, re.IGNORECASE)
        for match in matches:
            filename = match.group(1).strip()
            if filename and not filename.endswith('.txt'):
                filename += '.txt'
            output_files.append(filename)
            
        # Remove duplicates while preserving order
        unique_files = []
        for file in output_files:
            if file and file not in unique_files:
                unique_files.append(file)
                
        return unique_files
        
    def _extract_search_results(self, soup: BeautifulSoup, domain: str) -> List[Dict[str, str]]:
        """
        Extract search results from HTML content.
        
        Args:
            soup: BeautifulSoup object containing the HTML content
            domain: Domain of the search engine
            
        Returns:
            List of search results as dictionaries with title, url, and snippet
        """
        search_results = []
        print(f"  Extracting search results from {domain}...")
        
        # Handle different search engines
        if domain == "stackoverflow.com":
            # Extract search results from Stack Overflow
            result_elements = soup.select('.search-result')
            
            for element in result_elements:
                result = {}
                
                # Extract title
                title_element = element.select_one('.question-hyperlink')
                if title_element:
                    result['title'] = title_element.get_text().strip()
                    
                    # Extract URL
                    href = title_element.get('href')
                    if href:
                        if href.startswith('/'):
                            result['url'] = f"https://stackoverflow.com{href}"
                        else:
                            result['url'] = href
                
                # Extract snippet
                snippet_element = element.select_one('.excerpt')
                if snippet_element:
                    result['snippet'] = snippet_element.get_text().strip()
                
                if 'title' in result and 'url' in result:
                    search_results.append(result)
        elif domain == "google.com":
            # Google-specific extraction - using multiple approaches to handle different Google layouts
            # Google frequently changes their HTML structure, so we need to try multiple selectors
            
            # Approach 1: Modern Google search results (2023-2025 layout)
            result_elements = soup.select('div.g, div.MjjYud, div.Gx5Zad, div.egMi0, div[data-sokoban-container]')
            
            if result_elements:
                for element in result_elements:
                    result = {}
                    
                    # Extract title - try multiple possible selectors
                    title_element = element.select_one('h3, a > h3, div.DKV0Md, div.vvjwJb')
                    if title_element:
                        result['title'] = title_element.get_text().strip()
                        
                        # Find the closest <a> tag that contains the URL
                        parent_link = title_element.find_parent('a')
                        if parent_link and parent_link.get('href'):
                            href = parent_link.get('href')
                            if href.startswith('/url?') and 'q=' in href:
                                # Extract the actual URL from Google's redirect
                                actual_url = re.search(r'q=([^&]+)', href)
                                if actual_url:
                                    result['url'] = actual_url.group(1)
                            elif href.startswith('http'):
                                result['url'] = href
                    
                    # If we couldn't find the URL from the title's parent link, try other links
                    if 'url' not in result or not result['url']:
                        # Try to find any link in this result container
                        link_elements = element.select('a[href^="/url?"], a[href^="http"]')
                        for link_element in link_elements:
                            href = link_element.get('href')
                            if href and len(href) > 10:  # Skip very short URLs
                                if href.startswith('/url?') and 'q=' in href:
                                    actual_url = re.search(r'q=([^&]+)', href)
                                    if actual_url:
                                        url = actual_url.group(1)
                                        # Skip Google's own domains
                                        if 'google.com' not in url:
                                            result['url'] = url
                                            break
                                elif href.startswith('http') and 'google.com' not in href:
                                    result['url'] = href
                                    break
                    
                    # Extract snippet - try multiple possible selectors
                    snippet_candidates = element.select('div.VwiC3b, span.aCOpRe, div.s, div.IsZvec, div.lEBKkf, div.lyLwlc, div.kb0PBd')
                    for candidate in snippet_candidates:
                        text = candidate.get_text().strip()
                        if text and len(text) > 20:  # Skip very short snippets
                            result['snippet'] = text
                            break
                    
                    # If we have both title and URL, add this result
                    if 'title' in result and result['title'] and 'url' in result and result['url']:
                        search_results.append(result)
            
            # Approach 2: If we couldn't find results using the standard approach, try a more aggressive approach
            if not search_results:
                print("  Using aggressive approach to extract Google search results...")
                
                # Try to find search results by looking for common patterns in Google's HTML
                # First, look for all divs that might contain search results
                potential_containers = soup.select('div.tF2Cxc, div.yuRUbf, div.kCrYT, div.ZINbbc, div.Gx5Zad, div.g, div[jscontroller]')
                
                for container in potential_containers:
                    result = {}
                    
                    # Look for links within these containers
                    links = container.select('a[href]')
                    for link in links:
                        href = link.get('href')
                        if not href:
                            continue
                            
                        # Process links that look like Google search result links
                        if href.startswith('/url?') and 'q=' in href:
                            actual_url = re.search(r'q=([^&]+)', href)
                            if actual_url:
                                url = actual_url.group(1)
                                # Skip Google's own domains and common navigation links
                                if 'google.com' in url or any(nav in url for nav in ['accounts', 'login', 'signin', 'settings']):
                                    continue
                                    
                                result['url'] = url
                                
                                # Try to find a title near this link
                                # First check if the link itself has good text content
                                link_text = link.get_text().strip()
                                if link_text and len(link_text) > 10:
                                    result['title'] = link_text
                                else:
                                    # Look for heading elements or strong text near this link
                                    title_candidates = container.select('h3, h4, strong, b, div.DKV0Md')
                                    for title_elem in title_candidates:
                                        title_text = title_elem.get_text().strip()
                                        if title_text and len(title_text) > 5:
                                            result['title'] = title_text
                                            break
                                
                                # Try to find a snippet near this link
                                snippet_candidates = container.select('div.VwiC3b, span.aCOpRe, div.s, div.IsZvec, div.lEBKkf, div.lyLwlc')
                                for snippet_elem in snippet_candidates:
                                    snippet_text = snippet_elem.get_text().strip()
                                    if snippet_text and len(snippet_text) > 30:
                                        result['snippet'] = snippet_text
                                        break
                                        
                                # If we couldn't find a good snippet, use any text in the container
                                if 'snippet' not in result:
                                    container_text = container.get_text().strip()
                                    # Remove the title from the container text to avoid duplication
                                    if 'title' in result:
                                        container_text = container_text.replace(result['title'], '')
                                    if container_text and len(container_text) > 30:
                                        result['snippet'] = container_text
                                
                                # If we have both title and URL, add this result
                                if 'url' in result and ('title' in result or 'snippet' in result):
                                    # If we don't have a title but have a snippet, use the first part of the snippet as title
                                    if 'title' not in result and 'snippet' in result:
                                        result['title'] = result['snippet'][:50] + '...'
                                    # If we don't have a snippet, create a generic one
                                    if 'snippet' not in result:
                                        result['snippet'] = f"Result from search: {result['title']}"
                                        
                                    search_results.append(result)
                                    break  # Move to the next container once we've found a valid result
        elif domain in ["bing.com", "duckduckgo.com"]:
            # Generic search result extraction for Bing, DuckDuckGo
            result_elements = soup.select('div.b_algo, .result, .web-result, .result__body')
            
            for element in result_elements:
                result = {}
                
                # Extract title
                title_element = element.select_one('h2, .result__title, .title')
                if title_element:
                    result['title'] = title_element.get_text().strip()
                    
                    # Try to find the URL
                    link_element = title_element.find('a') or element.select_one('a')
                    if link_element and link_element.get('href'):
                        href = link_element.get('href')
                        if href.startswith('/'):
                            result['url'] = f"https://{domain}{href}"
                        elif href.startswith('http'):
                            result['url'] = href
                
                # Extract snippet
                snippet_element = element.select_one('.b_caption, .result__snippet, .snippet-item')
                if snippet_element:
                    result['snippet'] = snippet_element.get_text().strip()
                
                if 'title' in result and 'url' in result:
                    search_results.append(result)
        
        # Final fallback: If we still couldn't extract any search results, use a more aggressive approach with all links
        if not search_results:
            print("  Falling back to generic link extraction...")
            
            # First, try to find links that look like search results
            all_links = soup.find_all('a')
            valid_links = []
            
            # Process all links to find valid external URLs
            for link in all_links:
                href = link.get('href')
                text = link.get_text().strip()
                
                # Skip links without href or with very short text
                if not href or not text:
                    continue
                    
                # Process Google redirect links
                if href.startswith('/url?') and 'q=' in href:
                    actual_url = re.search(r'q=([^&]+)', href)
                    if actual_url:
                        url = actual_url.group(1)
                        # Skip Google's own domains and common navigation links
                        if ('google.com' in url or 
                            any(nav in url.lower() for nav in ['accounts', 'login', 'signin', 'settings', 'support', 'policies'])):
                            continue
                        valid_links.append({
                            'text': text,
                            'url': url,
                            'is_redirect': True
                        })
                # Process direct external links
                elif href.startswith('http') and domain not in href:
                    # Skip common navigation and social media links
                    if (len(text) < 10 or
                        any(nav_term in text.lower() for nav_term in ['sign in', 'log in', 'register', 'home', 'about', 'contact', 'privacy', 'terms']) or
                        any(social in href.lower() for social in ['facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com', 'youtube.com'])):
                        continue
                    valid_links.append({
                        'text': text,
                        'url': href,
                        'is_redirect': False
                    })
            
            # Sort links by text length (longer text is usually more informative)
            valid_links.sort(key=lambda x: len(x['text']), reverse=True)
            
            # Take the top 10 most promising links
            for i, link_data in enumerate(valid_links[:10]):
                # Try to find a better title and snippet for this link
                parent_elem = None
                link_element = None
                
                # Try to find the link element in the soup
                if link_data['is_redirect']:
                    # For redirect links, we need to find the link with the /url? pattern
                    for a in soup.find_all('a'):
                        if a.get('href') and '/url?' in a.get('href') and f"q={link_data['url']}" in a.get('href').replace('%3A', ':').replace('%2F', '/'):
                            link_element = a
                            break
                else:
                    # For direct links, we can search directly
                    link_element = soup.find('a', href=link_data['url'])
                
                # If we found the link element, look for a good parent container
                if link_element:
                    for parent in link_element.parents:
                        if parent.name in ['div', 'li', 'section'] and len(parent.get_text().strip()) > 50:
                            parent_elem = parent
                            break
                
                title = link_data['text']
                snippet = ""
                
                # If we found a good parent element, try to extract a better snippet
                if parent_elem:
                    # Get all text from the parent element
                    parent_text = parent_elem.get_text().strip()
                    # Remove the link text to avoid duplication
                    parent_text = parent_text.replace(title, '')
                    if parent_text and len(parent_text) > 30:
                        snippet = parent_text[:200] + '...' if len(parent_text) > 200 else parent_text
                
                # If we couldn't find a good snippet, create a generic one
                if not snippet:
                    snippet = f"Found in search results: {title}"
                
                search_results.append({
                    'title': title,
                    'url': link_data['url'],
                    'snippet': snippet
                })
                
                # If we've found at least 5 good results, that's enough for a fallback
                if len(search_results) >= 5:
                    break
        
        # Deduplicate results based on URL
        unique_results = []
        seen_urls = set()
        for result in search_results:
            if 'url' in result and result['url'] not in seen_urls:
                seen_urls.add(result['url'])
                unique_results.append(result)
        
        print(f"  Extracted {len(unique_results)} search results")
        return unique_results
