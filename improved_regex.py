# Improved regex to handle apostrophes and quotes in filenames
import re

# Example tasks
tasks = [
    "save to 'my_file.txt'",
    "save as \"company's_report.txt\"",
    "save in file.txt",
    "save to O'Reilly's_book.txt",
    "save as CEO's_info.txt"
]

# Original regex
original_regex = r'save\s+(?:to|in|as)\s+[\'"]?([^\'"]+\.txt)[\'"]?'

# Improved regex
improved_regex = r'save\s+(?:to|in|as)\s+[\'"]?([^\s]+?\.txt)[\'"]?'

print("Testing filename extraction with original vs improved regex:\n")

for task in tasks:
    print(f"Task: {task}")
    
    # Test original regex
    original_match = re.search(original_regex, task)
    if original_match:
        print(f"  Original regex extracted: {original_match.group(1)}")
    else:
        print("  Original regex failed to extract filename")
    
    # Test improved regex
    improved_match = re.search(improved_regex, task)
    if improved_match:
        filename = improved_match.group(1)
        # Clean up any trailing punctuation
        filename = filename.rstrip('.,;:"\'')
        print(f"  Improved regex extracted: {filename}")
    else:
        print("  Improved regex failed to extract filename")
    
    print()
