#!/usr/bin/env python3
"""
Script to safely fix task management issues in the Enhanced Agentic Assistant.
This script addresses two main issues:
1. Filename extraction not working correctly
2. Web browsing tasks being incorrectly classified as file creation tasks
"""

import os
import sys
import re
from pathlib import Path

def update_extract_filename_method(file_path):
    """Update the _extract_filename method to better handle filename extraction."""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Find the start and end of the _extract_filename method
    start_line = -1
    end_line = -1
    
    for i, line in enumerate(lines):
        if "def _extract_filename(self, task_description: str) -> str:" in line:
            start_line = i
        elif start_line != -1 and "def _detect_content_type" in line:
            end_line = i
            break
    
    if start_line == -1 or end_line == -1:
        print("Could not find _extract_filename method in the file.")
        return False
    
    # Create the updated method
    updated_method = [
        "    def _extract_filename(self, task_description: str) -> str:\n",
        '        """\n',
        "        Extract the filename from a task description using multiple regex patterns.\n",
        "        If no filename is found, generate a default one based on content type.\n",
        "        \n",
        "        Args:\n",
        "            task_description: Description of the task\n",
        "            \n",
        "        Returns:\n",
        "            Extracted or generated filename\n",
        '        """\n',
        '        logger.info(f"Extracting filename from: {task_description}")\n',
        "        \n",
        '        # Pattern 1: Named file pattern - "named/called [filename]" with or without quotes\n',
        '        named_file_match = re.search(r\'named\\s+["\\\'"]?([\\w\\-\\.\\s]+)["\\\'"]?\', task_description, re.IGNORECASE)\n',
        "        if named_file_match:\n",
        "            filename = named_file_match.group(1).strip()\n",
        "            # Add .txt extension if no extension is present\n",
        '            if not re.search(r\'\\.\\w{2,4}$\', filename):\n',
        '                filename += ".txt"\n',
        '            logger.info(f"Extracted filename using named pattern: {filename}")\n',
        "            return filename\n",
        "        \n",
        '        # Pattern 2: "save it to/as/in [filename]" - standard pattern with or without quotes\n',
        '        save_as_match = re.search(r\'save\\s+(?:it|this|them|the\\s+\\w+)?\\s+(?:to|as|in)\\s+["\\\'"]?([\\w\\-\\.\\s]+)["\\\'"]?\', task_description, re.IGNORECASE)\n',
        "        if save_as_match:\n",
        "            filename = save_as_match.group(1).strip()\n",
        "            # Add .txt extension if no extension is present\n",
        '            if not re.search(r\'\\.\\w{2,4}$\', filename):\n',
        '                filename += ".txt"\n',
        '            logger.info(f"Extracted filename using save as pattern: {filename}")\n',
        "            return filename\n",
        "        \n",
        '        # Pattern 3: "save to a file named/called [filename]" - with or without quotes\n',
        '        save_named_match = re.search(r\'save\\s+(?:to|in|as)?\\s+(?:a\\s+)?(?:file|document)\\s+(?:named|called)\\s+["\\\'"]?([\\w\\-\\.\\s]+)["\\\'"]?\', task_description, re.IGNORECASE)\n',
        "        if save_named_match:\n",
        "            filename = save_named_match.group(1).strip()\n",
        "            # Add .txt extension if no extension is present\n",
        '            if not re.search(r\'\\.\\w{2,4}$\', filename):\n',
        '                filename += ".txt"\n',
        '            logger.info(f"Extracted filename using save named pattern: {filename}")\n',
        "            return filename\n",
        "        \n",
        '        # Pattern 4: "create/write a file named/called [filename]" - with or without quotes\n',
        '        create_named_match = re.search(r\'(?:create|write)\\s+(?:a\\s+)?(?:file|document)\\s+(?:named|called)\\s+["\\\'"]?([\\w\\-\\.\\s]+)["\\\'"]?\', task_description, re.IGNORECASE)\n',
        "        if create_named_match:\n",
        "            filename = create_named_match.group(1).strip()\n",
        "            # Add .txt extension if no extension is present\n",
        '            if not re.search(r\'\\.\\w{2,4}$\', filename):\n',
        '                filename += ".txt"\n',
        '            logger.info(f"Extracted filename using create named pattern: {filename}")\n',
        "            return filename\n",
        "        \n",
        '        # Pattern 5: Look for any quoted text that might be a filename\n',
        '        quoted_match = re.search(r\'["\\\'"]([\\w\\-\\.\\s]+)["\\\'"]?\', task_description, re.IGNORECASE)\n',
        "        if quoted_match:\n",
        "            filename = quoted_match.group(1).strip()\n",
        "            # Add .txt extension if no extension is present\n",
        '            if not re.search(r\'\\.\\w{2,4}$\', filename):\n',
        '                filename += ".txt"\n',
        '            logger.info(f"Extracted filename from quotes: {filename}")\n',
        "            return filename\n",
        "        \n",
        '        # Pattern 6: Look for any word that ends with a file extension\n',
        '        extension_match = re.search(r\'\\b([\\w\\-\\.]+\\.\\w{2,4})\\b\', task_description, re.IGNORECASE)\n',
        "        if extension_match:\n",
        "            filename = extension_match.group(1).strip()\n",
        '            logger.info(f"Extracted filename with extension: {filename}")\n',
        "            return filename\n",
        "        \n",
        '        # Check for specific filename mentions without extensions\n',
        '        filename_mention = re.search(r\'\\bfile(?:\\s+named|\\s+called)?\\s+["\\\'"]?([\\w\\-\\s]+)["\\\'"]?\', task_description, re.IGNORECASE)\n',
        "        if filename_mention:\n",
        "            filename = filename_mention.group(1).strip()\n",
        "            # Add .txt extension if no extension is present\n",
        '            if not re.search(r\'\\.\\w{2,4}$\', filename):\n',
        '                filename += ".txt"\n',
        '            logger.info(f"Extracted filename from mention: {filename}")\n',
        "            return filename\n",
        "        \n",
        '        # If no filename is found, generate a default one based on content type\n',
        '        logger.info(f"No filename found in: {task_description}")\n',
        "        content_type = self._detect_content_type(task_description)\n",
        '        default_filename = f"{content_type}.txt"\n',
        '        logger.info(f"No filename found, using default: {default_filename}")\n',
        "        return default_filename\n",
    ]
    
    # Replace the original method with the updated one
    new_lines = lines[:start_line] + updated_method + lines[end_line:]
    
    # Write the updated content back to the file
    with open(file_path, 'w') as f:
        f.writelines(new_lines)
    
    print("Successfully updated _extract_filename method.")
    return True

