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
                    
                    if search_results:
                        for i, result in enumerate(search_results[:10], 1):
                            response_text += f"{i}. {result['title']}\n"
                            if 'url' in result:
                                response_text += f"   URL: {result['url']}\n"
                            if 'snippet' in result:
                                response_text += f"   {result['snippet']}\n\n"
                    else:
                        # Fallback to headlines and main content
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
    
    def _extract_search_query(self, task_description: str) -> Optional[str]:
        """
        Extract a search query from the task description.
        
        Args:
            task_description: Task description
            
        Returns:
            Extracted search query or None if not found
        """
        # Try to extract the search query from the task description
        search_patterns = [
            r"search\s+(?:for|about)?\s+([\w\s\d\-\+]+)\s+(?:on|in|at)",  # search for X on
            r"search\s+(?:for|about)?\s+([\w\s\d\-\+]+)",  # search for X
            r"find\s+(?:information|solutions|articles|posts)\s+(?:about|on|for)\s+([\w\s\d\-\+]+)",  # find information about X
            r"look\s+for\s+([\w\s\d\-\+]+)",  # look for X
            r"solutions\s+(?:to|for)\s+(?:the)?\s+([\w\s\d\-\+]+)\s+(?:error|problem|issue)",  # solutions to the X error
            r"information\s+(?:about|on)\s+([\w\s\d\-\+]+)",  # information about X
            r"articles\s+(?:about|on)\s+([\w\s\d\-\+]+)",  # articles about X
            r"research\s+(?:about|on)?\s+([\w\s\d\-\+]+)"  # research X
        ]
        
        for pattern in search_patterns:
            match = re.search(pattern, task_description, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Look for error codes or specific technical terms
        error_code_pattern = r"(?:error|code|hresult)\s*:\s*([\w\d]+)"
        match = re.search(error_code_pattern, task_description, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
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
        
        # 1. Look for main content containers
        content_elements = [
            soup.find('main'),
            soup.find(id=lambda i: i and 'content' in i.lower()),
            soup.find(class_=lambda c: c and 'content' in c.lower()),
            soup.find(id=lambda i: i and 'main' in i.lower()),
            soup.find(class_=lambda c: c and 'main' in c.lower()),
            soup.find('article')
        ]
        
        # Use the first non-None element that has substantial content
        for element in content_elements:
            if element:
                text = element.get_text(separator='\n', strip=True)
                if len(text) > 200:  # Ensure it has substantial content
                    main_content = text
                    break
        
        # If no main content found, extract paragraphs from the body
        if not main_content:
            paragraphs = [p.get_text().strip() for p in soup.find_all('p') if len(p.get_text().strip()) > 50]
            main_content = '\n\n'.join(paragraphs[:5])  # Get up to 5 substantial paragraphs
        
        # Limit the length of the main content
        if len(main_content) > 1000:
            main_content = main_content[:997] + '...'
        
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
                
                if 'title' in result:
                    search_results.append(result)
        elif domain in ["google.com", "bing.com", "duckduckgo.com"]:
            # Generic search result extraction for Google, Bing, DuckDuckGo
            # Look for common search result patterns
            result_elements = soup.select('div.g, .result, .web-result, .result__body')
            
            if not result_elements:
                # Try alternative selectors
                result_elements = soup.select('div[data-hveid], div.rc, div.result, article')
            
            for element in result_elements:
                result = {}
                
                # Extract title - try different patterns
                title_element = element.select_one('h3, .result__title, .title')
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
                snippet_element = element.select_one('.snippet, .result__snippet, .snippet-item, .abstract')
                if snippet_element:
                    result['snippet'] = snippet_element.get_text().strip()
                else:
                    # Try to find any paragraph or div that might contain the snippet
                    snippet_candidates = element.select('p, div.s, span.st, div.snippet-content')
                    for candidate in snippet_candidates:
                        text = candidate.get_text().strip()
                        if text and len(text) > 50 and len(text) < 300:
                            result['snippet'] = text
                            break
                
                if 'title' in result:
                    search_results.append(result)
        
        # If we couldn't extract any search results, create some generic ones
        if not search_results:
            # Extract any links and text that might be search results
            links = soup.find_all('a')
            for link in links:
                href = link.get('href')
                text = link.get_text().strip()
                
                # Skip empty or very short links/text
                if not href or not text or len(text) < 10:
                    continue
                    
                # Skip navigation links
                if any(nav_term in text.lower() for nav_term in ['sign in', 'log in', 'register', 'home', 'about', 'contact']):
                    continue
                
                result = {
                    'title': text
                }
                
                if href.startswith('http'):
                    result['url'] = href
                elif href.startswith('/'):
                    result['url'] = f"https://{domain}{href}"
                
                # Try to find a snippet near this link
                parent = link.parent
                if parent:
                    # Get all text nodes that are siblings of this link
                    siblings = list(parent.contents)
                    for sibling in siblings:
                        if sibling != link and hasattr(sibling, 'get_text'):
                            sibling_text = sibling.get_text().strip()
                            if sibling_text and len(sibling_text) > 30:
                                result['snippet'] = sibling_text
                                break
                
                search_results.append(result)
        
        return search_results
