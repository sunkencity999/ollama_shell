#!/usr/bin/env python3
"""
Local Web Integration for Ollama Shell

This module provides a local web browsing integration for the Ollama Shell,
allowing users to browse websites and gather information using local resources.
"""

import os
import re
import json
import logging
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

from agentic_ollama import AgenticOllama

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('local_web_integration')

class LocalWebIntegration:
    """
    Integration for browsing websites and gathering information using local resources.
    """
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the LocalWebIntegration with a specified model name.
        
        Args:
            model_name: Optional name of the model to use for local processing
        """
        self.agentic_ollama = AgenticOllama(model_name)
        self.documents_folder = os.path.expanduser("~/Documents")
        logger.info(f"Initialized Local Web Integration with model: {model_name or 'llama3.2:latest'}")
    
    async def _query_local_model(self, prompt: str, timeout: int = 60) -> str:
        """
        Query the local Ollama model with a prompt and timeout.
        
        Args:
            prompt: The prompt to send to the model
            timeout: Timeout in seconds for the request
            
        Returns:
            The model's response as a string
        """
        try:
            # Use asyncio.wait_for to implement a timeout
            response_task = self.agentic_ollama._generate_completion(prompt)
            response = await asyncio.wait_for(response_task, timeout=timeout)
            
            # Check if we got a valid response
            content = response.get("content", "") or response.get("result", "")
            if not content and response.get("success", False):
                # Try to extract content from the result field if content is empty
                content = str(response.get("result", ""))
            
            logger.info(f"LLM response received, length: {len(content)} characters")
            return content
        except asyncio.TimeoutError:
            logger.error(f"Timeout error querying local model after {timeout} seconds")
            return "The request to the language model timed out. Please try again with a simpler query."
        except Exception as e:
            logger.error(f"Error querying local model: {e}")
            return ""
    
    async def browse_website(self, url: str) -> Dict[str, Any]:
        """
        Browse a website and extract its content using local resources.
        
        Args:
            url: The URL of the website to browse
            
        Returns:
            A dictionary containing the extracted content and metadata
        """
        logger.info(f"Attempting to browse website: {url}")
        try:
            async with aiohttp.ClientSession() as session:
                try:
                    # Add timeout to avoid hanging on slow websites
                    async with session.get(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}, timeout=10) as response:
                        logger.info(f"Response status for {url}: {response.status}")
                        if response.status != 200:
                            logger.error(f"Error browsing website: {response.status}, url='{url}'")
                            return {"success": False, "error": f"HTTP error: {response.status}", "url": url}
                        
                        content = await response.text()
                        logger.info(f"Successfully retrieved content from {url}, length: {len(content)} characters")
                        
                        # Parse the HTML content
                        soup = BeautifulSoup(content, 'html.parser')
                        
                        # Remove script and style elements
                        for script in soup(["script", "style"]):
                            script.extract()
                        
                        # Get the text content
                        text = soup.get_text()
                        
                        # Clean up the text
                        lines = (line.strip() for line in text.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        text = '\n'.join(chunk for chunk in chunks if chunk)
                        
                        # Truncate if too long
                        if len(text) > 10000:
                            text = text[:10000] + "...[truncated]"
                        
                        logger.info(f"Extracted {len(text)} characters of text from {url}")
                        
                        return {
                            "success": True,
                            "url": url,
                            "title": soup.title.string if soup.title else "Unknown Title",
                            "content": text,
                            "html": content
                        }
                except asyncio.TimeoutError:
                    logger.error(f"Timeout error browsing website: {url}")
                    return {"success": False, "error": f"Timeout error: The request to {url} timed out", "url": url}
                except aiohttp.ClientError as ce:
                    logger.error(f"Client error browsing website: {url}, error: {ce}")
                    return {"success": False, "error": f"Client error: {str(ce)}", "url": url}
        except Exception as e:
            logger.error(f"Error browsing website: {e}, url='{url}', url='{url}'")
            return {"success": False, "error": str(e), "url": url}
    
    async def _extract_headlines_from_html(self, html_content: str) -> List[str]:
        """
        Extract headlines directly from HTML content without using LLM.
        
        Args:
            html_content: The HTML content to extract headlines from
            
        Returns:
            A list of extracted headlines
        """
        headlines = []
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for common headline patterns
        # 1. Check header tags (h1, h2, h3)
        for header in soup.find_all(['h1', 'h2', 'h3']):
            text = header.get_text().strip()
            if 10 < len(text) < 200:  # Filter out navigation items and very long headers
                headlines.append(text)
        
        # 2. Check elements with headline-related classes or IDs
        headline_keywords = ['headline', 'title', 'heading', 'header', 'news-item']
        for keyword in headline_keywords:
            for element in soup.find_all(class_=lambda x: x and keyword in x.lower()):
                text = element.get_text().strip()
                if 10 < len(text) < 200:
                    headlines.append(text)
            
            for element in soup.find_all(id=lambda x: x and keyword in x.lower()):
                text = element.get_text().strip()
                if 10 < len(text) < 200:
                    headlines.append(text)
        
        # Remove duplicates while preserving order
        unique_headlines = []
        seen = set()
        for headline in headlines:
            if headline not in seen:
                seen.add(headline)
                unique_headlines.append(headline)
        
        # Limit to a reasonable number
        return unique_headlines[:15]
    
    async def gather_headlines(self, websites: List[str], topic: str) -> Dict[str, Any]:
        """
        Gather headlines from a list of websites.
        
        Args:
            websites: List of website URLs to gather headlines from
            topic: The topic to gather headlines about
            
        Returns:
            A dictionary containing the gathered headlines and metadata
        """
        all_headlines = []
        successful_sites = []
        
        for url in websites:
            try:
                result = await self.browse_website(url)
                
                if not result.get("success", False):
                    continue
                
                # First try direct HTML parsing
                html_headlines = await self._extract_headlines_from_html(result.get("html", ""))
                
                if html_headlines:
                    all_headlines.extend(html_headlines)
                    successful_sites.append(url)
                    continue
                
                # If direct parsing didn't yield results, fall back to LLM
                prompt = f"""
                You are an AI assistant tasked with extracting headlines or key points from a webpage about {topic}.
                Please extract the main headlines or key points from the following webpage content.
                Return ONLY the headlines or key points, one per line, with no additional text or formatting.
                
                Webpage content:
                {result.get('content', '')[:5000]}
                """
                
                response = await self._query_local_model(prompt)
                
                if response:
                    # Process the response to extract headlines
                    headlines = [line.strip() for line in response.split('\n') if line.strip()]
                    all_headlines.extend(headlines)
                    successful_sites.append(url)
            except Exception as e:
                logger.error(f"Error gathering headlines from {url}: {e}")
        
        # Remove duplicates while preserving order
        unique_headlines = []
        seen = set()
        for headline in all_headlines:
            if headline not in seen and len(headline) > 10:
                seen.add(headline)
                unique_headlines.append(headline)
        
        # Prepare the result
        result = {
            "success": len(unique_headlines) > 0,
            "headlines": unique_headlines,
            "sample_headlines": unique_headlines[:5] if unique_headlines else [],
            "sources": successful_sites,
            "topic": topic,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if not result["success"]:
            result["error"] = f"Could not gather headlines about {topic} from any of the provided websites."
        
        return result
    
    async def _validate_information_relevance(self, content: str, query: str) -> Dict[str, Any]:
        """
        Validate if the content contains information relevant to the query.
        
        Args:
            content: The content to validate
            query: The original query
            
        Returns:
            Dictionary with validation results
        """
        logger.info(f"Validating relevance of content for query: '{query}'")
        
        # Check if the content has clear indicators of relevant information
        query_terms = set(query.lower().split())
        content_lower = content.lower()
        
        # Extract the main topic from the query (usually the first 1-3 words)
        main_topic = ' '.join(query.split()[:3]).lower()
        
        # Check for direct mentions of the main topic
        topic_present = main_topic in content_lower
        
        # Check for direct mentions of query terms
        term_matches = sum(1 for term in query_terms if term in content_lower and len(term) > 3)
        
        # Check for specific information patterns (bullet points, facts, etc.)
        has_bullet_points = bool(re.search(r'[•\*\-]\s*[^\n\r]{10,}', content))
        has_numbered_lists = bool(re.search(r'\d+\.\s*[^\n\r]{10,}', content))
        has_specific_facts = bool(re.search(r'(?:in\s+\d{4}|\d{4}\s*-\s*\d{4}|\$\d+|\d+%)', content))
        
        # Check for limitations statement
        has_limitation_statement = "not available" in content_lower or "could not find" in content_lower or "no information" in content_lower or "no specific information" in content_lower
        
        # Check for unrelated content indicators
        has_unrelated_content = False
        if "this appears to be" in content_lower and not topic_present:
            has_unrelated_content = True
        
        # Make a determination based on the checks
        if has_unrelated_content:
            return {
                "is_relevant": False,
                "reason": "Content appears to be unrelated to the query topic"
            }
        elif has_limitation_statement:
            return {
                "is_relevant": False,
                "reason": "Content indicates information limitations"
            }
        elif not topic_present:
            return {
                "is_relevant": False,
                "reason": "Content does not mention the main topic of the query"
            }
        elif term_matches < 2:
            return {
                "is_relevant": False,
                "reason": "Content may not be specifically about the query topic"
            }
        elif not (has_bullet_points or has_numbered_lists or has_specific_facts):
            return {
                "is_relevant": False,
                "reason": "Content lacks specific facts or structured information"
            }
        elif topic_present and term_matches >= 2 and (has_bullet_points or has_numbered_lists or has_specific_facts):
            return {
                "is_relevant": True,
                "reason": "Content contains specific information related to the query"
            }
        else:
            return {
                "is_relevant": False,
                "reason": "Content may not provide sufficient information about the query topic"
            }
    
    async def analyze_search_results(self, websites: List[str], query: str) -> List[str]:
        """
        Analyze the list of potential websites and determine which ones are most likely to contain
        relevant information for the query.
        
        Args:
            websites: List of potential website URLs
            query: The search query
            
        Returns:
            List of prioritized websites to visit
        """
        logger.info(f"Analyzing {len(websites)} potential websites for query: '{query}'")
        
        if not websites:
            logger.warning("No websites to analyze")
            return []
            
        # If we only have a few websites, just return them all
        if len(websites) <= 3:
            logger.info("Few websites to analyze, returning all of them")
            return websites
        
        # Extract key terms from the query for better analysis
        key_terms_prompt = f"""
        Extract 3-5 key terms or concepts from this search query: "{query}"
        These terms should represent the most important aspects of what the user is looking for.
        Return ONLY a comma-separated list of terms, no explanations.
        """
        
        key_terms_response = await self._query_local_model(key_terms_prompt)
        key_terms = key_terms_response.strip()
        logger.info(f"Extracted key terms: {key_terms}")
        
        # Create initial categories of websites based on URL patterns
        official_sites = []
        news_sites = []
        reference_sites = []
        other_sites = []
        
        for url in websites:
            url_lower = url.lower()
            
            # Check for official/authoritative sites
            if any(domain in url_lower for domain in [".gov", ".edu", "official", "association", "org/"]):
                official_sites.append(url)
            # Check for news/media sites
            elif any(domain in url_lower for domain in ["news", "bbc", "cnn", "nyt", "reuters", "guardian", "times", "post", "wsj", "bloomberg"]):
                news_sites.append(url)
            # Check for reference sites
            elif any(domain in url_lower for domain in ["wikipedia", "britannica", "dictionary", "encyclopedia", "howto", "guide"]):
                reference_sites.append(url)
            # Other sites
            else:
                other_sites.append(url)
        
        # Use LLM to further analyze and prioritize websites
        analysis_prompt = f"""
        You are a search engine expert tasked with determining which websites are most likely to contain 
        accurate and relevant information for this query: "{query}"
        
        The key concepts in this query are: {key_terms}
        
        Here are the potential websites to visit, categorized:
        
        OFFICIAL SOURCES:
        {', '.join(official_sites) if official_sites else 'None'}
        
        NEWS SOURCES:
        {', '.join(news_sites) if news_sites else 'None'}
        
        REFERENCE SOURCES:
        {', '.join(reference_sites) if reference_sites else 'None'}
        
        OTHER SOURCES:
        {', '.join(other_sites) if other_sites else 'None'}
        
        Analyze these websites and select the most promising ones based on these criteria:
        - Authority and reliability (prefer well-known, established websites)
        - Specificity to the query (URLs that mention key terms from the query)
        - Recency (websites likely to contain up-to-date information)
        - Diversity (include different types of sources for a comprehensive view)
        
        Return a numbered list of 5-6 websites to visit, in order of priority, with the most promising websites first.
        Format your response as a simple numbered list with no additional text or explanations.
        Example:
        1. https://example.com/relevant-page
        2. https://another-site.org/useful-info
        ...
        """
        
        # Get the analysis from the LLM
        response = await self._query_local_model(analysis_prompt)
        
        # Extract the prioritized websites from the response
        prioritized_websites = []
        for line in response.strip().split('\n'):
            line = line.strip()
            # Look for lines that start with a number and contain a URL
            if re.match(r'^\d+\.\s*https?://', line):
                # Extract just the URL part
                url_match = re.search(r'(https?://[^\s]+)', line)
                if url_match:
                    url = url_match.group(1).rstrip('.,;')
                    
                    # Check if this URL is in the original list or starts with one of the original URLs
                    if url in websites:
                        prioritized_websites.append(url)
                    else:
                        # Find the closest match in the original list
                        for website in websites:
                            if url.startswith(website) or website.startswith(url):
                                if website not in prioritized_websites:
                                    prioritized_websites.append(website)
                                break
        
        # If we couldn't extract any websites, fall back to our category-based approach
        if not prioritized_websites:
            logger.warning("Could not extract prioritized websites from LLM response, using category-based prioritization")
            # Combine the categorized lists, taking up to 2 from each category to ensure diversity
            prioritized_websites = []
            for category in [official_sites, news_sites, reference_sites, other_sites]:
                prioritized_websites.extend(category[:2])
            
            # Deduplicate while preserving order
            seen = set()
            prioritized_websites = [x for x in prioritized_websites if not (x in seen or seen.add(x))]
        
        # Ensure we have a reasonable number of websites
        if len(prioritized_websites) > 6:
            prioritized_websites = prioritized_websites[:6]
        elif len(prioritized_websites) < 3 and len(websites) > 3:
            # Add more websites from the original list if we don't have enough
            for website in websites:
                if website not in prioritized_websites:
                    prioritized_websites.append(website)
                    if len(prioritized_websites) >= 5:
                        break
        
        logger.info(f"Prioritized {len(prioritized_websites)} websites: {prioritized_websites}")
        return prioritized_websites
    
    async def gather_information(self, websites: List[str], query: str) -> Dict[str, Any]:
        """
        Gather information from a list of websites based on a query.
        
        Args:
            websites: List of website URLs to gather information from
            query: The query to gather information about
            
        Returns:
            A dictionary containing the gathered information and metadata
        """
        logger.info(f"Gathering information about '{query}' from {len(websites)} websites")
        all_content = []
        successful_sites = []
        
        for url in websites:
            try:
                logger.info(f"Processing website: {url}")
                result = await self.browse_website(url)
                
                if not result.get("success", False):
                    logger.warning(f"Failed to browse website {url}: {result.get('error', 'Unknown error')}")
                    continue
                
                # Extract relevant content
                content = result.get('content', '')
                if content:
                    logger.info(f"Successfully extracted content from {url}, length: {len(content)} characters")
                    all_content.append({
                        "url": url,
                        "title": result.get('title', 'Unknown Title'),
                        "content": content[:5000]  # Limit content length
                    })
                    successful_sites.append(url)
                else:
                    logger.warning(f"No content extracted from {url}")
            except Exception as e:
                logger.error(f"Error gathering information from {url}: {e}")
        
        # If we have content, use the LLM to generate a response
        if all_content:
            logger.info(f"Successfully gathered content from {len(all_content)} websites for query: '{query}'")
            # Prepare the content for the prompt
            formatted_content = "\n\n".join([
                f"Source: {item['url']}\nTitle: {item['title']}\n{item['content']}"
                for item in all_content
            ])
            logger.info(f"Formatted content for LLM processing, total length: {len(formatted_content)} characters")
            
            # Structured information extraction prompt with clear steps
            prompt = f"""
            You are a research assistant tasked with gathering specific information about: {query}
            
            RESEARCH OBJECTIVE: Extract, analyze, and synthesize information SPECIFICALLY about {query} from the web content below.
            
            STEP 1: INFORMATION EXTRACTION
            - Carefully read through ALL the provided web content
            - Identify ONLY information specifically related to {query}
            - Extract facts, data, opinions, and details that directly answer the query
            - Pay special attention to dates, names, statistics, and specific details
            - IGNORE any content not directly related to {query}
            
            STEP 2: ANALYSIS & SYNTHESIS
            - Organize the extracted information into logical categories
            - Identify patterns, trends, or consensus across multiple sources
            - Note any contradictions or differing perspectives
            - Determine what information is most relevant and reliable
            
            STEP 3: RESPONSE FORMULATION
            Format your response with:
            1. A clear main heading: "Information about: {query}"
            2. Logical subheadings that organize the information
            3. Bullet points or numbered lists for key facts and details
            4. A concise conclusion summarizing the key findings
            5. A "Sources" section listing ALL websites referenced
            
            IMPORTANT GUIDELINES:
            - If the EXACT information about {query} is not available, CLEARLY STATE THIS at the beginning of your response
            - If no specific information about {query} is found, DO NOT provide general information about other topics
            - Instead, state: "No specific information about {query} was found in the provided sources."
            - DO NOT summarize unrelated content from the websites
            - Be SPECIFIC and DETAILED about {query} only - include names, dates, facts, and precise details
            - Do NOT make up or infer information not present in the content
            - ALWAYS include a "Sources" section with a numbered list of all websites used
            
            Web Content:
            {formatted_content}
            """
            
            logger.info("Sending prompt to LLM for information gathering...")
            response = await self._query_local_model(prompt)
            
            if response:
                logger.info(f"Received response from LLM, length: {len(response)} characters")
                
                # Validate if the response contains relevant information
                relevance_check = await self._validate_information_relevance(response, query)
                logger.info(f"Relevance check: {relevance_check}")
                
                # If the response doesn't contain relevant information, create a more helpful response
                if not relevance_check["is_relevant"]:
                    logger.warning(f"Response may not contain relevant information: {relevance_check['reason']}")
                    
                    # Check if the response already acknowledges limitations
                    has_limitation_acknowledgment = any(phrase in response.lower() for phrase in [
                        "limitation", "not available", "could not find", "no information", 
                        "no specific information", "was not found"
                    ])
                    
                    if not has_limitation_acknowledgment:
                        # Create a completely new response that's more helpful
                        new_response = f"""# Information about: {query}

