#!/usr/bin/env python3
"""
Script to fix task management issues in the Enhanced Agentic Assistant.
This script addresses two main issues:
1. Filename extraction not working correctly
2. Web browsing tasks being incorrectly classified as file creation tasks
"""

import re
import os
import sys

def update_extract_filename_method(file_path):
    """Update the _extract_filename method to better handle filename extraction."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find the _extract_filename method
    extract_filename_pattern = r'def _extract_filename\(self, task_description: str\) -> str:.*?def _detect_content_type'
    extract_filename_match = re.search(extract_filename_pattern, content, re.DOTALL)
    
    if not extract_filename_match:
        print("Could not find _extract_filename method in the file.")
        return False
    
    # Get the original method
    original_method = extract_filename_match.group(0)
    
    # Create the updated method
    updated_method = '''def _extract_filename(self, task_description: str) -> str:
        """
        Extract the filename from a task description using multiple regex patterns.
        If no filename is found, generate a default one based on content type.
        
        Args:
            task_description: Description of the task
            
        Returns:
            Extracted or generated filename
        """
        logger.info(f"Extracting filename from: {task_description}")
        
        # Pattern 1: Named file pattern - "named/called [filename]" with or without quotes
        named_file_match = re.search(r'named\\s+["\']?([\\w\\-\\.\\s]+)["\']?', task_description, re.IGNORECASE)
        if named_file_match:
            filename = named_file_match.group(1).strip()
            # Add .txt extension if no extension is present
            if not re.search(r'\\.[a-zA-Z0-9]{2,4}$', filename):
                filename += ".txt"
            logger.info(f"Extracted filename using named pattern: {filename}")
            return filename
        
        # Pattern 2: "save it to/as/in [filename]" - standard pattern with or without quotes
        save_as_match = re.search(r'save\\s+(?:it|this|them|the\\s+\\w+)?\\s+(?:to|as|in)\\s+["\']?([\\w\\-\\.\\s]+)["\']?', task_description, re.IGNORECASE)
        if save_as_match:
            filename = save_as_match.group(1).strip()
            # Add .txt extension if no extension is present
            if not re.search(r'\\.[a-zA-Z0-9]{2,4}$', filename):
                filename += ".txt"
            logger.info(f"Extracted filename using save as pattern: {filename}")
            return filename
        
        # Pattern 3: "save to a file named/called [filename]" - with or without quotes
        save_named_match = re.search(r'save\\s+(?:to|in|as)?\\s+(?:a\\s+)?(?:file|document)\\s+(?:named|called)\\s+["\']?([\\w\\-\\.\\s]+)["\']?', task_description, re.IGNORECASE)
        if save_named_match:
            filename = save_named_match.group(1).strip()
            # Add .txt extension if no extension is present
            if not re.search(r'\\.[a-zA-Z0-9]{2,4}$', filename):
                filename += ".txt"
            logger.info(f"Extracted filename using save named pattern: {filename}")
            return filename
        
        # Pattern 4: "create/write a file named/called [filename]" - with or without quotes
        create_named_match = re.search(r'(?:create|write)\\s+(?:a\\s+)?(?:file|document)\\s+(?:named|called)\\s+["\']?([\\w\\-\\.\\s]+)["\']?', task_description, re.IGNORECASE)
        if create_named_match:
            filename = create_named_match.group(1).strip()
            # Add .txt extension if no extension is present
            if not re.search(r'\\.[a-zA-Z0-9]{2,4}$', filename):
                filename += ".txt"
            logger.info(f"Extracted filename using create named pattern: {filename}")
            return filename
        
        # Pattern 5: Look for any quoted text that might be a filename
        quoted_match = re.search(r'["\']([\\w\\-\\.\\s]+)["\']', task_description, re.IGNORECASE)
        if quoted_match:
            filename = quoted_match.group(1).strip()
            # Add .txt extension if no extension is present
            if not re.search(r'\\.[a-zA-Z0-9]{2,4}$', filename):
                filename += ".txt"
            logger.info(f"Extracted filename from quotes: {filename}")
            return filename
        
        # Pattern 6: Look for any word that ends with a file extension
        extension_match = re.search(r'\\b([\\w\\-\\.]+\\.[a-zA-Z0-9]{2,4})\\b', task_description, re.IGNORECASE)
        if extension_match:
            filename = extension_match.group(1).strip()
            logger.info(f"Extracted filename with extension: {filename}")
            return filename
        
        # Check for specific filename mentions without extensions
        filename_mention = re.search(r'\\bfile(?:\\s+named|\\s+called)?\\s+["\']?([\\w\\-\\s]+)["\']?', task_description, re.IGNORECASE)
        if filename_mention:
            filename = filename_mention.group(1).strip()
            # Add .txt extension if no extension is present
            if not re.search(r'\\.[a-zA-Z0-9]{2,4}$', filename):
                filename += ".txt"
            logger.info(f"Extracted filename from mention: {filename}")
            return filename
            
        # If no filename is found, generate a default one based on content type
        logger.info(f"No filename found in: {task_description}")
        content_type = self._detect_content_type(task_description)
        default_filename = f"{content_type}.txt"
        logger.info(f"No filename found, using default: {default_filename}")
        return default_filename
        
    def _detect_content_type'''
    
    # Replace the original method with the updated one
    updated_content = content.replace(original_method, updated_method)
    
    # Write the updated content back to the file
    with open(file_path, 'w') as f:
        f.write(updated_content)
    
    print("Successfully updated _extract_filename method.")
    return True

def update_is_direct_file_creation_task(file_path):
    """Update the _is_direct_file_creation_task method to better handle web browsing tasks."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find the _is_direct_file_creation_task method
    is_direct_file_creation_pattern = r'def _is_direct_file_creation_task\(self, task_description: str\) -> bool:.*?return False'
    is_direct_file_creation_match = re.search(is_direct_file_creation_pattern, content, re.DOTALL)
    
    if not is_direct_file_creation_match:
        print("Could not find _is_direct_file_creation_task method in the file.")
        return False
    
    # Get the original method
    original_method = is_direct_file_creation_match.group(0)
    
    # Create the updated method with better web task detection
    updated_method = '''def _is_direct_file_creation_task(self, task_description: str) -> bool:
        """
        Determine if a task is a direct file creation task that should be handled directly.
        
        Args:
            task_description: Description of the task
            
        Returns:
            True if the task is a direct file creation task, False otherwise
        """
        # Check for explicit web browsing tasks first
        # If the task contains a URL, it's likely a web browsing task
        url_pattern = r'https?://[\\w\\-\\.]+\\.[a-zA-Z]{2,}(?:/[\\w\\-\\.]*)*'
        if re.search(url_pattern, task_description, re.IGNORECASE):
            # But if it also mentions saving to a file, it might be a complex task
            if any(term in task_description.lower() for term in ["save", "write", "store", "create file"]):
                # This is a complex web browsing task with file output
                logger.info(f"Detected web browsing task with file output: '{task_description}'")
                return False
            # Pure web browsing task
            logger.info(f"Detected pure web browsing task with URL: '{task_description}'")
            return False
        
        # Check for explicit web search tasks
        web_search_patterns = [
            r"search\\s+(?:for|about)\\s+[\\w\\s]+\\s+(?:on|using)\\s+(?:the\\s+)?(?:web|internet|google|bing|yahoo)",
            r"(?:find|get|look\\s+up)\\s+(?:information|data|content|details|news)\\s+(?:about|on|regarding)\\s+[\\w\\s]+\\s+(?:on|from)\\s+(?:the\\s+)?(?:web|internet|online)",
            r"(?:browse|visit|go\\s+to)\\s+(?:the\\s+)?(?:web|internet|website|site|page)",
            r"(?:analyze|check|read|view)\\s+(?:the\\s+)?(?:headlines|news|content|articles)\\s+(?:on|from|at)\\s+[\\w\\s\\.]+\\.com"
        ]
        
        for pattern in web_search_patterns:
            if re.search(pattern, task_description, re.IGNORECASE):
                logger.info(f"Detected web search task: '{task_description}'")
                return False
        
        # Pattern 1: Create a file/document with...
        pattern1 = r"create\\s+(?:a|an)\\s+(?:file|document|text|story|poem|essay|article|report|note|analysis|summary|list)\\s+(?:with|about|for|containing|of|on)"
        if re.search(pattern1, task_description, re.IGNORECASE):
            logger.info(f"Detected direct file creation task: '{task_description}'. Handling directly.")
            return True
        
        # Pattern 2: Write a story/poem/essay...
        pattern2 = r"write\\s+(?:a|an|the)\\s+(?:story|poem|essay|article|report|note|text|document|analysis|summary|list)"
        if re.search(pattern2, task_description, re.IGNORECASE):
            logger.info(f"Detected direct file creation task: '{task_description}'. Handling directly.")
            return True
        
        # Pattern 3: Save as filename...
        pattern3 = r"save\\s+(?:it|this|the\\s+file|the\\s+document|the\\s+content|the\\s+result|the\\s+output|that|the\\s+analysis|the\\s+summary)\\s+(?:as|to|in)\\s+([\\w\\-\\.\\s/]+)"
        if re.search(pattern3, task_description, re.IGNORECASE):
            logger.info(f"Detected direct file creation task with save pattern: '{task_description}'. Handling directly.")
            return True
        
        # Pattern 4: Create a file named/called...
        pattern4 = r"(?:create|make|write)\\s+(?:a|an|the)\\s+(?:file|document)\\s+(?:named|called)"
        if re.search(pattern4, task_description, re.IGNORECASE):
            logger.info(f"Detected direct file creation task with named file: '{task_description}'. Handling directly.")
            return True
        
        # Pattern 5: Save to folder or file...
        pattern5 = r"save\\s+(?:it|this|that|the\\s+content|the\\s+result|the\\s+output)?\\s+(?:to|in)\\s+(?:my\\s+)?(?:[\\w\\s]+\\s+)?(?:folder|directory|file|document)\\s+(?:as|named|called)?\\s*"
        if re.search(pattern5, task_description, re.IGNORECASE):
            logger.info(f"Detected direct file creation task with folder/file path: '{task_description}'. Handling directly.")
            return True
        
        # Pattern 6: Look for quoted filenames or filenames with extensions
        pattern6 = r'(?:["\']+[\\w\\-\\.\\s]+\\.[\\w]+["\']+|\\b[\\w\\-\\.]+\\.[a-zA-Z0-9]{2,4}\\b)' 
        if re.search(pattern6, task_description, re.IGNORECASE) and any(term in task_description.lower() for term in ["create", "write", "save", "store", "output", "generate"]):
            logger.info(f"Detected direct file creation task with filename: '{task_description}'. Handling directly.")
            return True
            
        # Pattern 7: Compile/analyze/summarize and save
        pattern7 = r"(?:compile|analyze|summarize)\\s+(?:[\\w\\s]+)\\s+(?:and|then)\\s+(?:save|store|write|output)"
        if re.search(pattern7, task_description, re.IGNORECASE):
            logger.info(f"Detected direct file creation task with compilation: '{task_description}'. Handling directly.")
            return True
            
        # Pattern 8: File named/called pattern
        pattern8 = r"(?:file|document|text)\\s+(?:named|called)\\s+['\"]?([\\w\\s\\.\\-]+)['\"]?"
        if re.search(pattern8, task_description, re.IGNORECASE):
            logger.info(f"Detected direct file creation task with named file: '{task_description}'. Handling directly.")
            return True
            
        # Pattern 9: Complex pattern for search and save
        pattern9 = r"(?:search|find|look\\s+for|research|get\\s+information\\s+about)\\s+(?:[\\w\\s\\d\\-\\+]+)\\s+(?:and|then)\\s+(?:save|store|write|create)\\s+(?:it|that|them|the\\s+results?|the\\s+information|a\\s+file|a\\s+document)"
        if re.search(pattern9, task_description, re.IGNORECASE):
            # Check if this is actually a web search task
            web_terms = ["web", "internet", "online", "website", "site", "page", "browser", "chrome", "firefox", "safari", "edge"]
            if any(term in task_description.lower() for term in web_terms):
                logger.info(f"Detected web search task with file output: '{task_description}'")
                return False
            logger.info(f"Detected complex file creation task with search and save: '{task_description}'. Handling directly.")
            return True
            
        # Pattern 10: Search for X and save to file Y
        pattern10 = r"(?:search|find|look\\s+for|research|get\\s+information\\s+about)\\s+(?:[\\w\\s\\d\\-\\+]+)\\s+(?:and|then)\\s+(?:save|store|write)\\s+(?:it|that|them|the\\s+results?|the\\s+information)\\s+(?:to|in|as)\\s+(?:a\\s+)?(?:file|document)\\s+(?:named|called)?\\s+['\"]?([\\w\\s\\.\\-]+)['\"]?"
        if re.search(pattern10, task_description, re.IGNORECASE):
            # Check if this is actually a web search task
            web_terms = ["web", "internet", "online", "website", "site", "page", "browser", "chrome", "firefox", "safari", "edge"]
            if any(term in task_description.lower() for term in web_terms):
                logger.info(f"Detected web search task with file output: '{task_description}'")
                return False
            logger.info(f"Detected complex file creation task with search and named file: '{task_description}'. Handling directly.")
            return True
            
        # Pattern 11: Generate/create X based on search/web results
        pattern11 = r"(?:generate|create|write|make|prepare)\\s+(?:a|an|the)\\s+(?:summary|report|analysis|document|file|list|compilation)\\s+(?:of|about|on|for)\\s+(?:[\\w\\s\\d\\-\\+]+)\\s+(?:based\\s+on|using|from|with)\\s+(?:search|web|internet|online)\\s+(?:results|information|data|content)"
        if re.search(pattern11, task_description, re.IGNORECASE):
            logger.info(f"Detected complex file creation task with web research: '{task_description}'. Handling directly.")
            return False  # Changed to False to ensure web browsing is used
            
        # Pattern 12: Find information and create a document
        pattern12 = r"(?:find|get|gather|collect)\\s+(?:information|data|content|details)\\s+(?:about|on|for)\\s+(?:[\\w\\s\\d\\-\\+]+)\\s+(?:and|then)\\s+(?:create|write|prepare|make)\\s+(?:a|an|the)\\s+(?:summary|report|analysis|document|file)"
        if re.search(pattern12, task_description, re.IGNORECASE):
            # Check if this is actually a web search task
            web_terms = ["web", "internet", "online", "website", "site", "page", "browser", "chrome", "firefox", "safari", "edge"]
            if any(term in task_description.lower() for term in web_terms):
                logger.info(f"Detected web search task with file output: '{task_description}'")
                return False
            logger.info(f"Detected complex file creation task with information gathering: '{task_description}'. Handling directly.")
            return True
            
        # Pattern 13: Summarize web content
        pattern13 = r"(?:summarize|analyze|extract)\\s+(?:information|data|content|details)\\s+(?:from|about|on)\\s+(?:[\\w\\s\\d\\-\\+]+)\\s+(?:and|then)?\\s+(?:save|write|create|put\\s+it\\s+in)\\s+(?:a|an|the)?\\s+(?:file|document|summary|report)"
        if re.search(pattern13, task_description, re.IGNORECASE):
            # Check if this is actually a web search task
            web_terms = ["web", "internet", "online", "website", "site", "page", "browser", "chrome", "firefox", "safari", "edge"]
            if any(term in task_description.lower() for term in web_terms) or ".com" in task_description:
                logger.info(f"Detected web content summarization task: '{task_description}'")
                return False
            logger.info(f"Detected complex file creation task with content summarization: '{task_description}'. Handling directly.")
            return True
        
        # Fallback pattern: If it contains create/write/save and doesn't look like a web search
        web_patterns = [r"search", r"find", r"look\\s+up", r"browse", r"internet", r"web", r"online", r"information about", r"articles on"]
        has_web_term = any(re.search(p, task_description, re.IGNORECASE) for p in web_patterns)
        
        # Check for file creation terms
        file_creation_terms = ["create", "write", "save", "store", "output", "generate", "compile", "summarize", "analyze", "extract"]
        has_file_creation_term = any(term in task_description.lower() for term in file_creation_terms)
        
        # Check for content type terms that suggest file creation
        content_type_terms = ["story", "poem", "essay", "article", "report", "note", "text", "document", "analysis", 
                              "summary", "list", "compilation", "collection", "information", "data", "content", "details"]
        has_content_type_term = any(term in task_description.lower() for term in content_type_terms)
        
        # Check for output file terms
        output_file_terms = ["file", "document", "txt", "output", "save as", "save to", "write to", "report", "summary", "analysis"]
        has_output_file_term = any(term in task_description.lower() for term in output_file_terms)
        
        # Check for terms that suggest the task is about creating a document from web content
        web_to_file_terms = ["based on search", "from web", "from the internet", "from online", "using search results", 
                             "from search results", "search and save", "find and save", "research and write", 
                             "look up and create", "search and create"]
        has_web_to_file_term = any(term in task_description.lower() for term in web_to_file_terms)
        
        # Special case 1: If the task has both web terms AND file creation terms with output file terms,
        # it's likely a complex task that should be handled as file creation
        if has_web_term and has_file_creation_term and has_output_file_term:
            # Check for domain names or URLs which would indicate web browsing
            domain_pattern = r'\\b[\\w\\-]+\\.[a-zA-Z]{2,}\\b'
            if re.search(domain_pattern, task_description, re.IGNORECASE):
                logger.info(f"Detected web browsing task with domain and file output: '{task_description}'")
                return False
            logger.info(f"Detected complex file creation task with web research and file output: '{task_description}'. Handling directly.")
            return True
        
        # Special case 2: If the task has terms suggesting web-to-file workflow
        if has_web_to_file_term:
            logger.info(f"Detected web-to-file workflow task: '{task_description}'")
            return False
        
        # Special case 3: If it has file creation terms and content type terms but no web terms
        if (has_file_creation_term and has_content_type_term) and not has_web_term:
            logger.info(f"Detected file creation task via fallback: '{task_description}'. Handling directly.")
            return True
        
        # Special case 4: If it has both file creation terms and output file terms
        if has_file_creation_term and has_output_file_term:
            logger.info(f"Detected file creation task with explicit output terms: '{task_description}'. Handling directly.")
            return True
        
        return False'''
    
    # Replace the original method with the updated one
    updated_content = content.replace(original_method, updated_method)
    
    # Write the updated content back to the file
    with open(file_path, 'w') as f:
        f.write(updated_content)
    
    print("Successfully updated _is_direct_file_creation_task method.")
    return True

def main():
    """Main function to update the Enhanced Agentic Assistant."""
    file_path = '/Users/christopher.bradford/ollamaShell/agentic_assistant_enhanced.py'
    
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} does not exist.")
        return 1
    
    # Make a backup of the original file
    backup_path = f"{file_path}.bak"
    with open(file_path, 'r') as src, open(backup_path, 'w') as dst:
        dst.write(src.read())
    print(f"Created backup at {backup_path}")
    
    # Update the methods
    success1 = update_extract_filename_method(file_path)
    success2 = update_is_direct_file_creation_task(file_path)
    
    if success1 and success2:
        print("Successfully updated the Enhanced Agentic Assistant.")
        print("The following issues have been fixed:")
        print("1. Improved filename extraction to handle more patterns")
        print("2. Better detection of web browsing tasks vs. file creation tasks")
        print("3. Added support for detecting domain names and URLs")
        print("4. Enhanced handling of complex tasks that involve both web browsing and file creation")
        return 0
    else:
        print("Failed to update one or more methods.")
        print("Restoring from backup...")
        with open(backup_path, 'r') as src, open(file_path, 'w') as dst:
            dst.write(src.read())
        print("Restored from backup.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
