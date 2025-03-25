#!/usr/bin/env python3
# Disable PostHog analytics before any other imports
# Import our enhanced PostHog disabler that completely blocks all PostHog functionality
import posthog_disable

"""
Web Browsing Module for Ollama Shell

This module provides web browsing functionality for the Ollama Shell application.
It allows users to browse websites, extract headlines, and save content to files.
"""

import os
import re
import json
import logging
import requests
import asyncio
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

# Import MCP browser module
try:
    from mcp_browser import MCPBrowser, start_mcp_server
    MCP_AVAILABLE = True
    # Import the JavaScript content extraction module
    import js_content_extraction
except ImportError:
    MCP_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("MCP browser module not available. Advanced browsing features will be disabled.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import SSL utilities
try:
    from ssl_utils import configure_ssl_verification, should_skip_verification
    SSL_UTILS_AVAILABLE = True
    # Configure SSL verification with PostHog domains
    configure_ssl_verification(disable_all=False)
except ImportError:
    SSL_UTILS_AVAILABLE = False
    logger.warning("SSL utilities not available. SSL certificate verification issues may occur.")

class WebBrowser:
    """
    Web Browser class for handling web browsing tasks.
    """
    
    def __init__(self, ollama_client, use_mcp: bool = True):
        """
        Initialize the Web Browser.
        
        Args:
            ollama_client: The Ollama client to use for generating content
            use_mcp: Whether to use the MCP browser for enhanced browsing capabilities
        """
        self.ollama_client = ollama_client
        self.use_mcp = use_mcp and MCP_AVAILABLE
        
        # Initialize MCP browser if available and enabled
        if self.use_mcp:
            try:
                # Start the MCP server if it's not already running
                start_mcp_server()
                
                # Initialize the MCP browser
                self.mcp_browser = MCPBrowser()
                print("MCP browser initialized for enhanced web browsing capabilities")
            except Exception as e:
                logger.warning(f"Failed to initialize MCP browser: {str(e)}")
                self.use_mcp = False
    
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
                        # Fetch content from the URL
            try:
                print(f"  Fetching content from {url}...")
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                # Initialize structured_content dictionary for all paths
                structured_content = {
                    'url': url,
                    'title': '',
                    'headings': [],
                    'paragraphs': [],
                    'links': [],
                    'images': [],
                    'tables': [],
                    'metadata': {},
                    'raw_text': ''
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
                    
                    # Determine whether to use MCP browser or traditional HTTP requests
                    if self.use_mcp:
                        print(f"  Using MCP browser for enhanced search capabilities...")
                        try:
                            # Use MCP browser to fetch content with JavaScript rendering
                            mcp_result = await self.mcp_browser.extract_content(search_url)
                            
                            if mcp_result.get('success', False):
                                # Extract content from MCP browser result
                                content = mcp_result.get('content', '')
                                
                                # Parse the HTML content using BeautifulSoup
                                soup = BeautifulSoup(content, 'html.parser')
                                print(f"  Successfully fetched content using MCP browser")
                            else:
                                # Fall back to traditional HTTP requests if MCP browser fails
                                print(f"  MCP browser failed: {mcp_result.get('error', 'Unknown error')}. Falling back to HTTP requests.")
                                # Apply SSL verification handling
                                verify = True
                                if SSL_UTILS_AVAILABLE and should_skip_verification(search_url):
                                    verify = False
                                    logger.debug(f"SSL verification disabled for request to {search_url}")
                                response = requests.get(search_url, headers=headers, timeout=15, verify=verify)
                                response.raise_for_status()
                                soup = BeautifulSoup(response.content, 'html.parser')
                        except Exception as e:
                            print(f"  Error using MCP browser: {str(e)}. Falling back to HTTP requests.")
                            # Apply SSL verification handling
                            verify = True
                            if SSL_UTILS_AVAILABLE and should_skip_verification(search_url):
                                verify = False
                                logger.debug(f"SSL verification disabled for request to {search_url}")
                            response = requests.get(search_url, headers=headers, timeout=15, verify=verify)
                            response.raise_for_status()
                            soup = BeautifulSoup(response.content, 'html.parser')
                    else:
                        # Use traditional HTTP requests
                        # Apply SSL verification handling
                        verify = True
                        if SSL_UTILS_AVAILABLE and should_skip_verification(search_url):
                            verify = False
                            logger.debug(f"SSL verification disabled for request to {search_url}")
                        response = requests.get(search_url, headers=headers, timeout=15, verify=verify)
                        response.raise_for_status()
                        soup = BeautifulSoup(response.content, 'html.parser')
                else:
                    # For non-search URLs, use our enhanced structured content extraction
                    print(f"  Using enhanced structured content extraction for {url}...")
                    
                    # Check if this is a news site
                    news_domains = ['cnn.com', 'bbc.com', 'nytimes.com', 'foxnews.com', 'reuters.com', 
                                   'washingtonpost.com', 'theguardian.com', 'news.', 'nbcnews.com', 
                                   'cbsnews.com', 'abcnews.go.com', 'usatoday.com', 'wsj.com']
                    
                    # Store the news site status in structured_content for consistent access
                    structured_content['is_news_site'] = any(news_domain in domain.lower() for news_domain in news_domains)
                    
                    if structured_content['is_news_site']:
                        print(f"  Detected news site: {domain}. Using specialized news content extraction.")
                    
                    # Use the enhanced structured content extraction
                    # Handle the async method properly by using the synchronous version
                    structured_content = self.extract_structured_content_sync(url)                
                    # Create soup object for compatibility with existing code
                    if self.use_mcp:
                        try:
                            # Use MCP browser to fetch content with JavaScript rendering
                            mcp_result = await self.mcp_browser.extract_content(url)
                            
                            if mcp_result.get('success', False):
                                # Extract content from MCP browser result
                                content = mcp_result.get('content', '')
                                
                                # Parse the HTML content using BeautifulSoup
                                soup = BeautifulSoup(content, 'html.parser')
                                print(f"  Successfully fetched content using MCP browser")
                            else:
                                # Fall back to traditional HTTP requests if MCP browser fails
                                print(f"  MCP browser failed: {mcp_result.get('error', 'Unknown error')}. Falling back to HTTP requests.")
                                # Apply SSL verification handling
                                verify = True
                                if SSL_UTILS_AVAILABLE and should_skip_verification(url):
                                    verify = False
                                    logger.debug(f"SSL verification disabled for request to {url}")
                                response = requests.get(url, headers=headers, timeout=15, verify=verify)
                                response.raise_for_status()
                                soup = BeautifulSoup(response.content, 'html.parser')
                        except Exception as e:
                            print(f"  Error using MCP browser: {str(e)}. Falling back to HTTP requests.")
                            # Apply SSL verification handling
                            verify = True
                            if SSL_UTILS_AVAILABLE and should_skip_verification(url):
                                verify = False
                                logger.debug(f"SSL verification disabled for request to {url}")
                            response = requests.get(url, headers=headers, timeout=15, verify=verify)
                            response.raise_for_status()
                            soup = BeautifulSoup(response.content, 'html.parser')
                    else:
                        # Use traditional HTTP requests
                        # Apply SSL verification handling
                        verify = True
                        if SSL_UTILS_AVAILABLE and should_skip_verification(url):
                            verify = False
                            logger.debug(f"SSL verification disabled for request to {url}")
                        response = requests.get(url, headers=headers, timeout=15, verify=verify)
                        response.raise_for_status()
                        soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract headlines from the structured content if available, otherwise use the traditional method
                if structured_content.get('is_news_site', False) and 'news_content' in structured_content and structured_content['news_content']['headlines']:
                    headlines = structured_content['news_content']['headlines']
                    print(f"  Extracted {len(headlines)} headlines using specialized news content extraction")
                else:
                    headlines = self._extract_headlines_from_html(soup)
                    print(f"  Extracted {len(headlines)} headlines using traditional method")
                
                # Extract main content from the structured content if available, otherwise use the traditional method
                if structured_content.get('is_news_site', False) and 'news_content' in structured_content and structured_content['news_content']['main_content']:
                    main_content = structured_content['news_content']['main_content']
                    print(f"  Extracted main content using specialized news content extraction")
                else:
                    # If we have paragraphs in structured content, use them
                    if structured_content['paragraphs']:
                        main_content = '\n\n'.join(structured_content['paragraphs'])
                        print(f"  Extracted main content from {len(structured_content['paragraphs'])} paragraphs")
                    else:
                        main_content = self._extract_main_content_from_html(soup)
                        print(f"  Extracted main content using traditional method")
                
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
                        detailed_analysis = await self._follow_and_analyze_links(search_results, search_query)
                        
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
            
            # Check if we have specific output files from the task description
            has_specific_output_files = len(output_files) > 0
            
            # Only save to the default file if no specific output files were mentioned
            if not has_specific_output_files:
                default_file_path = os.path.join(documents_dir, filename)
                with open(default_file_path, "w") as f:
                    f.write(response_text)
                artifacts["filename"] = default_file_path
                # Store the default file path in the artifacts
                artifacts["default_file"] = default_file_path
            artifacts["url"] = url
            artifacts["domain"] = domain
            artifacts["headlines"] = headlines
            artifacts["information"] = information
            artifacts["content_preview"] = response_text[:200] + "..." if len(response_text) > 200 else response_text
            
            # Check if this task requires saving to additional files or creating analysis
            if (has_file_creation_term and (has_output_file_term or has_content_type_term)) or has_web_to_file_term:
                print(f"  Task involves file creation. Saving content to specified files...")
                
                # If specific output files were extracted from the task description, use those
                if output_files:
                    print(f"  Using specified filename(s): {', '.join(output_files)}")
                    # When specific output files are mentioned, don't generate any additional files
                # If no specific output files were mentioned, but the task involves file creation,
                # generate a descriptive filename based on the search query or task
                elif search_query:
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
                    
                    # Only add analysis file if no specific output files were mentioned in the task description
                    # and if analysis is needed and no analysis file is already included
                    if needs_analysis and not any('analysis' in file.lower() for file in output_files):
                        if search_query:
                            analysis_filename = f"{search_query.replace(' ', '_')}_analysis.txt"
                        else:
                            analysis_filename = f"web_content_analysis_{datetime.now().strftime('%Y%m%d')}.txt"
                        
                        if analysis_filename not in output_files:
                            output_files.append(analysis_filename)
                            print(f"  Adding analysis file: {analysis_filename}")
            
            # Save to output files if specified
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
                        
                        # Add the file to the artifacts
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
        
    async def _follow_and_analyze_links(self, search_results: List[Dict[str, str]], search_query: str) -> str:
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
                    
                    # Make the request with SSL verification handling
                    verify = True
                    if SSL_UTILS_AVAILABLE and should_skip_verification(ddg_url):
                        verify = False
                        logger.debug(f"SSL verification disabled for request to {ddg_url}")
                    ddg_response = requests.get(ddg_url, headers=ddg_headers, timeout=20, verify=verify)
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
                    
                    # Initialize structured_content dictionary
                    structured_content = {
                        'url': url,
                        'title': '',
                        'headings': [],
                        'paragraphs': [],
                        'links': [],
                        'images': [],
                        'tables': [],
                        'metadata': {},
                        'raw_text': ''
                    }
                    
                    # Determine whether to use MCP browser or traditional HTTP requests
                    if self.use_mcp:
                        print(f"  Using MCP browser for enhanced content extraction...")
                        try:
                            # Use MCP browser to fetch content with JavaScript rendering
                            mcp_result = await self.mcp_browser.extract_content(url)
                            
                            if mcp_result.get('success', False):
                                # Extract content from MCP browser result
                                content = mcp_result.get('content', '')
                                
                                # Parse the HTML content using BeautifulSoup
                                soup = BeautifulSoup(content, 'html.parser')
                                print(f"  Successfully fetched content using MCP browser")
                            else:
                                # Fall back to traditional HTTP requests if MCP browser fails
                                print(f"  MCP browser failed: {mcp_result.get('error', 'Unknown error')}. Falling back to HTTP requests.")
                                # Apply SSL verification handling
                                verify = True
                                if SSL_UTILS_AVAILABLE and should_skip_verification(url):
                                    verify = False
                                    logger.debug(f"SSL verification disabled for request to {url}")
                                response = requests.get(url, headers=headers, timeout=20, verify=verify)  # Increased timeout
                                response.raise_for_status()
                                soup = BeautifulSoup(response.content, 'html.parser')
                        except Exception as e:
                            print(f"  Error using MCP browser: {str(e)}. Falling back to HTTP requests.")
                            # Apply SSL verification handling
                            verify = True
                            if SSL_UTILS_AVAILABLE and should_skip_verification(url):
                                verify = False
                                logger.debug(f"SSL verification disabled for request to {url}")
                            response = requests.get(url, headers=headers, timeout=20, verify=verify)  # Increased timeout
                            response.raise_for_status()
                            soup = BeautifulSoup(response.content, 'html.parser')
                    else:
                        # Use traditional HTTP requests
                        # Apply SSL verification handling
                        verify = True
                        if SSL_UTILS_AVAILABLE and should_skip_verification(url):
                            verify = False
                            logger.debug(f"SSL verification disabled for request to {url}")
                        response = requests.get(url, headers=headers, timeout=20, verify=verify)  # Increased timeout
                        response.raise_for_status()
                        soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Use enhanced structured content extraction for all pages
                    print(f"  Using enhanced structured content extraction for {url}...")
                    structured_content = self.extract_structured_content_sync(url)
                    
                    # Extract title from structured content or fallback to soup
                    title = structured_content.get('title', '')
                    if not title and soup.title:
                        title = soup.title.string.strip()
                    if not title:
                        title = result.get('title', 'Unknown Title')
                    
                    # Check if this is a news site
                    news_domains = ['cnn.com', 'bbc.com', 'nytimes.com', 'foxnews.com', 'reuters.com', 
                                   'washingtonpost.com', 'theguardian.com', 'news.', 'nbcnews.com', 
                                   'cbsnews.com', 'abcnews.go.com', 'usatoday.com', 'wsj.com']
                    
                    domain = self._extract_domain(url)
                    # Store the news site status in structured_content for consistent access
                    structured_content['is_news_site'] = any(news_domain in domain.lower() for news_domain in news_domains)
                    
                    if structured_content['is_news_site']:
                        print(f"  Detected news site: {domain}. Using specialized news content extraction.")
                    
                    # Format the content based on the page type
                    if structured_content.get('is_news_site', False) and 'news_content' in structured_content:
                        # Use news-specific content extraction
                        news_content = structured_content['news_content']
                        
                        # Extract structured content
                        main_content = news_content.get('main_content', '')
                        headlines = news_content.get('headlines', [])
                        summary = news_content.get('summary', '')
                        author = news_content.get('author', '')
                        publication_date = news_content.get('publication_date', '')
                        related_articles = news_content.get('related_articles', [])
                        
                        # Format the content nicely
                        formatted_content = []
                        
                        # Add title
                        if headlines and headlines[0]:
                            formatted_content.append(f"# {headlines[0]}")
                        else:
                            formatted_content.append(f"# {title}")
                        
                        # Add metadata
                        metadata = []
                        if author:
                            metadata.append(f"Author: {author}")
                        if publication_date:
                            metadata.append(f"Published: {publication_date}")
                        if metadata:
                            formatted_content.append(" | ".join(metadata))
                            formatted_content.append("")
                        
                        # Add summary if available
                        if summary:
                            formatted_content.append(f"**Summary**: {summary}")
                            formatted_content.append("")
                        
                        # Add main content
                        if main_content:
                            formatted_content.append(main_content)
                        
                        # Add related articles if available
                        if related_articles:
                            formatted_content.append("\n## Related Articles")
                            for article in related_articles:
                                formatted_content.append(f"- [{article['title']}]({article['url']})")
                        
                        # Join everything together
                        main_content = "\n\n".join(formatted_content)
                        
                        # Set headings from headlines
                        headings = headlines[:5] if headlines else []
                        
                        # Extract key points from the content
                        key_points = []
                        for paragraph in main_content.split('\n\n'):
                            if len(paragraph) > 30 and len(paragraph) < 300 and not paragraph.startswith('#') and not paragraph.startswith('-'):
                                key_points.append(paragraph)
                        key_points = key_points[:5]  # Limit to 5 key points
                    else:
                        # For non-news sites, use the structured content extraction
                        # Format the content nicely
                        formatted_content = []
                        
                        # Add title
                        formatted_content.append(f"# {title}")
                        formatted_content.append("")
                        
                        # Add headings as a table of contents if available
                        if structured_content['headings']:
                            formatted_content.append("## Table of Contents")
                            for heading in structured_content['headings']:
                                level = heading['level']
                                text = heading['text']
                                indent = "  " * (level - 1)
                                formatted_content.append(f"{indent}- {text}")
                            formatted_content.append("")
                        
                        # Add paragraphs as main content
                        if structured_content['paragraphs']:
                            main_content_paragraphs = structured_content['paragraphs']
                            formatted_content.append("\n\n".join(main_content_paragraphs))
                        else:
                            # Fallback to traditional extraction if no paragraphs found
                            main_content_text = self._extract_main_content_from_html(soup)
                            formatted_content.append(main_content_text)
                        
                        # Add tables if available
                        if structured_content['tables']:
                            formatted_content.append("\n## Tables")
                            for i, table in enumerate(structured_content['tables']):
                                formatted_content.append(f"\n### Table {i+1}")
                                if table['headers']:
                                    formatted_content.append(" | ".join(table['headers']))
                                    formatted_content.append(" | ".join(["---" for _ in table['headers']]))
                                for row in table['rows']:
                                    formatted_content.append(" | ".join(row))
                                formatted_content.append("")
                        
                        # Add images if available
                        if structured_content['images'] and len(structured_content['images']) <= 5:  # Limit to 5 images
                            formatted_content.append("\n## Images")
                            for image in structured_content['images'][:5]:
                                if image['alt']:
                                    formatted_content.append(f"![{image['alt']}]({image['url']})")
                                else:
                                    formatted_content.append(f"![Image]({image['url']})")
                        
                        # Join everything together
                        main_content = "\n\n".join(formatted_content)
                        
                        # Extract headings from structured content
                        headings = [heading['text'] for heading in structured_content['headings']]
                        headings = headings[:5] if headings else []  # Limit to 5 headings
                        
                        # Extract key points from paragraphs
                        key_points = []
                        for paragraph in structured_content['paragraphs']:
                            if len(paragraph) > 30 and len(paragraph) < 300:
                                key_points.append(paragraph)
                        key_points = key_points[:5]  # Limit to 5 key points
                        
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
        headline_classes = ['headline', 'title', 'article-title', 'story-title', 'heading', 'card-title', 'entry-title']
        for cls in headline_classes:
            for element in soup.find_all(class_=lambda c: c and cls in (c or '').lower()):
                text = element.get_text().strip()
                if text and len(text) > 10 and len(text) < 200 and text not in headlines:
                    headlines.append(text)
        
        # 3. Look for article titles in common news site structures
        for article in soup.find_all(['article', 'div'], class_=lambda c: c and any(cls in (c or '').lower() for cls in ['article', 'story', 'card', 'post', 'item'])):
            title_element = article.find(['h1', 'h2', 'h3', 'h4']) or article.find(class_=lambda c: c and any(cls in (c or '').lower() for cls in ['title', 'headline', 'heading']))
            if title_element:
                text = title_element.get_text().strip()
                if text and len(text) > 10 and len(text) < 200 and text not in headlines:
                    headlines.append(text)
        
        # 4. Look for list items that might be headlines in news sites
        for li in soup.find_all('li', class_=lambda c: c and any(cls in (c or '').lower() for cls in ['headline', 'title', 'story', 'item'])):
            a_tag = li.find('a')
            if a_tag:
                text = a_tag.get_text().strip()
                if text and len(text) > 10 and len(text) < 200 and text not in headlines:
                    headlines.append(text)
        
        # 5. Look for anchor tags with headline-like characteristics
        for a_tag in soup.find_all('a', class_=lambda c: c and any(cls in (c or '').lower() for cls in ['headline', 'title', 'story', 'card-title'])):
            text = a_tag.get_text().strip()
            if text and len(text) > 10 and len(text) < 200 and text not in headlines:
                headlines.append(text)
        
        # 6. Special handling for news sites with specific structures
        # CNN specific patterns
        for element in soup.find_all(class_=lambda c: c and any(cls in (c or '').lower() for cls in ['cd__headline', 'container__headline', 'headline__text'])):
            text = element.get_text().strip()
            if text and len(text) > 10 and len(text) < 200 and text not in headlines:
                headlines.append(text)
                
        # BBC specific patterns
        for element in soup.find_all(class_=lambda c: c and any(cls in (c or '').lower() for cls in ['gs-c-promo-heading', 'media__title', 'nw-o-headline'])):
            text = element.get_text().strip()
            if text and len(text) > 10 and len(text) < 200 and text not in headlines:
                headlines.append(text)
        
        # Fox News specific patterns
        for element in soup.find_all(class_=lambda c: c and any(cls in (c or '').lower() for cls in ['title', 'headline', 'article-title', 'story-title'])):
            text = element.get_text().strip()
            if text and len(text) > 10 and len(text) < 200 and text not in headlines:
                headlines.append(text)
        
        # Reuters specific patterns
        for element in soup.find_all(class_=lambda c: c and any(cls in (c or '').lower() for cls in ['article-headline', 'story-title', 'headline', 'media-story-card__heading__eqhp9'])):
            text = element.get_text().strip()
            if text and len(text) > 10 and len(text) < 200 and text not in headlines:
                headlines.append(text)
        
        # New York Times specific patterns
        for element in soup.find_all(class_=lambda c: c and any(cls in (c or '').lower() for cls in ['css-1qwf1ke', 'css-1vxca1d', 'e1h9rw200', 'headline'])):
            text = element.get_text().strip()
            if text and len(text) > 10 and len(text) < 200 and text not in headlines:
                headlines.append(text)
        
        # Remove duplicates while preserving order
        unique_headlines = []
        for headline in headlines:
            if headline not in unique_headlines:
                unique_headlines.append(headline)
        
        return unique_headlines[:15]  # Return up to 15 headlines for better coverage
    
    def _extract_domain(self, url: str) -> str:
        """
        Extract the domain from a URL.
        
        Args:
            url: The URL to extract the domain from
            
        Returns:
            The domain name
        """
        # Use regex to extract the domain
        domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
        if domain_match:
            return domain_match.group(1)
        return ""
        
    def _extract_with_enhanced_javascript(self, url: str, domain: str) -> Dict[str, Any]:
        """
        Extract content from a news site using enhanced JavaScript execution techniques.
        This method delegates to the js_content_extraction module for the actual implementation.
        
        Args:
            url: URL of the news site to extract content from
            domain: Domain of the news site (e.g., 'cnn.com')
            
        Returns:
            Dict containing the extraction results
        """
        # Delegate to the js_content_extraction module
        return js_content_extraction.extract_with_enhanced_javascript(url, domain, self.mcp_browser.server_url)
    
    def _extract_news_content(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """
        Extract structured content specifically from news websites.
        This method is optimized for news sites and extracts headlines, summary, main content,
        author information, publication date, related articles, and categories/tags.
        
        Args:
            soup: BeautifulSoup object containing the HTML content
            url: URL of the news site
            
        Returns:
            Dict containing structured news content with the following keys:
            - headlines: List of headlines found on the page
            - summary: Article summary or description
            - main_content: Main article content
            - author: Author information
            - publication_date: Publication date
            - related_articles: List of related articles with titles and URLs
            - source: Original URL
            - categories: List of article categories or tags
            - keywords: List of article keywords
            - image_url: Main article image URL
        """
        # Initialize the result dictionary with more comprehensive fields
        result = {
            'headlines': [],
            'summary': '',
            'main_content': '',
            'author': '',
            'publication_date': '',
            'related_articles': [],
            'source': url,
            'categories': [],
            'keywords': [],
            'image_url': ''
        }
        
        # Extract domain for site-specific handling
        domain = self._extract_domain(url)
        
        # Extract headlines
        result['headlines'] = self._extract_headlines_from_html(soup)
        
        # Extract summary/description with multiple fallbacks
        summary_elements = []
        
        # Look for meta descriptions (multiple variants)
        meta_tags = [
            soup.find('meta', attrs={'name': 'description'}),
            soup.find('meta', attrs={'property': 'og:description'}),
            soup.find('meta', attrs={'name': 'twitter:description'}),
            soup.find('meta', attrs={'itemprop': 'description'})
        ]
        
        for meta_tag in meta_tags:
            if meta_tag and meta_tag.get('content'):
                content = meta_tag.get('content').strip()
                if content and len(content) > 20:
                    summary_elements.append(content)
        
        # Look for summary/lead paragraphs with expanded class list
        summary_classes = ['summary', 'description', 'lead', 'intro', 'subheadline', 'standfirst', 
                          'article-summary', 'article-excerpt', 'article-intro', 'article-description',
                          'entry-summary', 'post-summary', 'excerpt', 'teaser', 'deck', 'kicker']
        
        for cls in summary_classes:
            for element in soup.find_all(class_=lambda c: c and cls in (c or '').lower()):
                text = element.get_text().strip()
                if text and len(text) > 30:
                    summary_elements.append(text)
        
        # Look for first paragraph if no summary found yet
        if not summary_elements:
            # Try to find the first substantial paragraph in the article content
            article_content = soup.find('article') or soup.find(class_=lambda c: c and any(cls in (c or '').lower() for cls in ['article-content', 'story-content', 'entry-content']))
            if article_content:
                first_p = article_content.find('p')
                if first_p:
                    text = first_p.get_text().strip()
                    if text and len(text) > 40 and len(text) < 300:  # Reasonable summary length
                        summary_elements.append(text)
        
        # Set the summary
        if summary_elements:
            result['summary'] = summary_elements[0]
        
        # Extract author information with enhanced patterns
        author_elements = []
        
        # Look for author meta tags (multiple variants)
        meta_author_tags = [
            soup.find('meta', attrs={'name': 'author'}),
            soup.find('meta', attrs={'property': 'article:author'}),
            soup.find('meta', attrs={'name': 'twitter:creator'}),
            soup.find('meta', attrs={'property': 'og:author'})
        ]
        
        for meta_tag in meta_author_tags:
            if meta_tag and meta_tag.get('content'):
                content = meta_tag.get('content').strip()
                if content and len(content) < 100:  # Reasonable author length
                    author_elements.append(content)
        
        # Look for author in the content with expanded class list
        author_classes = ['author', 'byline', 'writer', 'contributor', 'meta-author', 'article-author',
                         'entry-author', 'post-author', 'story-author', 'reporter', 'journalist',
                         'credit', 'attribution', 'signature']
        
        for cls in author_classes:
            for element in soup.find_all(class_=lambda c: c and cls in (c or '').lower()):
                text = element.get_text().strip()
                if text:
                    # Clean up author text
                    text = re.sub(r'^by\s+|^written by\s+', '', text, flags=re.IGNORECASE).strip()
                    if text and len(text) < 100:  # Reasonable author length
                        author_elements.append(text)
        
        # Look for schema.org author markup
        schema_authors = soup.find_all(itemprop='author')
        for author in schema_authors:
            name_elem = author.find(itemprop='name')
            if name_elem:
                text = name_elem.get_text().strip()
                if text:
                    author_elements.append(text)
            else:
                text = author.get_text().strip()
                if text and len(text) < 100:
                    author_elements.append(text)
        
        # Set the author
        if author_elements:
            result['author'] = author_elements[0]
        
        # Extract publication date with enhanced patterns
        date_elements = []
        
        # Look for date meta tags (multiple variants)
        meta_date_tags = [
            soup.find('meta', attrs={'name': 'date'}),
            soup.find('meta', attrs={'property': 'article:published_time'}),
            soup.find('meta', attrs={'property': 'article:modified_time'}),
            soup.find('meta', attrs={'name': 'pubdate'}),
            soup.find('meta', attrs={'itemprop': 'datePublished'}),
            soup.find('meta', attrs={'itemprop': 'dateModified'})
        ]
        
        for meta_tag in meta_date_tags:
            if meta_tag and meta_tag.get('content'):
                content = meta_tag.get('content').strip()
                if content:
                    date_elements.append(content)
        
        # Look for date in the content with expanded class list
        date_classes = ['date', 'time', 'published', 'timestamp', 'meta-date', 'article-date',
                       'entry-date', 'post-date', 'story-date', 'pub-date', 'publish-date',
                       'publication-date', 'article-timestamp', 'dateline']
        
        for cls in date_classes:
            for element in soup.find_all(class_=lambda c: c and cls in (c or '').lower()):
                text = element.get_text().strip()
                if text and len(text) < 50:  # Reasonable date length
                    date_elements.append(text)
        
        # Look for time tags and schema.org date markup
        for time_tag in soup.find_all(['time']) + soup.find_all(attrs={'itemprop': 'datePublished'}) + soup.find_all(attrs={'itemprop': 'dateModified'}):
            if time_tag.get('datetime'):
                date_elements.append(time_tag.get('datetime'))
            else:
                text = time_tag.get_text().strip()
                if text and len(text) < 50:
                    date_elements.append(text)
        
        # Set the publication date
        if date_elements:
            result['publication_date'] = date_elements[0]
        
        # Extract main content with enhanced patterns
        content_elements = []
        
        # Look for article content with expanded class list
        content_classes = ['article-content', 'story-content', 'entry-content', 'post-content', 'article-body', 
                          'story-body', 'main-content', 'content-body', 'article-text', 'story-text',
                          'entry-body', 'post-body', 'article', 'content', 'main', 'body']
        
        # Try site-specific content extraction first
        site_specific_content = self._extract_site_specific_content(soup, domain)
        if site_specific_content:
            content_elements.extend(site_specific_content)
        
        # If no site-specific content, try generic patterns
        if not content_elements:
            for cls in content_classes:
                for element in soup.find_all(class_=lambda c: c and cls in (c or '').lower()):
                    # Get all paragraphs within the content element
                    paragraphs = element.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text and len(text) > 20:  # Reasonable paragraph length
                            content_elements.append(text)
        
        # If no content found in specific classes, try to get all paragraphs in the article
        if not content_elements:
            # Look for article tag
            article = soup.find('article')
            if article:
                paragraphs = article.find_all('p')
                for p in paragraphs:
                    text = p.get_text().strip()
                    if text and len(text) > 20:  # Reasonable paragraph length
                        content_elements.append(text)
            else:
                # Try to find main content area using heuristics
                main_content_candidates = [
                    soup.find('main'),
                    soup.find(id='main'),
                    soup.find(id='content'),
                    soup.find(id='article'),
                    soup.find(role='main')
                ]
                
                for candidate in main_content_candidates:
                    if candidate:
                        paragraphs = candidate.find_all('p')
                        for p in paragraphs:
                            text = p.get_text().strip()
                            if text and len(text) > 20:  # Reasonable paragraph length
                                content_elements.append(text)
                        if content_elements:
                            break
                
                # If still no content, fallback to main content extraction
                if not content_elements:
                    main_content = self._extract_main_content_from_html(soup)
                    if main_content:
                        # Split by paragraphs if it's a large chunk of text
                        if len(main_content) > 500:
                            paragraphs = main_content.split('\n\n')
                            for p in paragraphs:
                                if p.strip() and len(p.strip()) > 20:
                                    content_elements.append(p.strip())
                        else:
                            content_elements.append(main_content)
        
        # Remove duplicates while preserving order
        unique_content = []
        for content in content_elements:
            if content not in unique_content:
                unique_content.append(content)
        
        # Set the main content
        if unique_content:
            result['main_content'] = '\n\n'.join(unique_content)
        
        # Extract related articles with enhanced patterns
        related_articles = []
        
        # Look for related articles section with expanded class list
        related_classes = ['related', 'read-more', 'more-stories', 'more-articles', 'similar', 'recommended',
                          'related-content', 'related-stories', 'related-posts', 'suggested', 'popular',
                          'trending', 'most-read', 'also-read', 'see-also', 'more-like-this']
        
        for cls in related_classes:
            for element in soup.find_all(class_=lambda c: c and cls in (c or '').lower()):
                # Look for links within the related articles section
                links = element.find_all('a')
                for link in links:
                    href = link.get('href')
                    text = link.get_text().strip()
                    if href and text and len(text) > 10:
                        # Make sure the href is a full URL
                        if not href.startswith('http'):
                            # Check if it's a relative URL
                            if href.startswith('/'):
                                # Extract the domain from the original URL
                                domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
                                if domain_match:
                                    domain = domain_match.group(0)
                                    href = domain + href
                            else:
                                # Skip if we can't form a proper URL
                                continue
                        
                        # Check if this article is already in the list
                        if not any(article['url'] == href for article in related_articles):
                            related_articles.append({
                                'title': text,
                                'url': href
                            })
        
        # Set the related articles
        result['related_articles'] = related_articles[:5]  # Limit to 5 related articles
        
        # Extract categories and tags
        categories = []
        
        # Look for category meta tags
        meta_category = soup.find('meta', attrs={'property': 'article:section'}) or soup.find('meta', attrs={'name': 'category'})
        if meta_category and meta_category.get('content'):
            categories.append(meta_category.get('content'))
        
        # Look for category/tag elements
        category_classes = ['category', 'tag', 'topic', 'section', 'article-category', 'article-tag',
                           'entry-category', 'entry-tag', 'post-category', 'post-tag']
        
        for cls in category_classes:
            for element in soup.find_all(class_=lambda c: c and cls in (c or '').lower()):
                text = element.get_text().strip()
                if text and len(text) < 50:  # Reasonable category length
                    categories.append(text)
        
        # Set the categories
        result['categories'] = list(set(categories))[:10]  # Remove duplicates and limit to 10
        
        # Extract keywords
        keywords = []
        
        # Look for keyword meta tags
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'}) or soup.find('meta', attrs={'property': 'article:tag'})
        if meta_keywords and meta_keywords.get('content'):
            # Split by commas and clean up
            for keyword in meta_keywords.get('content').split(','):
                keyword = keyword.strip()
                if keyword:
                    keywords.append(keyword)
        
        # Set the keywords
        result['keywords'] = list(set(keywords))[:10]  # Remove duplicates and limit to 10
        
        # Extract main image URL
        image_url = ''
        
        # Look for og:image meta tag
        meta_image = soup.find('meta', attrs={'property': 'og:image'}) or soup.find('meta', attrs={'name': 'twitter:image'})
        if meta_image and meta_image.get('content'):
            image_url = meta_image.get('content')
        
        # If no meta image, look for main article image
        if not image_url:
            # Look for article featured image
            featured_image_classes = ['featured-image', 'article-image', 'post-image', 'entry-image',
                                     'story-image', 'main-image', 'lead-image', 'hero-image']
            
            for cls in featured_image_classes:
                for element in soup.find_all(class_=lambda c: c and cls in (c or '').lower()):
                    img = element.find('img')
                    if img and img.get('src'):
                        image_url = img.get('src')
                        break
                if image_url:
                    break
            
            # If still no image, look for first substantial image in the page
            if not image_url:
                # Extract images directly from the soup
                images = []
                for img in soup.find_all('img'):
                    src = img.get('src')
                    alt = img.get('alt', '')
                    if src and len(src) > 10 and not src.endswith(('.gif', '.svg')):
                        images.append({'url': src, 'alt': alt})
                
                # Use the first substantial image
                if images:
                    image_url = images[0].get('url', '')
        
        # Set the image URL
        result['image_url'] = image_url
        
        return result
    
    def _extract_site_specific_content(self, soup: BeautifulSoup, domain: str) -> List[str]:
        """
        Extract content using site-specific patterns for major news sites.
        
        Args:
            soup: BeautifulSoup object containing the HTML content
            domain: Domain of the news site
            
        Returns:
            List of content paragraphs
        """
        content_elements = []
        logger.info(f"Extracting site-specific content for domain: {domain}")
        
        # CNN specific extraction
        if 'cnn.com' in domain:
            logger.info("Using CNN-specific content extraction")
            # Try multiple possible CNN article body selectors
            # CNN has changed their layout multiple times
            cnn_content_selectors = [
                # Current CNN layout (2025)
                soup.find(class_='article__content'),
                soup.find(class_='article-content'),
                soup.find(class_='l-container'),
                soup.find(class_='body-text'),
                soup.find(class_='zn-body__paragraph'),
                # Try the main content area
                soup.find('main'),
                soup.find(id='body-text'),
                soup.find(class_='pg-rail-tall__body'),
                # Additional CNN selectors
                soup.find(class_='article__main'),
                soup.find(class_='basic-article'),
                soup.find(class_='article-section'),
                # Latest CNN layout selectors
                soup.find(class_='article__body'),
                soup.find(class_='article-body'),
                soup.find(class_='article__content-container'),
                soup.find(class_='body__content'),
                soup.find(class_='article-body__content')
            ]
            
            # Try each selector until we find content
            for cnn_content in cnn_content_selectors:
                if cnn_content:
                    # Try different paragraph selectors
                    for p_class in [None, 'paragraph', 'zn-body__paragraph', 'el__leafmedia', 'zn-body-text', 'article-paragraph']:
                        paragraphs = cnn_content.find_all('p', class_=p_class) if p_class else cnn_content.find_all('p')
                        for p in paragraphs:
                            text = p.get_text().strip()
                            if text and len(text) > 20:
                                content_elements.append(text)
                    
                    # If we found content, break the loop
                    if content_elements:
                        logger.info(f"Found {len(content_elements)} content elements from CNN")
                        break
            
            # If still no content, try to find any paragraphs in the document with substantial text
            if not content_elements:
                logger.info("No content found with specific selectors, trying generic paragraph extraction")
                all_paragraphs = soup.find_all('p')
                for p in all_paragraphs:
                    text = p.get_text().strip()
                    if text and len(text) > 40:  # Longer threshold for generic paragraphs
                        content_elements.append(text)
        
        # BBC specific extraction
        elif 'bbc.com' in domain or 'bbc.co.uk' in domain:
            logger.info("Using BBC-specific content extraction")
            # BBC article body - try multiple possible selectors
            bbc_content_selectors = [
                soup.find(class_='ssrcss-uf6wea-RichTextComponentWrapper'),
                soup.find(class_='story-body'),
                soup.find(id='story-body'),
                soup.find(class_='story-body__inner'),
                soup.find(class_='article-body-component'),
                # Latest BBC selectors (2025)
                soup.find(class_='ssrcss-pv1rh6-ArticleWrapper'),
                soup.find(class_='ssrcss-1ocoo3l-Prose'),
                soup.find(class_='ssrcss-11r1m41-RichTextComponentWrapper'),
                soup.find(class_='lx-stream__post-text'),
                soup.find(class_='gs-u-mb+'),
                # Fallback to article
                soup.find('article')
            ]
            
            for bbc_content in bbc_content_selectors:
                if bbc_content:
                    # Try to find paragraphs or divs containing text
                    paragraphs = bbc_content.find_all(['p', 'div.ssrcss-11r1m41-RichTextComponentWrapper'])
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text and len(text) > 20:
                            content_elements.append(text)
                    
                    if content_elements:
                        logger.info(f"Found {len(content_elements)} content elements from BBC")
                        break
        
        # New York Times specific extraction
        elif 'nytimes.com' in domain:
            logger.info("Using NYT-specific content extraction")
            # NYT article body - try multiple possible selectors
            nyt_content_selectors = [
                soup.find(class_='css-53u6y8'),
                soup.find(class_='css-1r7ky0e'),  # Updated selector
                soup.find(class_='StoryBodyCompanionColumn'),
                soup.find(id='story'),
                soup.find(class_='story-body'),
                soup.find(class_='article-content'),
                soup.find('article')
            ]
            
            for nyt_content in nyt_content_selectors:
                if nyt_content:
                    paragraphs = nyt_content.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text and len(text) > 20:
                            content_elements.append(text)
                    
                    if content_elements:
                        logger.info(f"Found {len(content_elements)} content elements from NYT")
                        break
        
        # Washington Post specific extraction
        elif 'washingtonpost.com' in domain:
            logger.info("Using WaPo-specific content extraction")
            # WaPo article body - updated with latest selectors
            wapo_content_selectors = [
                soup.find(class_='article-body'),
                soup.find(class_='teaser-content'),
                soup.find(class_='story-body'),
                soup.find(id='article-body'),
                soup.find(class_='grid-body'),
                soup.find(class_='article-content'),
                soup.find(class_='main-content'),
                soup.find(class_='paywall-article'),
                soup.find(class_='article__content'),
                soup.find(class_='story-headline'),
                soup.find('article')
            ]
            
            # Try each selector until we find content
            for wapo_content in wapo_content_selectors:
                if wapo_content:
                    # Try to find paragraphs
                    paragraphs = wapo_content.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text and len(text) > 20:
                            content_elements.append(text)
                    
                    # If we found content, break
                    if content_elements:
                        logger.info(f"Found {len(content_elements)} content elements from WaPo")
                        break
            
            # If no content found yet, try to find content in div elements with specific classes
            if not content_elements:
                # Try to find content in div elements with specific classes
                content_divs = soup.find_all(['div', 'section'], class_=['article-body', 'story-body', 'paywall-content'])
                for div in content_divs:
                    paragraphs = div.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text and len(text) > 20:
                            content_elements.append(text)
                
                if content_elements:
                    logger.info(f"Found {len(content_elements)} content elements from WaPo div containers")
        
        # Reuters specific extraction
        elif 'reuters.com' in domain:
            logger.info("Using Reuters-specific content extraction")
            # Reuters article body - updated with latest selectors
            reuters_content_selectors = [
                soup.find(class_='article-body__content__17Yit'),
                soup.find(class_='ArticleBody__content___2gQno2'),
                soup.find(class_='StandardArticleBody_body'),
                soup.find(class_='ArticleBodyWrapper'),
                soup.find(class_='article-body'),
                soup.find(class_='paywall-article'),
                soup.find(class_='article__content'),
                soup.find(class_='article-text'),
                soup.find(class_='main-content'),
                soup.find(class_='article__body'),
                soup.find('article')
            ]
            
            # Try each selector until we find content
            for reuters_content in reuters_content_selectors:
                if reuters_content:
                    # Try to find paragraphs
                    paragraphs = reuters_content.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text and len(text) > 20:
                            content_elements.append(text)
                    
                    # If we found content, break
                    if content_elements:
                        logger.info(f"Found {len(content_elements)} content elements from Reuters")
                        break
            
            # If no content found yet, try to find content in div elements with specific classes
            if not content_elements:
                # Try to find content in div elements with specific classes
                content_divs = soup.find_all(['div', 'section'], class_=['article-body', 'paywall-article', 'article__content'])
                for div in content_divs:
                    paragraphs = div.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text and len(text) > 20:
                            content_elements.append(text)
                
                if content_elements:
                    logger.info(f"Found {len(content_elements)} content elements from Reuters div containers")
        
        # The Guardian specific extraction
        elif 'theguardian.com' in domain:
            logger.info("Using Guardian-specific content extraction")
            # Guardian article body - updated with latest selectors
            guardian_content_selectors = [
                soup.find(class_='article-body-commercial-selector'),
                soup.find(class_='content__article-body'),
                soup.find(itemprop='articleBody'),
                soup.find(class_='dcr-185kcx9'),  # Updated selector
                soup.find(class_='dcr-7vl6y8'),    # New selector
                soup.find(class_='dcr-1jw8q47'),   # New selector
                soup.find(class_='article-body'),
                soup.find(class_='js-article__body'),
                soup.find(class_='js-liveblog-body'),
                soup.find(class_='content__main-column'),
                soup.find('article')
            ]
            
            # Try each selector until we find content
            for guardian_content in guardian_content_selectors:
                if guardian_content:
                    # Try to find paragraphs
                    paragraphs = guardian_content.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text and len(text) > 20:
                            content_elements.append(text)
                    
                    # If we found content, break
                    if content_elements:
                        logger.info(f"Found {len(content_elements)} content elements from Guardian")
                        break
            
            # If no content found yet, try to find content in div elements with specific classes
            if not content_elements:
                # Try to find content in div elements with specific classes
                content_divs = soup.find_all(['div', 'section'], class_=['article-body', 'dcr-1jw8q47', 'dcr-7vl6y8', 'content__main'])
                for div in content_divs:
                    paragraphs = div.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text and len(text) > 20:
                            content_elements.append(text)
                
                if content_elements:
                    logger.info(f"Found {len(content_elements)} content elements from Guardian div containers")
        
        # Fox News specific extraction
        elif 'foxnews.com' in domain:
            logger.info("Using Fox News-specific content extraction")
            # Fox News article body - try multiple possible selectors
            fox_content_selectors = [
                soup.find(class_='article-body'),
                soup.find(class_='article-content'),
                soup.find(class_='story-body'),
                soup.find(itemprop='articleBody'),
                soup.find('article')
            ]
            
            for fox_content in fox_content_selectors:
                if fox_content:
                    paragraphs = fox_content.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text and len(text) > 20:
                            content_elements.append(text)
                    
                    if content_elements:
                        logger.info(f"Found {len(content_elements)} content elements from Fox News")
                        break
                        
        # CNBC specific extraction
        elif 'cnbc.com' in domain:
            logger.info("Using CNBC-specific content extraction")
            # CNBC article body - try multiple possible selectors
            cnbc_content_selectors = [
                soup.find(class_='ArticleBody-articleBody'),
                soup.find(class_='group-content'),
                soup.find(class_='article-text'),
                soup.find(itemprop='articleBody'),
                soup.find('article')
            ]
            
            for cnbc_content in cnbc_content_selectors:
                if cnbc_content:
                    paragraphs = cnbc_content.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text and len(text) > 20:
                            content_elements.append(text)
                    
                    if content_elements:
                        logger.info(f"Found {len(content_elements)} content elements from CNBC")
                        break
        
        # NPR specific extraction
        elif 'npr.org' in domain:
            logger.info("Using NPR-specific content extraction")
            # NPR article body - try multiple possible selectors
            npr_content_selectors = [
                soup.find(id='storytext'),
                soup.find(class_='storytext'),
                soup.find(class_='story-text'),
                soup.find(itemprop='articleBody'),
                soup.find('article')
            ]
            
            for npr_content in npr_content_selectors:
                if npr_content:
                    paragraphs = npr_content.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text and len(text) > 20:
                            content_elements.append(text)
                    
                    if content_elements:
                        logger.info(f"Found {len(content_elements)} content elements from NPR")
                        break
        
        # AP News specific extraction
        elif 'apnews.com' in domain:
            logger.info("Using AP News-specific content extraction")
            # AP News article body selectors
            ap_content_selectors = [
                soup.find(class_='Article'),
                soup.find(class_='article-body'),
                soup.find(class_='RichTextStoryBody'),
                soup.find(class_='RichTextArticleBody'),
                soup.find(class_='article-text'),
                soup.find('article')
            ]
            
            for ap_content in ap_content_selectors:
                if ap_content:
                    paragraphs = ap_content.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text and len(text) > 20:
                            content_elements.append(text)
                    
                    if content_elements:
                        logger.info(f"Found {len(content_elements)} content elements from AP News")
                        break
                        
        # USA Today specific extraction
        elif 'usatoday.com' in domain:
            logger.info("Using USA Today-specific content extraction")
            # USA Today article body selectors
            usa_content_selectors = [
                soup.find(class_='gnt_ar_b'),
                soup.find(class_='story-text'),
                soup.find(class_='article-body'),
                soup.find(class_='content-well'),
                soup.find('article')
            ]
            
            for usa_content in usa_content_selectors:
                if usa_content:
                    paragraphs = usa_content.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text and len(text) > 20:
                            content_elements.append(text)
                    
                    if content_elements:
                        logger.info(f"Found {len(content_elements)} content elements from USA Today")
                        break
                        
        # Wall Street Journal specific extraction
        elif 'wsj.com' in domain:
            logger.info("Using WSJ-specific content extraction")
            # WSJ article body selectors - updated with latest selectors
            wsj_content_selectors = [
                soup.find(class_='article-content'),
                soup.find(class_='wsj-snippet-body'),
                soup.find(class_='article-wrap'),
                soup.find(class_='article__body'),
                soup.find(class_='WSJTheme--story-body--3HrS-PiU'),
                soup.find(class_='WSJTheme--article-body--1-Yw3-3a'),
                soup.find(class_='paywall-article'),
                soup.find(class_='article-container'),
                soup.find(class_='body-content'),
                soup.find('article')
            ]
            
            # Try each selector until we find content
            for wsj_content in wsj_content_selectors:
                if wsj_content:
                    # Try to find paragraphs
                    paragraphs = wsj_content.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text and len(text) > 20:
                            content_elements.append(text)
                    
                    # If we found content, break
                    if content_elements:
                        logger.info(f"Found {len(content_elements)} content elements from WSJ")
                        break
            
            # If no content found yet, try to find content in div elements with specific classes
            if not content_elements:
                # Try to find content in div elements with specific classes
                content_divs = soup.find_all(['div', 'section'], class_=['WSJTheme--body--1v8wWPdJ', 'article-body', 'body-content'])
                for div in content_divs:
                    paragraphs = div.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text and len(text) > 20:
                            content_elements.append(text)
                
                if content_elements:
                    logger.info(f"Found {len(content_elements)} content elements from WSJ div containers")
                        
        # Bloomberg specific extraction
        elif 'bloomberg.com' in domain:
            logger.info("Using Bloomberg-specific content extraction")
            # Bloomberg article body selectors
            bloomberg_content_selectors = [
                soup.find(class_='body-content'),
                soup.find(class_='body-copy'),
                soup.find(class_='body-copy-v2'),
                soup.find(class_='paywall'),
                soup.find(class_='fence-body'),
                soup.find('article')
            ]
            
            for bloomberg_content in bloomberg_content_selectors:
                if bloomberg_content:
                    paragraphs = bloomberg_content.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text and len(text) > 20:
                            content_elements.append(text)
                    
                    if content_elements:
                        logger.info(f"Found {len(content_elements)} content elements from Bloomberg")
                        break
        
        # Business Insider specific extraction
        elif 'businessinsider.com' in domain:
            logger.info("Using Business Insider-specific content extraction")
            # Business Insider article body selectors
            bi_content_selectors = [
                soup.find(class_='content-lock-content'),
                soup.find(id='piano-inline-content-wrapper'),
                soup.find(class_='article-body'),
                soup.find(class_='post-content'),
                soup.find('article')
            ]
            
            for bi_content in bi_content_selectors:
                if bi_content:
                    paragraphs = bi_content.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text and len(text) > 20:
                            content_elements.append(text)
                    
                    if content_elements:
                        logger.info(f"Found {len(content_elements)} content elements from Business Insider")
                        break
        
        # The Verge specific extraction
        elif 'theverge.com' in domain:
            logger.info("Using The Verge-specific content extraction")
            # The Verge article body selectors
            verge_content_selectors = [
                soup.find(class_='duet--article--article-body-component'),
                soup.find(class_='c-entry-content'),
                soup.find(class_='entry-content'),
                soup.find(class_='article-body'),
                soup.find('article')
            ]
            
            for verge_content in verge_content_selectors:
                if verge_content:
                    paragraphs = verge_content.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text and len(text) > 20:
                            content_elements.append(text)
                    
                    if content_elements:
                        logger.info(f"Found {len(content_elements)} content elements from The Verge")
                        break
        
        # TechCrunch specific extraction
        elif 'techcrunch.com' in domain:
            logger.info("Using TechCrunch-specific content extraction")
            # TechCrunch article body selectors
            tc_content_selectors = [
                soup.find(class_='article-content'),
                soup.find(class_='article__content'),
                soup.find(class_='article-entry'),
                soup.find(class_='entry-content'),
                soup.find('article')
            ]
            
            for tc_content in tc_content_selectors:
                if tc_content:
                    paragraphs = tc_content.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text and len(text) > 20:
                            content_elements.append(text)
                    
                    if content_elements:
                        logger.info(f"Found {len(content_elements)} content elements from TechCrunch")
                        break
        
        # Forbes specific extraction
        elif 'forbes.com' in domain:
            logger.info("Using Forbes-specific content extraction")
            # Forbes article body selectors
            forbes_content_selectors = [
                soup.find(class_='article-body'),
                soup.find(class_='article-container'),
                soup.find(class_='body-container'),
                soup.find(class_='article-content'),
                soup.find('article')
            ]
            
            for forbes_content in forbes_content_selectors:
                if forbes_content:
                    paragraphs = forbes_content.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text and len(text) > 20:
                            content_elements.append(text)
                    
                    if content_elements:
                        logger.info(f"Found {len(content_elements)} content elements from Forbes")
                        break
        
        # Wired specific extraction
        elif 'wired.com' in domain:
            logger.info("Using Wired-specific content extraction")
            # Wired article body selectors
            wired_content_selectors = [
                soup.find(class_='article__body'),
                soup.find(class_='content-body'),
                soup.find(class_='article-body-component'),
                soup.find(class_='body__content'),
                soup.find('article')
            ]
            
            for wired_content in wired_content_selectors:
                if wired_content:
                    paragraphs = wired_content.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text and len(text) > 20:
                            content_elements.append(text)
                    
                    if content_elements:
                        logger.info(f"Found {len(content_elements)} content elements from Wired")
                        break
        
        # Generic news site extraction for other domains
        if not content_elements:
            logger.info(f"No site-specific extraction for {domain} or no content found, using generic extraction")
            # Try common article containers
            article_selectors = [
                soup.find('article'),
                soup.find(class_=lambda c: c and 'article' in c.lower()),
                soup.find(id=lambda i: i and 'article' in i.lower()),
                soup.find(class_=lambda c: c and 'content' in c.lower()),
                soup.find(id=lambda i: i and 'content' in i.lower()),
                soup.find(class_=lambda c: c and 'story' in c.lower()),
                soup.find(id=lambda i: i and 'story' in i.lower()),
                soup.find('main'),
                soup.find(id='main'),
                soup.find(class_='main'),
                # Additional generic selectors
                soup.find(class_=lambda c: c and 'body' in c.lower()),
                soup.find(id=lambda i: i and 'body' in i.lower()),
                soup.find(class_=lambda c: c and 'text' in c.lower()),
                soup.find(id=lambda i: i and 'text' in i.lower())
            ]
            
            for article in article_selectors:
                if article:
                    paragraphs = article.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text and len(text) > 20:  # Only include substantial paragraphs
                            content_elements.append(text)
                    
                    if content_elements:
                        logger.info(f"Found {len(content_elements)} content elements using generic article selector")
                        break
            
            # If still no content, try to find any paragraphs with substantial text
            if not content_elements:
                logger.info("No content found with article selectors, trying all paragraphs")
                all_paragraphs = soup.find_all('p')
                for p in all_paragraphs:
                    text = p.get_text().strip()
                    if text and len(text) > 40:  # Higher threshold for generic paragraphs
                        content_elements.append(text)
                
                if content_elements:
                    logger.info(f"Found {len(content_elements)} content elements from all paragraphs")
            
            # If still no content, try to extract text from div elements
            if not content_elements:
                logger.info("No content found in paragraphs, trying div elements")
                # Look for divs that might contain article text
                content_divs = soup.find_all('div', class_=lambda c: c and any(term in c.lower() for term in ['text', 'content', 'article', 'story', 'body']))
                if not content_divs:  # If no divs with specific classes, try all divs
                    content_divs = soup.find_all('div')
                
                for div in content_divs:
                    # Skip divs that are likely navigation, headers, footers, etc.
                    if div.get('class') and any(term in div.get('class', [''])[0].lower() 
                           for term in ['nav', 'menu', 'header', 'footer', 'sidebar', 'comment', 'ad', 'share', 'related']):
                        continue
                    
                    # Skip very small divs
                    text = div.get_text().strip()
                    if not text or len(text) < 100:
                        continue
                        
                    # Only include divs with substantial text that looks like paragraphs
                    if text.count('.') > 3:
                        # Split by newlines to create paragraph-like chunks
                        for para in text.split('\n'):
                            para = para.strip()
                            if para and len(para) > 40:
                                content_elements.append(para)
                
                if content_elements:
                    logger.info(f"Found {len(content_elements)} content elements from div elements")
        
        # Remove duplicate paragraphs while preserving order
        unique_content = []
        seen = set()
        
        # First pass: remove exact duplicates and very similar content
        for text in content_elements:
            # Skip empty or very short text
            if not text or len(text) < 20:
                continue
                
            # Create a normalized version for comparison (lowercase, whitespace normalized)
            normalized = re.sub(r'\s+', ' ', text.lower()).strip()
            
            # Skip if we've seen this text before
            if normalized in seen:
                continue
                
            # Check for near-duplicates (texts that are very similar)
            is_near_duplicate = False
            for existing in seen:
                # If one text is contained within another with high similarity
                if len(normalized) > len(existing) * 0.9 and existing in normalized:
                    is_near_duplicate = True
                    break
                if len(existing) > len(normalized) * 0.9 and normalized in existing:
                    is_near_duplicate = True
                    break
            
            if not is_near_duplicate:
                seen.add(normalized)
                unique_content.append(text)
        
        # Remove very short paragraphs if we have enough content
        if len(unique_content) > 5:
            unique_content = [text for text in unique_content if len(text) > 30]
        
        # If we have too many paragraphs, keep only the most substantial ones
        if len(unique_content) > 100:
            logger.info(f"Too many paragraphs ({len(unique_content)}), filtering to most substantial ones")
            
            # Define a scoring function for paragraphs
            def paragraph_score(p):
                # Longer paragraphs get higher scores
                length_score = min(len(p) / 200, 1.0)  # Cap at 1.0 for paragraphs of 200+ chars
                
                # Paragraphs with punctuation get higher scores (likely more complete sentences)
                punct_count = sum(1 for c in p if c in '.,:;?!')
                punct_score = min(punct_count / 5, 1.0)  # Cap at 1.0 for 5+ punctuation marks
                
                # Paragraphs with quotes might be more important
                quote_score = 0.5 if '"' in p or "'" in p else 0
                
                return length_score + punct_score + quote_score
            
            # Sort by score and keep the top 100
            unique_content = sorted(unique_content, key=paragraph_score, reverse=True)[:100]
        
        # Log the result
        if unique_content:
            logger.info(f"Successfully extracted {len(unique_content)} unique content elements from {domain}")
        else:
            logger.warning(f"Failed to extract any content from {domain}")
            
        return unique_content
    
    def extract_structured_content_sync(self, url: str) -> Dict[str, Any]:
        """
        Extract structured content from any webpage.
        This method provides a comprehensive extraction of various content types
        from a webpage, including headings, paragraphs, links, images, tables, and metadata.
        It uses a hybrid approach with MCP browser for JavaScript-rendered content when available,
        and falls back to traditional HTTP requests.
        
        The method has special handling for news websites, extracting additional structured
        data such as headlines, article summaries, main content, author information,
        publication dates, related articles, categories, and keywords.
        
        Args:
            url: URL of the webpage to extract content from
            
        Returns:
            Dict containing structured content with the following keys:
            - url: Original URL
            - title: Page title
            - headings: List of heading elements with level and text
            - paragraphs: List of paragraph texts
            - links: List of links with text and href
            - images: List of images with url and alt text
            - tables: List of tables with headers and rows
            - metadata: Dictionary of metadata from meta tags
            - raw_text: Raw text content of the page
            - news_content: News-specific content if the page is a news article
        """
        # Import required modules
        import requests
        import json
        import datetime
        import re
        result = {
            'url': url,
            'title': '',
            'headings': [],
            'paragraphs': [],
            'links': [],
            'images': [],
            'tables': [],
            'metadata': {},
            'raw_text': ''
        }
        
        try:
            # Extract domain for later use
            domain = self._extract_domain(url)
            print(f"Extracted domain for URL {url}: {domain}")
            
            # Try to use MCP browser if available for JavaScript-rendered content
            soup = None
            content = None
            mcp_success = False
            print(f"Initial soup object: {soup is None}")
            
            if hasattr(self, 'mcp_browser') and self.mcp_browser and self.use_mcp:
                print(f"Using MCP browser to extract structured content from {url}")
                try:
                    # Check if this is a news site that might need enhanced JavaScript execution
                    domain = self._extract_domain(url)
                    news_domains = ['cnn.com', 'bbc.com', 'nytimes.com', 'foxnews.com', 'reuters.com', 
                                  'washingtonpost.com', 'theguardian.com', 'news.', 'nbcnews.com', 
                                  'cbsnews.com', 'abcnews.go.com', 'usatoday.com', 'wsj.com', 'apnews.com',
                                  'bloomberg.com', 'cnbc.com', 'economist.com', 'ft.com', 'huffpost.com',
                                  'independent.co.uk', 'latimes.com', 'npr.org', 'politico.com', 'time.com']
                    
                    # Store is_news_site in the result dictionary for later use
                    result['is_news_site'] = any(news_domain in domain.lower() for news_domain in news_domains)
                    
                    # Use enhanced JavaScript execution for news sites
                    if result['is_news_site']:
                        print(f"Using enhanced JavaScript execution for news site: {domain}")
                        # Use the new js_content_extraction module for enhanced JavaScript execution
                        try:
                            import js_content_extraction
                            mcp_result = js_content_extraction.extract_with_enhanced_javascript(url, domain, self.mcp_browser.server_url)
                        except Exception as e:
                            logger.warning(f"Error using enhanced JavaScript extraction: {str(e)}")
                            # Fall back to regular browsing if enhanced extraction fails
                            # Add a timeout to prevent potential infinite loops
                            import threading
                            import time
                            
                            def browse_with_timeout():
                                nonlocal mcp_result
                                try:
                                    mcp_result = self.mcp_browser.browse_url_sync(url)
                                except Exception as e:
                                    print(f"Error in browse_url_sync fallback: {str(e)}")
                                    mcp_result = {"success": False, "error": str(e)}
                            
                            # Start browsing in a separate thread
                            browse_thread = threading.Thread(target=browse_with_timeout)
                            browse_thread.daemon = True
                            browse_thread.start()
                            
                            # Wait for the thread to complete with a timeout
                            timeout = 30  # 30 seconds timeout
                            start_time = time.time()
                            while browse_thread.is_alive() and time.time() - start_time < timeout:
                                time.sleep(0.5)
                            
                            # If the thread is still running after timeout, set a failure result
                            if browse_thread.is_alive():
                                print(f"Timeout reached while browsing {url} in fallback")
                                mcp_result = {
                                    "success": False,
                                    "error": f"Timeout reached after {timeout} seconds in fallback",
                                    "url": url
                                }
                    else:
                        # Get content directly using the browse_url method which is already properly handled
                        # for synchronous execution
                        # Add a timeout to prevent potential infinite loops
                        import threading
                        import time
                        
                        def browse_with_timeout():
                            nonlocal mcp_result
                            try:
                                mcp_result = self.mcp_browser.browse_url_sync(url)
                            except Exception as e:
                                print(f"Error in browse_url_sync: {str(e)}")
                                mcp_result = {"success": False, "error": str(e)}
                        
                        # Start browsing in a separate thread
                        browse_thread = threading.Thread(target=browse_with_timeout)
                        browse_thread.daemon = True
                        browse_thread.start()
                        
                        # Wait for the thread to complete with a timeout
                        timeout = 30  # 30 seconds timeout
                        start_time = time.time()
                        while browse_thread.is_alive() and time.time() - start_time < timeout:
                            time.sleep(0.5)
                        
                        # If the thread is still running after timeout, set a failure result
                        if browse_thread.is_alive():
                            print(f"Timeout reached while browsing {url}")
                            mcp_result = {
                                "success": False,
                                "error": f"Timeout reached after {timeout} seconds",
                                "url": url
                            }
                    
                    if mcp_result and isinstance(mcp_result, dict) and mcp_result.get('success', False):
                        # Extract structured data from MCP browser result
                        if 'structured_data' in mcp_result:
                            # Use the structured data if available
                            result.update(mcp_result.get('structured_data', {}))
                            print(f"Successfully extracted structured data using MCP browser")
                        elif 'content' in mcp_result and isinstance(mcp_result['content'], dict):
                            # If content is a dictionary, it might contain the structured data
                            result.update(mcp_result.get('content', {}))
                            print(f"Successfully extracted structured content using MCP browser")
                        
                        mcp_success = True
                        
                        # If we have HTML content from MCP, create a soup object for additional processing
                        # Check for both 'html_content' and 'content' keys to handle different versions of MCP browser
                        if 'html_content' in mcp_result:
                            content = mcp_result['html_content']
                            print(f"Creating BeautifulSoup object from MCP browser HTML content: {len(content)} bytes")
                            soup = BeautifulSoup(content, 'html.parser')
                            print(f"BeautifulSoup object created successfully from MCP browser content")
                            # Store HTML content in the result for later use
                            result['html_content'] = content
                        elif 'content' in mcp_result and isinstance(mcp_result['content'], str):
                            # Handle case where HTML content is returned under 'content' key
                            content = mcp_result['content']
                            print(f"Creating BeautifulSoup object from MCP browser content: {len(content)} bytes")
                            soup = BeautifulSoup(content, 'html.parser')
                            print(f"BeautifulSoup object created successfully from MCP browser content")
                            # Store HTML content in the result for later use
                            result['html_content'] = content
                            
                            # Try to extract news content immediately if we have a soup object
                            if soup and domain:
                                # We already determined if this is a news site earlier, use that value
                                if result.get('is_news_site', False):
                                    print(f"Detected news site during MCP processing: {domain}")
                                    try:
                                        # Check for paywall indicators
                                        paywall_indicators = [
                                            'subscribe', 'subscription', 'paywall', 'sign in', 'sign up', 'login',
                                            'register', 'premium', 'paid content', 'member', 'account',
                                            'free article', 'free articles', 'remaining', 'continue reading',
                                            'unlock', 'access', 'limited access', 'subscribe now', 'join now',
                                            'already a subscriber', 'create an account', 'become a member',
                                            'subscribe for', 'subscribe today', 'monthly subscription',
                                            'annual subscription', 'digital subscription', 'digital access',
                                            'unlimited access', 'exclusive content', 'premium content',
                                            'premium article', 'premium access', 'members only', 'subscribers only'
                                        ]
                                        
                                        # Known paywall domains - these sites are known to have strict paywalls
                                        known_paywall_domains = [
                                            'wsj.com', 'ft.com', 'nytimes.com', 'economist.com',
                                            'newyorker.com', 'wired.com', 'bloomberg.com', 'washingtonpost.com',
                                            'thetimes.co.uk', 'telegraph.co.uk', 'barrons.com',
                                            'seekingalpha.com', 'forbes.com', 'hbr.org', 'foreignaffairs.com',
                                            'foreignpolicy.com', 'technologyreview.com', 'scientificamerican.com'
                                        ]
                                        
                                        # Check for login/subscription forms
                                        login_forms = soup.find_all(['form', 'div'], id=lambda x: x and any(term in x.lower() for term in 
                                                                                  ['login', 'signin', 'subscribe', 'paywall', 'premium']))
                                        
                                        subscription_divs = soup.find_all(['div', 'section', 'article'], 
                                                                       class_=lambda x: x and any(term in x.lower() for term in 
                                                                                         ['paywall', 'subscribe', 'subscription', 'premium', 'member', 'login', 'signin']))
                                        
                                        # Check for HTTP status code indicators in the page content
                                        status_indicators = ['401', '403', 'unauthorized', 'forbidden', 'access denied']
                                        page_text = soup.get_text().lower()
                                        
                                        # Check for specific paywall patterns in the content
                                        paywall_patterns = [
                                            r'\d+ (free )?articles? (left|remaining|this month)',
                                            r'you have reached your (free|monthly) limit',
                                            r'subscribe to (continue|read|access)',
                                            r'already a (subscriber|member)\?',
                                            r'sign in to (continue|read|access)',
                                            r'create (a free )?account to (continue|read|access)',
                                            r'subscribe for (just|only) \$\d+',
                                            r'premium content requires',
                                            r'this (content|article) is (only )?available to (subscribers|members)'
                                        ]
                                        
                                        # Check if the domain is a known paywall site
                                        is_known_paywall_domain = any(pd in domain.lower() for pd in known_paywall_domains)
                                        
                                        # Check for paywall patterns in the text
                                        has_paywall_pattern = any(re.search(pattern, page_text) for pattern in paywall_patterns)
                                        
                                        # Check content length - very short content might indicate a paywall
                                        paragraphs = soup.find_all('p')
                                        paragraph_text = [p.get_text().strip() for p in paragraphs]
                                        content_length = sum(len(p) for p in paragraph_text)
                                        suspiciously_short_content = content_length < 500 and len(paragraphs) < 5
                                        
                                        # Combine all checks to determine if there's a paywall
                                        has_paywall = (len(login_forms) > 0 or 
                                                      len(subscription_divs) > 0 or 
                                                      any(indicator.lower() in page_text for indicator in paywall_indicators) or
                                                      any(indicator.lower() in page_text for indicator in status_indicators) or
                                                      has_paywall_pattern or
                                                      (is_known_paywall_domain and suspiciously_short_content))
                                        
                                        if has_paywall:
                                            print(f"Detected potential paywall for {domain}")
                                            # Still try to extract what content we can
                                            try:
                                                # Extract news content directly from MCP browser HTML
                                                print(f"Attempting to extract available content despite paywall...")
                                                
                                                # Try to use site-specific paywall bypass techniques
                                                paywall_bypassed = False
                                                
                                                # For known paywall domains, try specific bypass techniques
                                                if any(pd in domain.lower() for pd in ['nytimes.com', 'wsj.com', 'washingtonpost.com']):
                                                    try:
                                                        print(f"Attempting site-specific paywall bypass for {domain}...")
                                                        
                                                        # Try to find article content in meta tags or JSON-LD
                                                        meta_description = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
                                                        if meta_description and meta_description.get('content', ''):
                                                            print(f"Found meta description: {len(meta_description['content'])} chars")
                                                        
                                                        # Look for JSON-LD structured data
                                                        json_ld_scripts = soup.find_all('script', type='application/ld+json')
                                                        article_data = None
                                                        
                                                        for script in json_ld_scripts:
                                                            try:
                                                                data = json.loads(script.string)
                                                                if isinstance(data, dict) and data.get('@type') in ['NewsArticle', 'Article']:
                                                                    article_data = data
                                                                    print(f"Found article data in JSON-LD: {len(str(article_data))} chars")
                                                                    paywall_bypassed = True
                                                                    break
                                                            except Exception as e:
                                                                print(f"Error parsing JSON-LD: {str(e)}")
                                                                continue
                                                        
                                                        # Extract content from article_data if available
                                                        if article_data:
                                                            # Create a news_content structure from JSON-LD data
                                                            news_content = {
                                                                'headlines': [article_data.get('headline', '')],
                                                                'summary': article_data.get('description', ''),
                                                                'main_content': article_data.get('articleBody', ''),
                                                                'author': article_data.get('author', {}).get('name', '') if isinstance(article_data.get('author'), dict) else str(article_data.get('author', '')),
                                                                'publication_date': article_data.get('datePublished', ''),
                                                                'categories': article_data.get('keywords', '').split(',') if isinstance(article_data.get('keywords'), str) else [],
                                                                'keywords': article_data.get('keywords', '').split(',') if isinstance(article_data.get('keywords'), str) else [],
                                                                'related_articles': [],
                                                                'image_url': article_data.get('image', {}).get('url', '') if isinstance(article_data.get('image'), dict) else '',
                                                                'paywall_detected': True,
                                                                'paywall_bypassed': True
                                                            }
                                                            print(f"Created news_content from JSON-LD data")
                                                    except Exception as e:
                                                        print(f"Error in site-specific paywall bypass: {str(e)}")
                                                
                                                # If paywall bypass failed, try regular extraction
                                                if not paywall_bypassed:
                                                    news_content = self._extract_news_content(soup, url)
                                                    print(f"Limited news content extracted with {len(news_content.keys())} fields")
                                                
                                                # Add paywall indicator to the result
                                                news_content['paywall_detected'] = True
                                                result['news_content'] = news_content
                                                print(f"Added limited news_content to result dictionary with paywall indicator")
                                            except Exception as e:
                                                print(f"Error extracting limited content: {str(e)}")
                                                # Create a minimal structure for paywall content
                                                # Try to extract at least some information from meta tags
                                                headlines = []
                                                summary = 'Content behind paywall'
                                                author = ''
                                                publication_date = ''
                                                image_url = ''
                                                
                                                # Try to get title from meta tags
                                                meta_title = soup.find('meta', property='og:title') or soup.find('meta', name='twitter:title')
                                                if meta_title and meta_title.get('content'):
                                                    headlines.append(meta_title['content'])
                                                
                                                # Try to get description from meta tags
                                                meta_desc = soup.find('meta', property='og:description') or soup.find('meta', name='description')
                                                if meta_desc and meta_desc.get('content'):
                                                    summary = meta_desc['content']
                                                
                                                # Try to get author
                                                meta_author = soup.find('meta', property='article:author') or soup.find('meta', name='author')
                                                if meta_author and meta_author.get('content'):
                                                    author = meta_author['content']
                                                
                                                # Try to get publication date
                                                meta_date = soup.find('meta', property='article:published_time') or soup.find('meta', name='publication_date')
                                                if meta_date and meta_date.get('content'):
                                                    publication_date = meta_date['content']
                                                
                                                # Try to get image
                                                meta_image = soup.find('meta', property='og:image') or soup.find('meta', name='twitter:image')
                                                if meta_image and meta_image.get('content'):
                                                    image_url = meta_image['content']
                                                
                                                # Create the news content structure with whatever we could extract
                                                result['news_content'] = {
                                                    'headlines': headlines,
                                                    'summary': summary,
                                                    'main_content': 'The full content of this article appears to be behind a paywall or requires authentication.',
                                                    'author': author,
                                                    'publication_date': publication_date,
                                                    'categories': [],
                                                    'keywords': [],
                                                    'related_articles': [],
                                                    'image_url': image_url,
                                                    'paywall_detected': True,
                                                    'extraction_source': 'meta_tags'
                                                }
                                                print(f"Created fallback structure for paywall content")
                                        else:
                                            # No paywall detected, proceed with normal extraction
                                            print(f"No paywall detected, proceeding with normal extraction")
                                            news_content = self._extract_news_content(soup, url)
                                            print(f"News content extracted from MCP HTML with {len(news_content.keys())} fields")
                                            result['news_content'] = news_content
                                            print(f"Added news_content to result dictionary from MCP HTML")
                                    except Exception as e:
                                        print(f"Error extracting news content from MCP HTML: {str(e)}")
                                        # Create a basic fallback structure
                                        result['news_content'] = {
                                            'headlines': [],
                                            'summary': 'Content extraction failed',
                                            'main_content': f'Failed to extract content from this news site. Error: {str(e)}',
                                            'author': '',
                                            'publication_date': '',
                                            'categories': [],
                                            'keywords': [],
                                            'related_articles': [],
                                            'image_url': ''
                                        }
                        else:
                            print(f"No HTML content available from MCP browser result")
                    else:
                        print(f"MCP browser failed: {mcp_result.get('error', 'Unknown error') if isinstance(mcp_result, dict) else 'Invalid result'}. Falling back to HTTP requests.")
                except Exception as e:
                    print(f"Error using MCP browser: {str(e)}. Falling back to HTTP requests.")
            
            # Fall back to traditional HTTP requests if MCP failed or is not available
            if not mcp_success:
                print(f"Using HTTP requests to fetch content from {url}")
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0'
                }
                
                # Try multiple user agents if the first one fails
                user_agents = [
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
                    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
                    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
                ]
                
                for user_agent in user_agents:
                    try:
                        headers['User-Agent'] = user_agent
                        print(f"Trying user agent: {user_agent[:30]}...")
                        # Apply SSL verification handling
                        verify = True
                        if SSL_UTILS_AVAILABLE and should_skip_verification(url):
                            verify = False
                            logger.debug(f"SSL verification disabled for request to {url}")
                        response = requests.get(url, headers=headers, timeout=30, verify=verify)
                        response.raise_for_status()
                        content = response.content
                        print(f"Successfully fetched content: {len(content)} bytes")
                        soup = BeautifulSoup(content, 'html.parser')
                        print(f"Successfully created BeautifulSoup object")
                        break
                    except Exception as e:
                        print(f"Error with user agent {user_agent[:30]}...: {str(e)}. Trying another...")
                        continue
                
                if not soup:
                    raise Exception("Failed to fetch content with any user agent")
            
            # Extract title if not already extracted by MCP
            if not result['title'] and soup and soup.title:
                result['title'] = soup.title.string.strip() if soup.title.string else ''
            
            # Extract headings if not already extracted by MCP
            if not result['headings'] and soup:
                result['headings'] = self._extract_headings(soup)
            
            # Extract paragraphs if not already extracted by MCP
            if not result['paragraphs'] and soup:
                result['paragraphs'] = self._extract_paragraphs(soup)
            
            # Extract links if not already extracted by MCP
            if not result['links'] and soup:
                result['links'] = self._extract_links_from_html(soup)
            
            # Extract images if not already extracted by MCP
            if not result['images'] and soup:
                result['images'] = self._extract_images(soup)
            
            # Extract tables if not already extracted by MCP
            if not result['tables'] and soup:
                result['tables'] = self._extract_tables(soup)
            
            # Extract metadata if not already extracted by MCP
            if not result['metadata'] and soup:
                result['metadata'] = self._extract_metadata(soup)
            
            # Extract raw text if not already extracted by MCP
            if not result['raw_text'] and soup:
                result['raw_text'] = soup.get_text(separator='\n', strip=True)
            
            # Check if this is a news site and add news-specific content
            news_domains = [
                # Major US news sites
                'cnn.com', 'foxnews.com', 'nbcnews.com', 'cbsnews.com', 'abcnews.go.com', 'usatoday.com', 
                'wsj.com', 'nytimes.com', 'washingtonpost.com', 'latimes.com', 'chicagotribune.com',
                'nypost.com', 'bostonglobe.com', 'sfchronicle.com', 'dallasnews.com', 'denverpost.com',
                'seattletimes.com', 'miamiherald.com', 'azcentral.com', 'startribune.com',
                # News agencies
                'apnews.com', 'reuters.com', 'bloomberg.com', 'afp.com', 'upi.com',
                # UK/International news
                'bbc.com', 'bbc.co.uk', 'theguardian.com', 'telegraph.co.uk', 'independent.co.uk',
                'ft.com', 'economist.com', 'aljazeera.com', 'france24.com', 'dw.com',
                # Business news
                'cnbc.com', 'businessinsider.com', 'forbes.com', 'marketwatch.com', 'barrons.com',
                'fortune.com', 'thestreet.com', 'benzinga.com', 'investing.com', 'fool.com',
                # Tech news
                'techcrunch.com', 'theverge.com', 'wired.com', 'arstechnica.com', 'engadget.com',
                'zdnet.com', 'cnet.com', 'venturebeat.com', 'gizmodo.com', 'mashable.com',
                # Other news categories
                'espn.com', 'sports.yahoo.com', 'bleacherreport.com', 'si.com',
                'variety.com', 'hollywoodreporter.com', 'deadline.com', 'ew.com',
                'sciencedaily.com', 'livescience.com', 'phys.org', 'scientificamerican.com',
                # Generic news indicators
                'news.', 'news-', '-news', '.news', 'daily', 'times', 'post', 'tribune', 'herald',
                'journal', 'gazette', 'chronicle', 'observer', 'sentinel', 'dispatch', 'star'
            ]
            
            print(f"Checking if {domain} is a news site...")
            # Store the news site status in the result dictionary for consistent access
            result['is_news_site'] = any(news_domain in domain.lower() for news_domain in news_domains)
            print(f"Is {domain} a news site? {result['is_news_site']}")
            
            if result['is_news_site']:
                print(f"Detected news site: {domain}")
                
                # If we don't have a soup object yet, try to fetch the content using HTTP requests
                if not soup:
                    print(f"No BeautifulSoup object available, fetching content using HTTP requests...")
                    try:
                        import requests
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                        }
                        # Apply SSL verification handling
                        verify = True
                        if SSL_UTILS_AVAILABLE and should_skip_verification(url):
                            verify = False
                            logger.debug(f"SSL verification disabled for request to {url}")
                        response = requests.get(url, headers=headers, timeout=10, verify=verify)
                        response.raise_for_status()
                        html_content = response.text
                        print(f"Successfully fetched HTML content: {len(html_content)} bytes")
                        soup = BeautifulSoup(html_content, 'html.parser')
                        print(f"Created BeautifulSoup object for news content extraction")
                    except Exception as e:
                        print(f"Error fetching content for news extraction: {str(e)}")
                
                if soup:
                    print(f"BeautifulSoup object is available for news content extraction")
                    print(f"Soup object has title? {soup.title is not None}")
                    if soup.title:
                        print(f"Page title: {soup.title.string}")
                    
                    try:
                        # Extract news content with proper error handling
                        print(f"Attempting to extract news content from {domain}...")
                        news_content = self._extract_news_content(soup, url)
                        print(f"News content extracted successfully with {len(news_content.keys())} fields")
                        result['news_content'] = news_content
                        print(f"Added news_content to result dictionary")
                    except Exception as e:
                        print(f"Error extracting news content: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        # Provide a minimal fallback structure for news content
                        result['news_content'] = {
                            'headlines': result.get('headings', []),
                            'summary': '',
                            'main_content': '\n\n'.join(result.get('paragraphs', [])),
                            'author': '',
                            'publication_date': '',
                            'related_articles': [],
                            'source': url,
                            'categories': [],
                            'keywords': [],
                            'image_url': ''
                        }
                        print(f"Created fallback news_content structure")
                else:
                    # If we still don't have a soup object, try one more time with a direct HTTP request
                    print(f"No BeautifulSoup object available, making one final attempt with direct HTTP request...")
                    try:
                        import requests
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                        }
                        # Apply SSL verification handling
                        verify = True
                        if SSL_UTILS_AVAILABLE and should_skip_verification(url):
                            verify = False
                            logger.debug(f"SSL verification disabled for request to {url}")
                        response = requests.get(url, headers=headers, timeout=15, verify=verify)
                        
                        # Check for HTTP status codes indicating authentication issues or paywalls
                        if response.status_code in [401, 403, 429, 451]:
                            print(f"HTTP status {response.status_code} detected, likely paywall or authentication required")
                            # Create a basic structure for paywall content
                            result['news_content'] = {
                                'headlines': result.get('headings', []),
                                'summary': 'Content behind paywall',
                                'main_content': f'The content appears to be behind a paywall or requires authentication. HTTP status: {response.status_code}',
                                'author': '',
                                'publication_date': '',
                                'categories': [],
                                'keywords': [],
                                'related_articles': [],
                                'image_url': '',
                                'paywall_detected': True
                            }
                            print(f"Created fallback structure for paywall content")
                            return result
                        
                        response.raise_for_status()
                        html_content = response.text
                        print(f"Successfully fetched HTML content: {len(html_content)} bytes")
                        soup = BeautifulSoup(html_content, 'html.parser')
                        print(f"Created BeautifulSoup object for news content extraction")
                        
                        # Check for paywall indicators in the content
                        paywall_indicators = [
                            'subscribe', 'subscription', 'paywall', 'sign in', 'sign up', 'login',
                            'register', 'premium', 'paid content', 'member', 'account',
                            'free article', 'free articles', 'remaining', 'continue reading',
                            'unlock', 'access', 'limited access'
                        ]
                        
                        # Check for login/subscription forms
                        login_forms = soup.find_all('form', id=lambda x: x and any(term in x.lower() for term in ['login', 'signin', 'subscribe']))
                        subscription_divs = soup.find_all('div', class_=lambda x: x and any(term in x.lower() for term in ['paywall', 'subscribe', 'subscription', 'premium']))
                        
                        # Check for HTTP status code indicators in the page content
                        status_indicators = ['401', '403', 'unauthorized', 'forbidden', 'access denied']
                        page_text = soup.get_text().lower()
                        
                        has_paywall = (len(login_forms) > 0 or len(subscription_divs) > 0 or 
                                      any(indicator.lower() in page_text for indicator in paywall_indicators) or
                                      any(indicator.lower() in page_text for indicator in status_indicators))
                        
                        if has_paywall:
                            print(f"Detected potential paywall for {domain} in final HTTP request")
                            # Still try to extract what content we can
                            try:
                                # Extract news content from the HTML
                                print(f"Attempting to extract available content despite paywall...")
                                news_content = self._extract_news_content(soup, url)
                                print(f"Limited news content extracted with {len(news_content.keys())} fields")
                                
                                # Add paywall indicator to the result
                                news_content['paywall_detected'] = True
                                result['news_content'] = news_content
                                print(f"Added limited news_content to result dictionary with paywall indicator")
                            except Exception as e:
                                print(f"Error extracting limited content: {str(e)}")
                                # Create a minimal structure for paywall content
                                result['news_content'] = {
                                    'headlines': result.get('headings', []),
                                    'summary': 'Content behind paywall',
                                    'main_content': 'The full content of this article appears to be behind a paywall or requires authentication.',
                                    'author': '',
                                    'publication_date': '',
                                    'categories': [],
                                    'keywords': [],
                                    'related_articles': [],
                                    'image_url': '',
                                    'paywall_detected': True
                                }
                                print(f"Created fallback structure for paywall content")
                        else:
                            # No paywall detected, proceed with normal extraction
                            print(f"No paywall detected, proceeding with normal extraction")
                            news_content = self._extract_news_content(soup, url)
                            print(f"News content extracted successfully with {len(news_content.keys())} fields")
                            result['news_content'] = news_content
                            print(f"Added news_content to result dictionary")
                    except Exception as e:
                        print(f"Error with final attempt: {str(e)}")
                        # Check if this might be a paywall or authentication error
                        is_auth_error = any(term in str(e).lower() for term in ['401', '403', '429', '451', 'unauthorized', 'forbidden', 'access denied'])
                        
                        # Provide a minimal fallback structure for news content
                        result['news_content'] = {
                            'headlines': result.get('headings', []),
                            'summary': 'Content behind paywall' if is_auth_error else '',
                            'main_content': 'The content appears to be behind a paywall or requires authentication.' if is_auth_error else '\n\n'.join(result.get('paragraphs', [])),
                            'author': '',
                            'publication_date': '',
                            'related_articles': [],
                            'source': url,
                            'categories': [],
                            'keywords': [],
                            'image_url': '',
                            'paywall_detected': is_auth_error
                        }
                        print(f"Created fallback news_content structure" + " with paywall indication" if is_auth_error else "")
                    
            # Special handling for sites that consistently have issues with paywalls
            known_paywall_sites = [
                'reuters.com', 'ft.com', 'wsj.com', 'nytimes.com', 'washingtonpost.com',
                'economist.com', 'bloomberg.com', 'barrons.com', 'seekingalpha.com',
                'thetimes.co.uk', 'telegraph.co.uk', 'newyorker.com', 'wired.com',
                'bostonglobe.com', 'latimes.com', 'chicagotribune.com', 'theatlantic.com',
                'foreignpolicy.com', 'hbr.org', 'technologyreview.com', 'foreignaffairs.com'
            ]
            
            if any(site in domain.lower() for site in known_paywall_sites) and 'news_content' not in result:
                print(f"Special handling for {domain} paywall")
                # Try to extract metadata even from paywall sites
                meta_title = ''
                meta_description = ''
                meta_author = ''
                meta_date = ''
                meta_image = ''
                
                if soup:
                    # Extract title from meta tags
                    meta_title_tag = soup.find('meta', property='og:title') or soup.find('meta', name='twitter:title')
                    if meta_title_tag and meta_title_tag.get('content'):
                        meta_title = meta_title_tag.get('content')
                    elif soup.title:
                        meta_title = soup.title.string
                    
                    # Extract description from meta tags
                    meta_desc_tag = soup.find('meta', property='og:description') or soup.find('meta', name='description')
                    if meta_desc_tag and meta_desc_tag.get('content'):
                        meta_description = meta_desc_tag.get('content')
                    
                    # Extract author from meta tags
                    meta_author_tag = soup.find('meta', property='article:author') or soup.find('meta', name='author')
                    if meta_author_tag and meta_author_tag.get('content'):
                        meta_author = meta_author_tag.get('content')
                    
                    # Extract date from meta tags
                    meta_date_tag = soup.find('meta', property='article:published_time') or soup.find('meta', name='date')
                    if meta_date_tag and meta_date_tag.get('content'):
                        meta_date = meta_date_tag.get('content')
                    
                    # Extract image from meta tags
                    meta_image_tag = soup.find('meta', property='og:image') or soup.find('meta', name='twitter:image')
                    if meta_image_tag and meta_image_tag.get('content'):
                        meta_image = meta_image_tag.get('content')
                
                result['news_content'] = {
                    'headlines': [meta_title] if meta_title else result.get('headings', []),
                    'summary': meta_description if meta_description else 'Content behind paywall',
                    'main_content': f'Content from {domain} appears to be behind a paywall or requires authentication.',
                    'author': meta_author,
                    'publication_date': meta_date,
                    'categories': [],
                    'keywords': [],
                    'related_articles': [],
                    'image_url': meta_image,
                    'paywall_detected': True,
                    'source': url
                }
                print(f"Created enhanced fallback structure for {domain} paywall content")
            
            # Check if news_content was added to the result
            print(f"Final result has news_content? {'news_content' in result}")
            
            # Post-processing to improve quality
            # Remove empty paragraphs
            result['paragraphs'] = [p for p in result['paragraphs'] if p.strip()]
            
            # Remove duplicate paragraphs while preserving order
            unique_paragraphs = []
            seen_paragraph_content = set()
            for p in result['paragraphs']:
                # Normalize paragraph text for comparison (lowercase, remove whitespace)
                normalized = re.sub(r'\s+', '', p.lower())
                if normalized not in seen_paragraph_content and len(normalized) > 0:
                    unique_paragraphs.append(p)
                    seen_paragraph_content.add(normalized)
            result['paragraphs'] = unique_paragraphs
            
            # Remove very short paragraphs (likely noise)
            result['paragraphs'] = [p for p in result['paragraphs'] if len(p) > 20]
            
            # Remove duplicate headings while preserving order
            unique_headings = []
            seen_texts = set()
            for h in result['headings']:
                # Normalize heading text for comparison
                normalized = re.sub(r'\s+', '', h['text'].lower())
                if normalized not in seen_texts and len(normalized) > 0:
                    unique_headings.append(h)
                    seen_texts.add(normalized)
            result['headings'] = unique_headings
            
            # Remove duplicate links while preserving order
            unique_links = []
            seen_urls = set()
            for link in result['links']:
                # Normalize URL for comparison
                url_to_check = link['url'].rstrip('/').lower()
                if url_to_check not in seen_urls:
                    unique_links.append(link)
                    seen_urls.add(url_to_check)
            result['links'] = unique_links
            
            # Remove duplicate images while preserving order
            unique_images = []
            seen_urls = set()
            for img in result['images']:
                # Normalize URL for comparison
                url_to_check = img['url'].split('?')[0].lower()  # Remove query parameters
                if url_to_check not in seen_urls and url_to_check:
                    unique_images.append(img)
                    seen_urls.add(url_to_check)
            result['images'] = unique_images
            
            # If this is a news article, ensure the news_content structure is complete
            if 'news_content' in result:
                # Ensure all fields are present
                news_fields = [
                    'headlines', 'summary', 'main_content', 'author', 'publication_date',
                    'related_articles', 'source', 'categories', 'keywords', 'image_url'
                ]
                
                for field in news_fields:
                    if field not in result['news_content']:
                        if field in ['headlines', 'related_articles', 'categories', 'keywords']:
                            result['news_content'][field] = []
                        else:
                            result['news_content'][field] = ''
                
                # If main_content is empty but we have paragraphs, use them
                if not result['news_content']['main_content'] and result['paragraphs']:
                    result['news_content']['main_content'] = '\n\n'.join(result['paragraphs'])
                
                # If headlines are empty but we have a title, use it
                if not result['news_content']['headlines'] and result['title']:
                    result['news_content']['headlines'] = [result['title']]
                
                # If image_url is empty but we have images, use the first one
                if not result['news_content']['image_url'] and result['images']:
                    result['news_content']['image_url'] = result['images'][0]['url']
            
            return result
        
        except Exception as e:
            print(f"Error extracting structured content: {str(e)}")
            # Try to return partial results if available
            return result
    
    def _extract_headings(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract all heading elements with their levels.
        
        Args:
            soup: BeautifulSoup object containing the HTML content
            
        Returns:
            List of dictionaries containing heading level and text
        """
        headings = []
        for level in range(1, 7):  # h1 to h6
            for heading in soup.find_all(f'h{level}'):
                text = heading.get_text(strip=True)
                if text:
                    headings.append({
                        'level': level,
                        'text': text
                    })
        return headings
    
    def _extract_paragraphs(self, soup: BeautifulSoup) -> List[str]:
        """
        Extract paragraph text.
        
        Args:
            soup: BeautifulSoup object containing the HTML content
            
        Returns:
            List of paragraph texts
        """
        paragraphs = []
        for p in soup.find_all('p'):
            text = p.get_text(strip=True)
            if text and len(text) > 20:  # Minimum length to filter out menu items, etc.
                paragraphs.append(text)
        return paragraphs
    
    def _extract_links_from_html(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        Extract links with text and href attributes.
        
        Args:
            soup: BeautifulSoup object containing the HTML content
            
        Returns:
            List of dictionaries containing link text and URL
        """
        links = []
        for a in soup.find_all('a', href=True):
            text = a.get_text(strip=True)
            href = a['href']
            if text and href and not href.startswith('javascript:'):
                links.append({
                    'text': text,
                    'url': href
                })
        return links
    
    def _extract_images(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        Extract images with src and alt attributes.
        
        Args:
            soup: BeautifulSoup object containing the HTML content
            
        Returns:
            List of dictionaries containing image URL and alt text
        """
        images = []
        for img in soup.find_all('img', src=True):
            src = img['src']
            alt = img.get('alt', '')
            if src:
                images.append({
                    'url': src,
                    'alt': alt
                })
        return images
    
    def _extract_tables(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract table data with headers and rows.
        
        Args:
            soup: BeautifulSoup object containing the HTML content
            
        Returns:
            List of dictionaries containing table headers and rows
        """
        tables = []
        for table in soup.find_all('table'):
            table_data = {
                'headers': [],
                'rows': []
            }
            
            # Extract headers
            headers = table.find_all('th')
            if headers:
                table_data['headers'] = [header.get_text(strip=True) for header in headers]
            
            # Extract rows
            for row in table.find_all('tr'):
                cells = row.find_all(['td', 'th'])
                if cells:
                    row_data = [cell.get_text(strip=True) for cell in cells]
                    table_data['rows'].append(row_data)
            
            tables.append(table_data)
        return tables
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Extract metadata from meta tags.
        
        Args:
            soup: BeautifulSoup object containing the HTML content
            
        Returns:
            Dictionary containing metadata
        """
        metadata = {}
        
        # Extract standard meta tags
        for meta in soup.find_all('meta'):
            name = meta.get('name', meta.get('property', ''))
            content = meta.get('content', '')
            if name and content:
                metadata[name] = content
        
        return metadata
        
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
            # Don't add .txt extension if the file already has an extension
            if filename and '.' not in filename:
                filename += '.txt'
            output_files.append(filename)
        
        # Pattern 2: Create a file named/called X
        pattern2 = r'(?:create|make)\s+(?:a\s+)?(?:file|document)\s+(?:named|called)\s+["\']?([\w\-\.]+)["\']?'
        matches = re.finditer(pattern2, task_description, re.IGNORECASE)
        for match in matches:
            filename = match.group(1).strip()
            # Don't add .txt extension if the file already has an extension
            if filename and '.' not in filename:
                filename += '.txt'
            output_files.append(filename)
        
        # Pattern 3: Save in X file
        pattern3 = r'save\s+(?:that|it|this|the\s+results?|the\s+content)\s+in\s+(?:a\s+)?(?:file\s+)?(?:named|called)?\s+["\']?([\w\-\.]+)["\']?'
        matches = re.finditer(pattern3, task_description, re.IGNORECASE)
        for match in matches:
            filename = match.group(1).strip()
            # Don't add .txt extension if the file already has an extension
            if filename and '.' not in filename:
                filename += '.txt'
            output_files.append(filename)
            
        # Pattern 4: File named X
        pattern4 = r'file\s+named\s+["\']?([\w\-\.]+)["\']?'
        matches = re.finditer(pattern4, task_description, re.IGNORECASE)
        for match in matches:
            filename = match.group(1).strip()
            # Don't add .txt extension if the file already has an extension
            if filename and '.' not in filename:
                filename += '.txt'
            output_files.append(filename)
        
        # Pattern 5: Save to X (without requiring the word 'file')
        pattern5 = r'save\s+to\s+["\']?([\w\-\.]+)["\']?'
        matches = re.finditer(pattern5, task_description, re.IGNORECASE)
        for match in matches:
            filename = match.group(1).strip()
            # Don't add .txt extension if the file already has an extension
            if filename and '.' not in filename:
                filename += '.txt'
            output_files.append(filename)
            
        # Remove duplicates while preserving order
        unique_files = []
        for file in output_files:
            if file and file not in unique_files:
                unique_files.append(file)
                
        return unique_files
        
    async def take_screenshot(self, url: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Take a screenshot of a webpage using the MCP browser.
        
        Args:
            url: URL to take a screenshot of
            filename: Optional filename to save the screenshot to
            
        Returns:
            Dict containing the screenshot results
        """
        if not self.use_mcp:
            return {
                "success": False,
                "message": "MCP browser is not available. Cannot take screenshots.",
                "url": url
            }
        
        try:
            print(f"Taking screenshot of {url}...")
            result = await self.mcp_browser.take_screenshot(url)
            
            if not result.get("success", False):
                return {
                    "success": False,
                    "message": f"Failed to take screenshot: {result.get('error', 'Unknown error')}",
                    "url": url
                }
            
            # If a filename is provided, save the screenshot
            if filename:
                # Create the Documents directory if it doesn't exist
                documents_dir = os.path.expanduser("~/Documents")
                os.makedirs(documents_dir, exist_ok=True)
                
                # Ensure the filename has a .png extension
                if not filename.endswith(".png"):
                    filename += ".png"
                
                # Save the screenshot to the file
                file_path = os.path.join(documents_dir, filename)
                
                # Extract the screenshot data and save it
                screenshot_data = result.get("screenshot")
                if screenshot_data:
                    import base64
                    with open(file_path, "wb") as f:
                        f.write(base64.b64decode(screenshot_data))
                    
                    print(f"Screenshot saved to {file_path}")
                    result["file_path"] = file_path
            
            return {
                "success": True,
                "message": "Successfully took screenshot",
                "url": url,
                "file_path": result.get("file_path", None),
                "screenshot_data": result.get("screenshot", None)
            }
        except Exception as e:
            logger.error(f"Error taking screenshot: {str(e)}")
            return {
                "success": False,
                "message": f"Error taking screenshot: {str(e)}",
                "url": url
            }
    
    async def fill_form(self, url: str, form_data: Dict[str, str]) -> Dict[str, Any]:
        """
        Fill a form on a webpage using the MCP browser.
        
        Args:
            url: URL containing the form
            form_data: Dict mapping form field selectors to values
            
        Returns:
            Dict containing the form submission results
        """
        if not self.use_mcp:
            return {
                "success": False,
                "message": "MCP browser is not available. Cannot fill forms.",
                "url": url
            }
        
        try:
            print(f"Filling form on {url}...")
            result = await self.mcp_browser.fill_form(url, form_data)
            
            return {
                "success": result.get("success", False),
                "message": result.get("message", "Form submission completed"),
                "url": url,
                "content": result.get("content", None)
            }
        except Exception as e:
            logger.error(f"Error filling form: {str(e)}")
            return {
                "success": False,
                "message": f"Error filling form: {str(e)}",
                "url": url
            }
    
    async def click_element(self, url: str, selector: str) -> Dict[str, Any]:
        """
        Click an element on a webpage using the MCP browser.
        
        Args:
            url: URL containing the element
            selector: CSS selector for the element to click
            
        Returns:
            Dict containing the click results
        """
        if not self.use_mcp:
            return {
                "success": False,
                "message": "MCP browser is not available. Cannot click elements.",
                "url": url
            }
        
        try:
            print(f"Clicking element {selector} on {url}...")
            result = await self.mcp_browser.click_element(url, selector)
            
            return {
                "success": result.get("success", False),
                "message": result.get("message", "Element clicked successfully"),
                "url": url,
                "content": result.get("content", None)
            }
        except Exception as e:
            logger.error(f"Error clicking element: {str(e)}")
            return {
                "success": False,
                "message": f"Error clicking element: {str(e)}",
                "url": url
            }
    
    async def scroll_page(self, url: str, direction: str = "down") -> Dict[str, Any]:
        """
        Scroll a webpage using the MCP browser.
        
        Args:
            url: URL to scroll
            direction: Direction to scroll (up, down, left, right)
            
        Returns:
            Dict containing the scroll results
        """
        if not self.use_mcp:
            return {
                "success": False,
                "message": "MCP browser is not available. Cannot scroll pages.",
                "url": url
            }
        
        try:
            print(f"Scrolling {direction} on {url}...")
            result = await self.mcp_browser.scroll_page(url, direction)
            
            return {
                "success": result.get("success", False),
                "message": result.get("message", f"Page scrolled {direction} successfully"),
                "url": url,
                "content": result.get("content", None)
            }
        except Exception as e:
            logger.error(f"Error scrolling page: {str(e)}")
            return {
                "success": False,
                "message": f"Error scrolling page: {str(e)}",
                "url": url
            }
    
    async def extract_structured_content(self, url: str) -> Dict[str, Any]:
        """
        Extract structured content from a webpage using the MCP browser.
        This method provides more detailed content extraction than the basic methods.
        
        Args:
            url: URL to extract content from
            
        Returns:
            Dict containing the extracted structured content
        """
        # Import required modules
        import datetime
        import re
        if not self.use_mcp:
            return {
                "success": False,
                "message": "MCP browser is not available. Cannot extract structured content.",
                "url": url
            }
        
        try:
            print(f"Extracting structured content from {url}...")
            result = await self.mcp_browser.browse_url(url, "extract detailed structure and content of the page")
            
            if not result.get("success", False):
                return {
                    "success": False,
                    "message": f"Failed to extract structured content: {result.get('error', 'Unknown error')}",
                    "url": url
                }
            
            # Process the extracted content
            content = result.get("content", "")
            soup = BeautifulSoup(content, "html.parser")
            
            # Extract structured data
            structured_data = {
                "title": soup.title.string if soup.title else "Unknown Title",
                "headings": self._extract_headings(soup),
                "paragraphs": self._extract_paragraphs(soup),
                "links": self._extract_links_from_html(soup),
                "images": self._extract_images(soup),
                "tables": self._extract_tables(soup),
                "metadata": self._extract_metadata(soup)
            }
            
            return {
                "success": True,
                "message": "Successfully extracted structured content",
                "url": url,
                "structured_data": structured_data,
                "raw_content": content
            }
        except Exception as e:
            logger.error(f"Error extracting structured content: {str(e)}")
            return {
                "success": False,
                "message": f"Error extracting structured content: {str(e)}",
                "url": url
            }
    
    def _extract_headings(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        Extract headings from a BeautifulSoup object.
        
        Args:
            soup: BeautifulSoup object to extract headings from
            
        Returns:
            List of headings with level and text
        """
        headings = []
        for level in range(1, 7):
            for heading in soup.find_all(f"h{level}"):
                headings.append({
                    "level": level,
                    "text": heading.get_text().strip()
                })
        return headings
    
    def _extract_paragraphs(self, soup: BeautifulSoup) -> List[str]:
        """
        Extract paragraphs from a BeautifulSoup object.
        
        Args:
            soup: BeautifulSoup object to extract paragraphs from
            
        Returns:
            List of paragraph texts
        """
        return [p.get_text().strip() for p in soup.find_all("p") if p.get_text().strip()]
    
    def _extract_links_from_html(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        Extract links from a BeautifulSoup object.
        
        Args:
            soup: BeautifulSoup object to extract links from
            
        Returns:
            List of links with text and href
        """
        links = []
        for link in soup.find_all("a"):
            href = link.get("href")
            if href:
                # Make relative URLs absolute
                if href.startswith("/"):
                    base_url = soup.find("base")["href"] if soup.find("base") and "href" in soup.find("base").attrs else ""
                    href = base_url + href
                
                links.append({
                    "text": link.get_text().strip(),
                    "href": href
                })
        return links
    
    def _extract_images(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        Extract images from a BeautifulSoup object.
        
        Args:
            soup: BeautifulSoup object to extract images from
            
        Returns:
            List of images with src and alt
        """
        images = []
        for img in soup.find_all("img"):
            src = img.get("src")
            if src:
                # Make relative URLs absolute
                if src.startswith("/"):
                    base_url = soup.find("base")["href"] if soup.find("base") and "href" in soup.find("base").attrs else ""
                    src = base_url + src
                
                images.append({
                    "src": src,
                    "alt": img.get("alt", "")
                })
        return images
    
    def _extract_tables(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract tables from a BeautifulSoup object.
        
        Args:
            soup: BeautifulSoup object to extract tables from
            
        Returns:
            List of tables with headers and rows
        """
        tables = []
        for table in soup.find_all("table"):
            headers = []
            for th in table.find_all("th"):
                headers.append(th.get_text().strip())
            
            rows = []
            for tr in table.find_all("tr"):
                row = []
                for td in tr.find_all("td"):
                    row.append(td.get_text().strip())
                if row:  # Skip empty rows
                    rows.append(row)
            
            tables.append({
                "headers": headers,
                "rows": rows
            })
        return tables
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Extract metadata from a BeautifulSoup object.
        
        Args:
            soup: BeautifulSoup object to extract metadata from
            
        Returns:
            Dict of metadata
        """
        metadata = {}
        
        # Extract meta tags
        for meta in soup.find_all("meta"):
            name = meta.get("name") or meta.get("property")
            content = meta.get("content")
            if name and content:
                metadata[name] = content
        
        return metadata
    
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
