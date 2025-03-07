import re

# Read the original file
with open('/Users/christopher.bradford/ollamaShell/ollama_shell.py', 'r') as f:
    content = f.read()

# Fix the dataset command
content = content.replace(
    'elif subcmd == "dataset" and subcmd_args:',
    'elif subcmd == "dataset":'
)

# Fix the export command
content = content.replace(
    'elif subcmd == "export" and subcmd_args:',
    'elif subcmd == "export":'
)

# Write the updated content back to the file
with open('/Users/christopher.bradford/ollamaShell/ollama_shell.py', 'w') as f:
    f.write(content)

print("Fixed the command handlers in ollama_shell.py")