No specific information about {query} was found in the provided sources.

The web search did not return relevant content specifically about {query}. This could be due to:

- The topic may be specialized or niche
- The selected websites may not cover this specific topic
- The information may exist but wasn't found in the current search

You may want to try:

1. Searching with more specific keywords
2. Checking specialized websites or forums related to {query}
3. Looking for academic or technical resources if this is a specialized topic

## Sources

The following sources were checked but did not contain specific information about {query}:

{chr(10).join([f'{i+1}. {url}' for i, url in enumerate(successful_sites)])}
"""
                        response = new_response
                
                # Extract a sample of information for UI display
                # Try to find bullet points or key information first
                sample_info = []
                logger.info("Extracting sample information from LLM response")
                
                # More generic patterns to extract useful information from any type of content
                info_patterns = [
                    # Bullet points (most common in structured responses)
                    r'[\n\r]\s*[•\-\*]\s*([^\n\r]{10,150})',
                    # Numbered points
                    r'[\n\r]\s*\d+\.\s*([^\n\r]{10,150})',
                    # Subheadings followed by text
                    r'[\n\r]#+\s*([^\n\r]{5,100})',
                    # Product mentions (for shopping/product queries)
                    r'[\n\r]([^\n\r]*?(?:recommend|best|top|popular|suggested)[^\n\r\.]{10,150})',
                    # Price information
                    r'[\n\r]([^\n\r]*?(?:\$|price|cost|value)[^\n\r\.]{10,150})',
                    # Any sentence with specific details (numbers, measurements, etc.)
                    r'[\n\r]([^\n\r]*?(?:\d+(?:\.\d+)?\s*(?:feet|ft|inches|in|cm|mm|pounds|lbs|kg|oz)[^\n\r\.]{10,150}))'
                ]
                
                # Try each pattern to extract useful information
                for pattern in info_patterns:
                    extracted_items = re.findall(pattern, response)
                    if extracted_items:
                        logger.info(f"Found {len(extracted_items)} items matching pattern")
                        for item in extracted_items[:3]:  # Get up to 3 items per pattern
                            clean_item = item.strip()
                            if clean_item and len(clean_item) > 10 and clean_item not in sample_info:
                                sample_info.append(clean_item)
                        if len(sample_info) >= 3:
                            break
                
                # Second priority: Look for bullet points (lines starting with * or -)
                if len(sample_info) < 3:
                    bullet_points = re.findall(r'[\n\r]([•\*\-]\s*[^\n\r]{10,100})', response)
                    if bullet_points:
                        logger.info(f"Found {len(bullet_points)} bullet points")
                        for point in bullet_points:
                            clean_point = point.strip()
                            if clean_point and clean_point not in sample_info:
                                sample_info.append(clean_point)
                            if len(sample_info) >= 3:
                                break
                
                # Third priority: Look for subheadings
                if len(sample_info) < 3:
                    headings = re.findall(r'[\n\r](#+\s*[^\n\r]{5,50}|[A-Z][^\n\r]{5,50}:)', response)
                    if headings:
                        logger.info(f"Found {len(headings)} headings")
                        for heading in headings:
                            clean_heading = heading.strip()
                            if clean_heading and clean_heading not in sample_info:
                                sample_info.append(clean_heading)
                            if len(sample_info) >= 3:
                                break
                
                # Last resort: Fall back to sentences
                if len(sample_info) < 3:
                    sentences = [s.strip() for s in response.split('.') if len(s.strip()) > 15 and len(s.strip()) < 100]
                    if sentences:
                        logger.info(f"Falling back to sentences, found {len(sentences)}")
                        for sentence in sentences:
                            if sentence and sentence not in sample_info:
                                sample_info.append(sentence)
                            if len(sample_info) >= 3:
                                break
                
                logger.info(f"Final sample info contains {len(sample_info)} items")
                
                # If we still don't have any sample info, extract the first few sentences as a fallback
                if not sample_info and response:
                    logger.info("No structured information found, using fallback extraction")
                    # Split by newlines first to try to get paragraph beginnings
                    lines = [line.strip() for line in response.split('\n') if line.strip()]
                    for line in lines[:5]:  # Check first 5 lines
                        if len(line) > 20 and line not in sample_info:  # Only add substantial lines
                            sample_info.append(line)
                        if len(sample_info) >= 3:
                            break
                    
                    # If still no sample info, try to extract sentences
                    if not sample_info:
                        sentences = re.findall(r'([^.!?]+[.!?])', response)
                        for sentence in sentences[:3]:
                            if len(sentence.strip()) > 20:
                                sample_info.append(sentence.strip())
                
                # If STILL no sample info, create a generic one
                if not sample_info:
                    sample_info = [f"Information gathered about {query} from {len(successful_sites)} websites."]
                
                # Split the content into paragraphs for the information field
                paragraphs = [p.strip() for p in response.split('\n\n') if p.strip()]
                
                # Ensure we have at least one paragraph
                if not paragraphs and response:
                    paragraphs = [response]
                
                # Ensure sources are included in the content
                if not any(marker in response.lower() for marker in ["sources:", "## sources", "# sources", "source list"]):
                    # If sources are not included, append them
                    sources_section = "\n\n## Sources\n\n"
                    for i, url in enumerate(successful_sites, 1):
                        sources_section += f"{i}. {url}\n"
                    response += sources_section
                    # Also add to paragraphs for the information field
                    paragraphs.append(sources_section)
                
                return {
                    "success": True,
                    "content": response,
                    "sample_information": sample_info,
                    "information": paragraphs,  # Add information field for agentic_assistant.py
                    "sources": successful_sites,
                    "query": query,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
        
        # Fallback if no content was gathered or LLM failed
        logger.error(f"Failed to gather or process information about '{query}'. Either no content was gathered or LLM processing failed.")
        return {
            "success": False,
            "error": f"Could not gather information about '{query}' from any of the provided websites.",
            "sample_information": [],
            "information": [],  # Add information field for agentic_assistant.py
            "sources": successful_sites,
            "query": query,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    async def determine_relevant_websites(self, query: str, category: str = None, max_sites: int = 5) -> List[str]:
        """
        Determine relevant websites for a given query and category.
        
        Args:
            query: The query to determine relevant websites for
            category: Optional category to help determine relevant websites
            max_sites: Maximum number of websites to return
            
        Returns:
            A list of relevant website URLs
        """
        # Define topic-specific website lists
        predefined_sites = {
            "news": [
                "https://www.bbc.com/news",
                "https://www.cnn.com",
                "https://www.theguardian.com",
                "https://apnews.com",
                "https://www.aljazeera.com"
            ],
            "gaming": [
                "https://www.ign.com",
                "https://www.gamespot.com",
                "https://www.polygon.com",
                "https://kotaku.com",
                "https://www.pcgamer.com"
            ],
            "tech": [
                "https://www.theverge.com",
                "https://techcrunch.com",
                "https://www.wired.com",
                "https://arstechnica.com",
                "https://www.cnet.com"
            ],
            "sports": [
                "https://www.espn.com",
                "https://sports.yahoo.com",
                "https://www.cbssports.com",
                "https://www.skysports.com",
                "https://www.sportingnews.com"
            ],
            "health": [
                "https://www.webmd.com",
                "https://www.mayoclinic.org",
                "https://www.healthline.com",
                "https://www.nih.gov",
                "https://www.medicalnewstoday.com"
            ],
            "finance": [
                "https://www.bloomberg.com",
                "https://www.cnbc.com",
                "https://www.forbes.com",
                "https://www.ft.com",
                "https://www.marketwatch.com"
            ],
            "fishing": [
                "https://www.takemefishing.org",
                "https://www.fieldandstream.com/fishing",
                "https://www.bassmaster.com",
                "https://www.fishingworld.com.au",
                "https://www.in-fisherman.com"
            ],
            "outdoor": [
                "https://www.outdoorlife.com",
                "https://www.backpacker.com",
                "https://www.outsideonline.com",
                "https://www.rei.com/learn",
                "https://www.adventure-journal.com"
            ],
            "gardening": [
                "https://www.gardeningknowhow.com",
                "https://www.thespruce.com/gardening-4127766",
                "https://www.almanac.com/gardening",
                "https://www.bhg.com/gardening",
                "https://www.gardeners.com/how-to"
            ],
            "cooking": [
                "https://www.allrecipes.com",
                "https://www.foodnetwork.com",
                "https://www.epicurious.com",
                "https://www.seriouseats.com",
                "https://www.bonappetit.com"
            ],
            "royalty": [
                "https://www.royal.uk",
                "https://www.townandcountrymag.com/society/tradition",
                "https://www.tatler.com/royals",
                "https://www.hellomagazine.com/royalty",
                "https://www.vanityfair.com/style/royals"
            ],
            "biographies": [
                "https://www.biography.com",
                "https://www.britannica.com/biography",
                "https://www.historynet.com",
                "https://www.notablebiographies.com",
                "https://www.famousbirthdays.com"
            ]
        }
        
        # Check if we have predefined sites for the category
        query_lower = query.lower()
        category_lower = category.lower() if category else ""
        
        # Simply check if the category matches any of our predefined categories
        # This makes the system rely more on intelligent category detection
        if category_lower in predefined_sites:
            return predefined_sites[category_lower][:max_sites]
        
        # For general queries or unknown categories, ask the LLM to suggest relevant websites
        logger.info(f"Using LLM to suggest websites for query: '{query}', category: '{category}'")
        
        # Use a more structured prompt to get better website suggestions
        analysis_prompt = f"""
        I need to gather CURRENT and FACTUAL information about: "{query}"
        Category: {category if category else 'unknown'}
        
        IMPORTANT: Suggest {max_sites} specific, high-quality websites that would have the MOST RELEVANT, CURRENT, and AUTHORITATIVE information on this EXACT topic.
        
        Your response should be in this format:
        CATEGORY: [brief category name like news, entertainment, technology, etc.]
        WEBSITES:
        https://www.example1.com
        https://www.example2.com
        https://www.example3.org
        https://www.example4.com
        https://www.example5.com
        
        IMPORTANT GUIDELINES:
        1. Include ONLY the full URL (with https://) and NO specific paths unless absolutely necessary
        2. Choose MAJOR, WELL-KNOWN websites that are most likely to have current information on this topic
        3. For entertainment topics, include sites like imdb.com, variety.com, hollywoodreporter.com
        4. For news, include major outlets like bbc.com, cnn.com, apnews.com
        5. For specialized topics, include the most authoritative industry-specific websites
        6. AVOID suggesting websites that might not exist or have limited content
        7. DO NOT include any social media sites unless they are the primary source for this information
        
        DO NOT include any explanations beyond the format specified above.
        """
        
        response = await self._query_local_model(analysis_prompt)
        
        # Extract category and URLs from the response
        category_match = re.search(r'CATEGORY:\s*([\w\s]+)', response)
        detected_category = category_match.group(1).strip().lower() if category_match else ""
        
        # Extract URLs from the response
        urls = re.findall(r'https?://[^\s"\'>]+', response)
        
        if urls and len(urls) > 0:
            logger.info(f"LLM suggested category: '{detected_category}' and {len(urls)} websites: {urls}")
            # Limit to max_sites
            return urls[:max_sites]
        
        # Try one more time with a simpler prompt
        logger.info(f"First attempt failed, trying simpler prompt for: '{query}'")
        simple_prompt = f"""
        What are the top {max_sites} websites for information about {query}?
        Just list the full URLs with https:// prefix, one per line.
        """
        
        simple_response = await self._query_local_model(simple_prompt)
        if simple_response:
            simple_urls = re.findall(r'https?://[^\s]+', simple_response)
            if simple_urls:
                logger.info(f"Second attempt found websites: {simple_urls}")
                return simple_urls[:max_sites]
        
        # Check if the LLM detected a category, and try to use predefined sites for that category
        if detected_category:
            logger.info(f"Checking if detected category '{detected_category}' matches any predefined categories")
            # Direct match
            if detected_category in predefined_sites:
                logger.info(f"Using predefined sites for detected category: '{detected_category}'")
                return predefined_sites[detected_category][:max_sites]
                
            # Check for partial matches
            for cat_name in predefined_sites.keys():
                if cat_name in detected_category or detected_category in cat_name:
                    logger.info(f"Found similar category in predefined sites: {cat_name}")
                    return predefined_sites[cat_name][:max_sites]
        
        # If we have a provided category, try to use predefined sites for similar categories
        if category_lower:
            logger.info(f"Looking for similar categories to: '{category_lower}'")
            # Check for similar categories
            similar_categories = []
            if any(word in category_lower for word in ["fish", "angl", "rod", "bait", "tackle"]):
                similar_categories.append("fishing")
                similar_categories.append("outdoor")
            elif any(word in category_lower for word in ["hike", "camp", "trek", "nature", "wilderness"]):
                similar_categories.append("outdoor")
            elif any(word in category_lower for word in ["health", "fitness", "exercise", "diet", "nutrition"]):
                similar_categories.append("health")
            elif any(word in category_lower for word in ["money", "invest", "stock", "market", "economy"]):
                similar_categories.append("finance")
            elif any(word in category_lower for word in ["queen", "king", "royal", "monarch", "prince", "princess"]):
                similar_categories.append("royalty")
                similar_categories.append("biographies")
            elif any(word in category_lower for word in ["garden", "plant", "flower", "vegetable", "soil"]):
                similar_categories.append("gardening")
            
            for similar_cat in similar_categories:
                if similar_cat in predefined_sites:
                    logger.info(f"Using predefined sites for similar category: '{similar_cat}'")
                    return predefined_sites[similar_cat][:max_sites]
        
        # Check query keywords as a last resort
        query_lower = query.lower()
        if any(word in query_lower for word in ["queen", "king", "royal", "monarch", "prince", "princess", "crown"]):
            logger.info("Query contains royalty keywords, using royalty websites")
            return predefined_sites["royalty"][:max_sites]
        
        # Ultimate fallback to a mix of general websites
        logger.info("All attempts failed, using general fallback websites")
        return [
            "https://en.wikipedia.org",
            "https://www.britannica.com",
            "https://www.nationalgeographic.com",
            "https://www.sciencedaily.com",
            "https://www.bbc.com"
        ][:max_sites]
    
    async def execute_web_task(self, task: str) -> Dict[str, Any]:
        """
        Execute a web-based task described in natural language.
        
        Args:
            task: The task to execute, described in natural language
            
        Returns:
            Dict containing the execution results
        """
        task_lower = task.lower()
        
        # Extract filename if specified
        filename = None
        
        # Try multiple patterns for filename extraction
        # Pattern 1: Quoted filename with .txt extension
        filename_match = re.search(r'[\'"](\w+\.txt)[\'"]', task_lower)
        
        # Pattern 2: File named pattern
        if not filename_match:
            filename_match = re.search(r'file\s+named\s+[\'"](\w+(?:\.\w+)?)[\'"]', task_lower)
        
        # Pattern 3: Save to pattern
        if not filename_match:
            filename_match = re.search(r'save\s+(?:to|in|as)\s+[\'"]?([^\'\"]+)[\'"]?', task_lower)
        
        if filename_match:
            filename = filename_match.group(1)
            # Add .txt extension if not present
            if '.' not in filename:
                filename += '.txt'
        
        # Information gathering tasks (news headlines, web research, etc.)
        if any(word in task_lower for word in ["gather", "collect", "get", "find", "search", "visit"]):
            # Extract the main topic from the task
            # First, try to identify predefined topics
            content_type = "general"
            
            # First, check for specific known topics directly in the task
            specific_topic = None
            
            # Pre-check for specific topics that we want to handle specially
            if any(word in task_lower for word in ["queen", "king", "royal", "monarch", "prince", "princess", "crown"]):
                logger.info("Detected royalty-related query")
                content_type = "royalty"
                # Extract the specific royal figure from the query
                royal_match = re.search(r'(queen|king|prince|princess)\s+(?:of\s+)?(\w+)', task_lower)
                if royal_match:
                    specific_topic = f"{royal_match.group(1)} of {royal_match.group(2)}"
                else:
                    specific_topic = "royal family"
                if not filename:
                    filename = "royalty_information.txt"
            
            elif any(word in task_lower for word in ["fishing", "rod", "angler", "bait", "tackle", "lure"]):
                logger.info("Detected fishing-related query")
                content_type = "fishing"
                # Set a default specific topic but we'll refine it later
                specific_topic = "fishing rods and equipment for beginners"
                if not filename:
                    filename = "fishing_guide.txt"
            
            elif any(word in task_lower for word in ["garden", "plant", "flower", "vegetable", "soil", "seed"]):
                logger.info("Detected gardening-related query")
                content_type = "gardening"
                if not filename:
                    filename = "gardening_guide.txt"
            
            elif any(word in task_lower for word in ["outdoor", "hiking", "camping", "backpacking", "wilderness"]):
                logger.info("Detected outdoor activity query")
                content_type = "outdoor"
                if not filename:
                    filename = "outdoor_guide.txt"
            
            elif any(word in task_lower for word in ["news", "headlines", "current events", "breaking"]):
                content_type = "news"
                specific_topic = "current news headlines"
                if not filename:
                    filename = "newsSummary.txt"
            
            elif any(term in task_lower for term in ["gaming", "games", "game", "gamer", "video game", "video games", "gamers", "playstation", "xbox", "nintendo", "steam"]):
                content_type = "gaming"
                specific_topic = "gaming news and updates"
                if not filename:
                    filename = "gameSummary.txt"
            
            elif any(word in task_lower for word in ["tech", "technology", "gadget", "apple", "google", "microsoft"]):
                content_type = "tech"
                specific_topic = "technology news and updates"
                if not filename:
                    filename = "techSummary.txt"
            
            # For general information gathering, extract the topic from the task
            if not specific_topic:
                # Use a more comprehensive prompt to extract the main topic and content type
                topic_prompt = f"""
                You are an AI assistant tasked with analyzing a user's information request.
                
                User request: {task}
                
                Please analyze this request and extract the following information:
                1. The main topic or subject - be as specific as possible (e.g., "fishing rods for beginners", "electric vehicles", "DSLR cameras for wildlife photography")
                2. The content category that best describes this topic - choose the most specific category possible
                
                For the category, consider these options but don't limit yourself to them:
                - fishing (for fishing-related topics)
                - outdoor (for hiking, camping, outdoor activities)
                - sports (for sports-related topics)
                - gaming (for video games, gaming hardware)
                - tech (for technology, gadgets, software)
                - health (for health, fitness, nutrition)
                - finance (for money, investing, economy)
                - news (for current events, headlines)
                - cooking (for recipes, food preparation)
                - travel (for destinations, travel tips)
                - education (for learning, courses)
                
                Respond in this exact format:
                Topic: [the specific topic]
                Category: [specific category]
                """
                
                topic_analysis = await self._query_local_model(topic_prompt)
                
                # Extract topic and category from the response
                topic_match = re.search(r'Topic:\s*(.+?)(?:\n|$)', topic_analysis)
                category_match = re.search(r'Category:\s*(.+?)(?:\n|$)', topic_analysis)
                
                specific_topic = topic_match.group(1).strip().lower() if topic_match else task.lower()
                content_type = category_match.group(1).strip().lower() if category_match else "general"
                
                # Default filename for general information
                if not filename:
                    # Create a filename based on the topic
                    topic_words = specific_topic.split()
                    if topic_words:
                        topic_filename = "_".join(topic_words[:3])  # Use first 3 words
                        filename = f"{topic_filename.replace(' ', '_')}_info.txt"
                    else:
                        filename = "information.txt"
            
            # Determine relevant websites based on the content type/category
            websites = await self.determine_relevant_websites(task, content_type)
            
            # For information gathering (we've removed the headline-specific path)
            # to make the system more intelligent and consistent
            logger.info(f"Processing general information gathering task: '{task}'")
            logger.info(f"Content type: {content_type}, Specific topic: {specific_topic}")
            
            # Gather information from the websites
            information_prompt = f"""
            You are a search engine optimization expert tasked with creating the most effective search query to find precise information about: {specific_topic or task}
            Content category: {content_type}
            
            Based on the user's request: "{task}"
            
            IMPORTANT GUIDELINES:
            1. Create a search query that will find CURRENT, FACTUAL, and SPECIFIC information about this topic
            2. DO NOT include site-specific operators (like site:) in your query
            3. DO include the current year (2025) for any time-sensitive topics to ensure up-to-date information
            4. Focus on terms that major authoritative websites would use in their content
            5. Include specific technical terms, proper nouns, and industry terminology when relevant
            6. Format the query for maximum relevance on major search engines
            7. Prioritize terms that would appear in titles and headings of relevant pages
            
            STRUCTURE YOUR QUERY WITH:
            - Primary topic/subject first
            - Specific attributes or qualifiers
            - Time frame indicators (2025, current, latest, etc.)
            - Content type indicators (guide, review, comparison, analysis, etc.)
            - Authority indicators (expert, official, research, etc.)
            
            EXAMPLES OF HIGHLY EFFECTIVE SEARCH QUERIES:
            - For entertainment: "top 10 highest-grossing actors 2025 box office rankings current data"
            - For products: "best premium fishing rods 2025 expert reviews comparison top brands specifications"
            - For technology: "latest flagship smartphone models 2025 features comparison battery life camera performance"
            - For health: "effective evidence-based weight loss strategies 2025 medical research clinical studies"
            - For finance: "stock market sector performance 2025 expert analysis trends predictions data"
            
            Respond with ONLY the optimized query text, no additional text or explanations.
            """
            
            specific_query = await self._query_local_model(information_prompt)
            specific_query = specific_query.strip()
            logger.info(f"Refined query: '{specific_query}'")
            
            # Use content_type as category when determining websites
            search_query = specific_query or specific_topic or task
            logger.info(f"Final search query: '{search_query}'")
            
            # Step 1: Get initial websites based on the content type
            logger.info(f"Step 1: Getting initial websites for query: '{search_query}'")
            initial_websites = await self.determine_relevant_websites(search_query, category=content_type, max_sites=8)
            
            # Step 2: Analyze and prioritize which websites to visit
            logger.info(f"Step 2: Analyzing and prioritizing websites for query: '{search_query}'")
            prioritized_websites = await self.analyze_search_results(initial_websites, search_query)
            logger.info(f"Prioritized {len(prioritized_websites)} websites for detailed examination")
            
            # Step 3: Gather information from the prioritized websites
            logger.info(f"Step 3: Gathering information from prioritized websites")
            result = await self.gather_information(prioritized_websites, search_query)
            
            # Step 4: If the first attempt failed or returned empty results, try a fallback approach
            if not result.get("success", False) or not result.get("content", ""):
                logger.warning(f"Initial attempt failed, trying fallback approach for: '{search_query}'")
                
                # Try with a more general search query
                fallback_prompt = f"""
                The search query "{search_query}" didn't yield useful results.
                Please create a more general version of this query that would work better on general knowledge websites.
                Focus on the core information need while removing any overly specific constraints.
                Return ONLY the revised query text, no explanations.
                """
                
                fallback_query = await self._query_local_model(fallback_prompt)
                fallback_query = fallback_query.strip()
                logger.info(f"Fallback query: '{fallback_query}'")
                
                # Use content-type specific fallback websites with expanded categories
                if content_type == "entertainment" or any(term in search_query.lower() for term in ["actor", "movie", "film", "tv", "television", "celebrity"]):
                    fallback_websites = [
                        "https://www.imdb.com",
                        "https://www.rottentomatoes.com",
                        "https://variety.com",
                        "https://www.hollywoodreporter.com",
                        "https://deadline.com",
                        "https://en.wikipedia.org/wiki/Portal:Film"
                    ]
                elif content_type == "news" or any(term in search_query.lower() for term in ["news", "current events", "headlines", "breaking"]):
                    fallback_websites = [
                        "https://www.reuters.com",
                        "https://apnews.com",
                        "https://www.bbc.com/news",
                        "https://www.aljazeera.com",
                        "https://www.npr.org",
                        "https://www.economist.com"
                    ]
                elif content_type == "tech" or any(term in search_query.lower() for term in ["technology", "smartphone", "computer", "gadget", "software", "ai", "artificial intelligence"]):
                    fallback_websites = [
                        "https://www.theverge.com",
                        "https://www.wired.com",
                        "https://techcrunch.com",
                        "https://arstechnica.com",
                        "https://www.cnet.com",
                        "https://www.technologyreview.com"
                    ]
                elif content_type == "sports" or any(term in search_query.lower() for term in ["sports", "football", "basketball", "baseball", "soccer", "nfl", "nba", "mlb", "nhl"]):
                    fallback_websites = [
                        "https://www.espn.com",
                        "https://www.sports-reference.com",
                        "https://www.cbssports.com",
                        "https://www.skysports.com",
                        "https://www.sportingnews.com",
                        "https://theathletic.com"
                    ]
                elif content_type == "health" or any(term in search_query.lower() for term in ["health", "medical", "disease", "treatment", "medicine", "fitness", "nutrition"]):
                    fallback_websites = [
                        "https://www.mayoclinic.org",
                        "https://www.nih.gov",
                        "https://www.webmd.com",
                        "https://www.healthline.com",
                        "https://medlineplus.gov",
                        "https://www.cdc.gov"
                    ]
                elif content_type == "finance" or any(term in search_query.lower() for term in ["finance", "money", "invest", "stock", "market", "economy", "financial"]):
                    fallback_websites = [
                        "https://www.bloomberg.com",
                        "https://www.ft.com",
                        "https://www.cnbc.com",
                        "https://www.investopedia.com",
                        "https://www.morningstar.com",
                        "https://www.wsj.com"
                    ]
                elif content_type == "travel" or any(term in search_query.lower() for term in ["travel", "vacation", "destination", "tourism", "hotel", "flight"]):
                    fallback_websites = [
                        "https://www.lonelyplanet.com",
                        "https://www.tripadvisor.com",
                        "https://www.nationalgeographic.com/travel",
                        "https://www.cntraveler.com",
                        "https://www.afar.com",
                        "https://www.fodors.com"
                    ]
                else:
                    # General fallback websites for any other category
                    fallback_websites = [
                        "https://en.wikipedia.org",
                        "https://www.britannica.com",
                        "https://www.nationalgeographic.com",
                        "https://www.smithsonianmag.com",
                        "https://time.com",
                        "https://www.reuters.com"
                    ]
                
                fallback_result = await self.gather_information(fallback_websites, fallback_query or search_query)
                
                # Use fallback result if it succeeded
                if fallback_result.get("success", False) and fallback_result.get("content", ""):
                    logger.info("Using fallback result")
                    result = fallback_result
            
            # Save the information to a file if requested
            if not filename:
                # Create a more descriptive filename based on content type and query
                query_words = search_query.split()[:3]  # Use first 3 words of query
                query_part = "_".join([w.lower() for w in query_words if len(w) > 2])
                
                if content_type == "fishing":
                    filename = f"fishing_guide_{query_part}.txt"
                elif content_type == "outdoor":
                    filename = f"outdoor_guide_{query_part}.txt"
                elif content_type == "tech":
                    filename = f"tech_guide_{query_part}.txt"
                elif content_type == "gaming":
                    filename = f"gaming_guide_{query_part}.txt"
                else:
                    filename = f"{content_type}_info_{query_part}.txt"
            
            # Make sure filename is valid
            filename = re.sub(r'[^\w\-_.]', '_', filename)
            
            file_path = os.path.join(self.documents_folder, filename)
            logger.info(f"Saving information to file: {file_path}")
            
            with open(file_path, "w") as f:
                content_to_save = result.get("content", "")
                if not content_to_save:
                    content_to_save = f"No information found about {search_query}. Please try a different query."
                
                # Check if sources are already included in the content
                sources = result.get("sources", [])
                if sources and "Sources:" not in content_to_save and "SOURCES:" not in content_to_save:
                    # Append sources section if not already present
                    content_to_save += "\n\n## Sources\n"
                    for i, source in enumerate(sources, 1):
                        content_to_save += f"\n{i}. {source}"
                
                f.write(content_to_save)
            
            result["filename"] = file_path
            
            result["task_type"] = f"{content_type}_information"
            return result
        
        # If we couldn't determine a specific task type, return an error
        return {
            "success": False,
            "error": "Could not determine a specific web task to execute.",
            "task_type": "general_web_task",
            "filename": filename,
            "sample_headlines": [],
            "sample_information": [],
            "headlines": [],
            "information": []
        }


async def handle_web_task(task: str) -> Dict[str, Any]:
    """
    Handle a web-based task using local resources.
    
    Args:
        task: Natural language description of the web task to execute
        
    Returns:
        Dict containing the execution results
    """
    logger.info(f"Handling web task: '{task}'")
    try:
        integration = LocalWebIntegration()
        logger.info("Initialized LocalWebIntegration, executing web task...")
        result = await integration.execute_web_task(task)
        logger.info(f"Web task execution result: success={result.get('success', False)}, task_type={result.get('task_type', 'unknown')}")
        
        # Ensure the result has all the fields that agentic_assistant.py expects
        if "task_type" not in result:
            # Try to determine task type from the task description
            task_lower = task.lower()
            
            # Extract the category from the result if available
            category = None
            if "_" in result.get("task_type", ""):
                category = result["task_type"].split("_")[0]
                
            # Set appropriate task_type based on content and task
            if any(word in task_lower for word in ["headline", "news", "current events"]):
                result["task_type"] = "news_headlines"
            elif any(term in task_lower for word in ["gaming", "games", "game", "gamer", "video game", "video games", "gamers"]):
                result["task_type"] = "gaming_headlines"
            elif any(word in task_lower for word in ["tech", "technology"]):
                result["task_type"] = "tech_headlines"
            elif category:
                # Use the category from the result
                result["task_type"] = f"{category}_information"
            else:
                # Try to extract a meaningful category from the task
                topic_match = re.search(r'(?:about|on|for)\s+([a-z]+)', task_lower)
                if topic_match:
                    result["task_type"] = f"{topic_match.group(1)}_information"
                else:
                    result["task_type"] = "general_information"
        
        # Ensure all required fields are present
        if "sample_headlines" not in result:
            result["sample_headlines"] = result.get("headlines", [])[:5] if result.get("headlines") else []
            
        if "sample_information" not in result:
            result["sample_information"] = result.get("information", [])[:3] if result.get("information") else []
            
        if "headlines" not in result:
            result["headlines"] = []
            
        if "information" not in result:
            result["information"] = []
            
        # Make sure the sample information is not empty
        if not result["sample_information"] and result.get("content"):
            # Extract some content as a fallback
            content = result["content"]
            sentences = [s.strip() for s in content.split(".") if len(s.strip()) > 15 and len(s.strip()) < 100]
            if sentences:
                result["sample_information"] = sentences[:3]
        
        return result
    except Exception as e:
        logger.error(f"Error handling web task: {e}")
        return {
            "success": False,
            "error": f"Web browsing failed: {str(e)}",
            "task_type": "general_information",
            "sample_headlines": [],
            "sample_information": [],
            "headlines": [],
            "information": [],
            "filename": None
        }
