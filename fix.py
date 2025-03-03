with open('ollama_shell.py', 'r') as f:
    lines = f.readlines()

# Fix the indentation issue
lines[993] = "                                    console.print(\"\\n[green]Assistant:[/green]\")\n"
lines[994] = "                                    console.print(Markdown(assistant_message))\n"

with open('ollama_shell.py', 'w') as f:
    f.writelines(lines)