def update_is_direct_file_creation_task(file_path):
    """Update the _is_direct_file_creation_task method to better handle web browsing tasks."""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Find the start and end of the _is_direct_file_creation_task method
    start_line = -1
    end_line = -1
    
    for i, line in enumerate(lines):
        if "def _is_direct_file_creation_task(self, task_description: str) -> bool:" in line:
            start_line = i
        elif start_line != -1 and "return False" in line and i > start_line + 5:
            # Find the end of the method (the last return False)
            for j in range(i+1, len(lines)):
                if lines[j].strip().startswith("def "):
                    end_line = j
                    break
            if end_line == -1:  # If we didn't find another method, use the next line
                end_line = i + 1
            break
    
    if start_line == -1 or end_line == -1:
        print("Could not find _is_direct_file_creation_task method in the file.")
        return False
    
    # Create the updated method
    updated_method = [
        "    def _is_direct_file_creation_task(self, task_description: str) -> bool:\n",
        '        """\n',
        "        Determine if a task is a direct file creation task that should be handled directly.\n",
        "        \n",
        "        Args:\n",
        "            task_description: Description of the task\n",
        "            \n",
        "        Returns:\n",
        "            True if the task is a direct file creation task, False otherwise\n",
        '        """\n',
        "        # Check for explicit web browsing tasks first\n",
        "        # If the task contains a URL, it's likely a web browsing task\n",
        '        url_pattern = r\'https?://[\\w\\-\\.]+\\.[a-zA-Z]{2,}(?:/[\\w\\-\\.]*)*\'\n',
        "        if re.search(url_pattern, task_description, re.IGNORECASE):\n",
        "            # But if it also mentions saving to a file, it might be a complex task\n",
        '            if any(term in task_description.lower() for term in ["save", "write", "store", "create file"]):\n',
        "                # This is a complex web browsing task with file output\n",
        '                logger.info(f"Detected web browsing task with file output: \'{task_description}\'")\n',
        "                return False\n",
        "            # Pure web browsing task\n",
        '            logger.info(f"Detected pure web browsing task with URL: \'{task_description}\'")\n',
        "            return False\n",
        "        \n",
        "        # Check for explicit web search tasks\n",
        "        web_search_patterns = [\n",
        '            r"search\\s+(?:for|about)\\s+[\\w\\s]+\\s+(?:on|using)\\s+(?:the\\s+)?(?:web|internet|google|bing|yahoo)",\n',
        '            r"(?:find|get|look\\s+up)\\s+(?:information|data|content|details|news)\\s+(?:about|on|regarding)\\s+[\\w\\s]+\\s+(?:on|from)\\s+(?:the\\s+)?(?:web|internet|online)",\n',
        '            r"(?:browse|visit|go\\s+to)\\s+(?:the\\s+)?(?:web|internet|website|site|page)",\n',
        '            r"(?:analyze|check|read|view)\\s+(?:the\\s+)?(?:headlines|news|content|articles)\\s+(?:on|from|at)\\s+[\\w\\s\\.]+\\.com"\n',
        "        ]\n",
        "        \n",
        "        for pattern in web_search_patterns:\n",
        "            if re.search(pattern, task_description, re.IGNORECASE):\n",
        '                logger.info(f"Detected web search task: \'{task_description}\'")\n',
        "                return False\n",
        "        \n",
        "        # Pattern 1: Create a file/document with...\n",
        '        pattern1 = r"create\\s+(?:a|an)\\s+(?:file|document|text|story|poem|essay|article|report|note|analysis|summary|list)\\s+(?:with|about|for|containing|of|on)"\n',
        "        if re.search(pattern1, task_description, re.IGNORECASE):\n",
        '            logger.info(f"Detected direct file creation task: \'{task_description}\'. Handling directly.")\n',
        "            return True\n",
        "        \n",
        "        # Pattern 2: Write a story/poem/essay...\n",
        '        pattern2 = r"write\\s+(?:a|an|the)\\s+(?:story|poem|essay|article|report|note|text|document|analysis|summary|list)"\n',
        "        if re.search(pattern2, task_description, re.IGNORECASE):\n",
        '            logger.info(f"Detected direct file creation task: \'{task_description}\'. Handling directly.")\n',
        "            return True\n",
        "        \n",
        "        # Pattern 3: Save as filename...\n",
        '        pattern3 = r"save\\s+(?:it|this|the\\s+file|the\\s+document|the\\s+content|the\\s+result|the\\s+output|that|the\\s+analysis|the\\s+summary)\\s+(?:as|to|in)\\s+([\\w\\-\\.\\s/]+)"\n',
        "        if re.search(pattern3, task_description, re.IGNORECASE):\n",
        '            logger.info(f"Detected direct file creation task with save pattern: \'{task_description}\'. Handling directly.")\n',
        "            return True\n",
        "        \n",
        "        # Pattern 4: Create a file named/called...\n",
        '        pattern4 = r"(?:create|make|write)\\s+(?:a|an|the)\\s+(?:file|document)\\s+(?:named|called)"\n',
        "        if re.search(pattern4, task_description, re.IGNORECASE):\n",
        '            logger.info(f"Detected direct file creation task with named file: \'{task_description}\'. Handling directly.")\n',
        "            return True\n",
        "        \n",
        "        # Pattern 5: Save to folder or file...\n",
        '        pattern5 = r"save\\s+(?:it|this|that|the\\s+content|the\\s+result|the\\s+output)?\\s+(?:to|in)\\s+(?:my\\s+)?(?:[\\w\\s]+\\s+)?(?:folder|directory|file|document)\\s+(?:as|named|called)?\\s*"\n',
        "        if re.search(pattern5, task_description, re.IGNORECASE):\n",
        '            logger.info(f"Detected direct file creation task with folder/file path: \'{task_description}\'. Handling directly.")\n',
        "            return True\n",
        "        \n",
        "        # Pattern 6: Look for quoted filenames or filenames with extensions\n",
        '        pattern6 = r\'(?:["\'"][\\w\\-\\.\\s]+\\.[\\w]+["\'"]|\\b[\\w\\-\\.]+\\.[a-zA-Z0-9]{2,4}\\b)\'\n',
        '        if re.search(pattern6, task_description, re.IGNORECASE) and any(term in task_description.lower() for term in ["create", "write", "save", "store", "output", "generate"]):\n',
        '            logger.info(f"Detected direct file creation task with filename: \'{task_description}\'. Handling directly.")\n',
        "            return True\n",
        "        \n",
        "        # Pattern 7: Compile/analyze/summarize and save\n",
        '        pattern7 = r"(?:compile|analyze|summarize)\\s+(?:[\\w\\s]+)\\s+(?:and|then)\\s+(?:save|store|write|output)"\n',
        "        if re.search(pattern7, task_description, re.IGNORECASE):\n",
        '            logger.info(f"Detected direct file creation task with compilation: \'{task_description}\'. Handling directly.")\n',
        "            return True\n",
        "        \n",
        "        # Pattern 8: File named/called pattern\n",
        '        pattern8 = r"(?:file|document|text)\\s+(?:named|called)\\s+[\'\\"]?([\\w\\s\\.\\-]+)[\'\\"]?"\n',
        "        if re.search(pattern8, task_description, re.IGNORECASE):\n",
        '            logger.info(f"Detected direct file creation task with named file: \'{task_description}\'. Handling directly.")\n',
        "            return True\n",
        "        \n",
        "        # Pattern 9: Complex pattern for search and save\n",
        '        pattern9 = r"(?:search|find|look\\s+for|research|get\\s+information\\s+about)\\s+(?:[\\w\\s\\d\\-\\+]+)\\s+(?:and|then)\\s+(?:save|store|write|create)\\s+(?:it|that|them|the\\s+results?|the\\s+information|a\\s+file|a\\s+document)"\n',
        "        if re.search(pattern9, task_description, re.IGNORECASE):\n",
        "            # Check if this is actually a web search task\n",
        '            web_terms = ["web", "internet", "online", "website", "site", "page", "browser", "chrome", "firefox", "safari", "edge"]\n',
        "            if any(term in task_description.lower() for term in web_terms):\n",
        '                logger.info(f"Detected web search task with file output: \'{task_description}\'")\n',
        "                return False\n",
        '            logger.info(f"Detected complex file creation task with search and save: \'{task_description}\'. Handling directly.")\n',
        "            return True\n",
        "        \n",
        "        # Pattern 10: Search for X and save to file Y\n",
        '        pattern10 = r"(?:search|find|look\\s+for|research|get\\s+information\\s+about)\\s+(?:[\\w\\s\\d\\-\\+]+)\\s+(?:and|then)\\s+(?:save|store|write)\\s+(?:it|that|them|the\\s+results?|the\\s+information)\\s+(?:to|in|as)\\s+(?:a\\s+)?(?:file|document)\\s+(?:named|called)?\\s+[\'\\"]?([\\w\\s\\.\\-]+)[\'\\"]?"\n',
        "        if re.search(pattern10, task_description, re.IGNORECASE):\n",
        "            # Check if this is actually a web search task\n",
        '            web_terms = ["web", "internet", "online", "website", "site", "page", "browser", "chrome", "firefox", "safari", "edge"]\n',
        "            if any(term in task_description.lower() for term in web_terms):\n",
        '                logger.info(f"Detected web search task with file output: \'{task_description}\'")\n',
        "                return False\n",
        '            logger.info(f"Detected complex file creation task with search and named file: \'{task_description}\'. Handling directly.")\n',
        "            return True\n",
        "        \n",
        "        # Pattern 11: Generate/create X based on search/web results\n",
        '        pattern11 = r"(?:generate|create|write|make|prepare)\\s+(?:a|an|the)\\s+(?:summary|report|analysis|document|file|list|compilation)\\s+(?:of|about|on|for)\\s+(?:[\\w\\s\\d\\-\\+]+)\\s+(?:based\\s+on|using|from|with)\\s+(?:search|web|internet|online)\\s+(?:results|information|data|content)"\n',
        "        if re.search(pattern11, task_description, re.IGNORECASE):\n",
        '            logger.info(f"Detected complex file creation task with web research: \'{task_description}\'. Handling directly.")\n',
        "            return False  # Changed to False to ensure web browsing is used\n",
        "        \n",
        "        # Pattern 12: Find information and create a document\n",
        '        pattern12 = r"(?:find|get|gather|collect)\\s+(?:information|data|content|details)\\s+(?:about|on|for)\\s+(?:[\\w\\s\\d\\-\\+]+)\\s+(?:and|then)\\s+(?:create|write|prepare|make)\\s+(?:a|an|the)\\s+(?:summary|report|analysis|document|file)"\n',
        "        if re.search(pattern12, task_description, re.IGNORECASE):\n",
        "            # Check if this is actually a web search task\n",
        '            web_terms = ["web", "internet", "online", "website", "site", "page", "browser", "chrome", "firefox", "safari", "edge"]\n',
        "            if any(term in task_description.lower() for term in web_terms):\n",
        '                logger.info(f"Detected web search task with file output: \'{task_description}\'")\n',
        "                return False\n",
        '            logger.info(f"Detected complex file creation task with information gathering: \'{task_description}\'. Handling directly.")\n',
        "            return True\n",
        "        \n",
        "        # Pattern 13: Summarize web content\n",
        '        pattern13 = r"(?:summarize|analyze|extract)\\s+(?:information|data|content|details)\\s+(?:from|about|on)\\s+(?:[\\w\\s\\d\\-\\+]+)\\s+(?:and|then)?\\s+(?:save|write|create|put\\s+it\\s+in)\\s+(?:a|an|the)?\\s+(?:file|document|summary|report)"\n',
        "        if re.search(pattern13, task_description, re.IGNORECASE):\n",
        "            # Check if this is actually a web search task\n",
        '            web_terms = ["web", "internet", "online", "website", "site", "page", "browser", "chrome", "firefox", "safari", "edge"]\n',
        '            if any(term in task_description.lower() for term in web_terms) or ".com" in task_description:\n',
        '                logger.info(f"Detected web content summarization task: \'{task_description}\'")\n',
        "                return False\n",
        '            logger.info(f"Detected complex file creation task with content summarization: \'{task_description}\'. Handling directly.")\n',
        "            return True\n",
        "        \n",
        "        # Fallback pattern: If it contains create/write/save and doesn't look like a web search\n",
        '        web_patterns = [r"search", r"find", r"look\\s+up", r"browse", r"internet", r"web", r"online", r"information about", r"articles on"]\n',
        "        has_web_term = any(re.search(p, task_description, re.IGNORECASE) for p in web_patterns)\n",
        "        \n",
        "        # Check for file creation terms\n",
        '        file_creation_terms = ["create", "write", "save", "store", "output", "generate", "compile", "summarize", "analyze", "extract"]\n',
        "        has_file_creation_term = any(term in task_description.lower() for term in file_creation_terms)\n",
        "        \n",
        "        # Check for content type terms that suggest file creation\n",
        '        content_type_terms = ["story", "poem", "essay", "article", "report", "note", "text", "document", "analysis", \n',
        '                              "summary", "list", "compilation", "collection", "information", "data", "content", "details"]\n',
        "        has_content_type_term = any(term in task_description.lower() for term in content_type_terms)\n",
        "        \n",
        "        # Check for output file terms\n",
        '        output_file_terms = ["file", "document", "txt", "output", "save as", "save to", "write to", "report", "summary", "analysis"]\n',
        "        has_output_file_term = any(term in task_description.lower() for term in output_file_terms)\n",
        "        \n",
        "        # Check for terms that suggest the task is about creating a document from web content\n",
        '        web_to_file_terms = ["based on search", "from web", "from the internet", "from online", "using search results", \n',
        '                             "from search results", "search and save", "find and save", "research and write", \n',
        '                             "look up and create", "search and create"]\n',
        "        has_web_to_file_term = any(term in task_description.lower() for term in web_to_file_terms)\n",
        "        \n",
        "        # Special case 1: If the task has both web terms AND file creation terms with output file terms,\n",
        "        # it's likely a complex task that should be handled as file creation\n",
        "        if has_web_term and has_file_creation_term and has_output_file_term:\n",
        "            # Check for domain names or URLs which would indicate web browsing\n",
        '            domain_pattern = r\'\\b[\\w\\-]+\\.[a-zA-Z]{2,}\\b\'\n',
        "            if re.search(domain_pattern, task_description, re.IGNORECASE):\n",
        '                logger.info(f"Detected web browsing task with domain and file output: \'{task_description}\'")\n',
        "                return False\n",
        '            logger.info(f"Detected complex file creation task with web research and file output: \'{task_description}\'. Handling directly.")\n',
        "            return True\n",
        "        \n",
        "        # Special case 2: If the task has terms suggesting web-to-file workflow\n",
        "        if has_web_to_file_term:\n",
        '            logger.info(f"Detected web-to-file workflow task: \'{task_description}\'")\n',
        "            return False\n",
        "        \n",
        "        # Special case 3: If it has file creation terms and content type terms but no web terms\n",
        "        if (has_file_creation_term and has_content_type_term) and not has_web_term:\n",
        '            logger.info(f"Detected file creation task via fallback: \'{task_description}\'. Handling directly.")\n',
        "            return True\n",
        "        \n",
        "        # Special case 4: If it has both file creation terms and output file terms\n",
        "        if has_file_creation_term and has_output_file_term:\n",
        '            logger.info(f"Detected file creation task with explicit output terms: \'{task_description}\'. Handling directly.")\n',
        "            return True\n",
        "        \n",
        "        return False\n",
    ]
    
    # Replace the original method with the updated one
    new_lines = lines[:start_line] + updated_method + lines[end_line:]
    
    # Write the updated content back to the file
    with open(file_path, 'w') as f:
        f.writelines(new_lines)
    
    print("Successfully updated _is_direct_file_creation_task method.")
    return True

def main():
    """Main function to update the Enhanced Agentic Assistant."""
    file_path = '/Users/christopher.bradford/ollamaShell/agentic_assistant_enhanced.py'
    
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} does not exist.")
        return 1
    
    # Make a backup of the original file
    backup_path = f"{file_path}.safe.bak"
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
