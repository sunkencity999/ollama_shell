#!/usr/bin/env python3
import os
import json
import typer
import requests
import sys
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.table import Table
from pyfiglet import Figlet
from termcolor import colored
from typing import Optional
from pathlib import Path
import datetime
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import concurrent.futures
import html2text
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings

app = typer.Typer()
console = Console()

OLLAMA_API = "http://localhost:11434/api"
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
DEFAULT_CONFIG = {
    "default_model": "llama2",
    "verbose": False,
    "save_history": True,
    "history_file": "~/.ollama_shell_history",
    "show_model_details": True,
    "temperature": 0.7,
    "context_length": 4096,
    "stored_prompts": {
        "code_expert": {
            "title": "Code Review & Improvement Expert",
            "prompt": """You are an expert software developer with deep knowledge across many programming languages and best practices. Your task is to:
1. Review code for potential issues
2. Suggest improvements for readability and performance
3. Identify security concerns
4. Recommend modern alternatives to deprecated practices
5. Explain complex code sections
Be specific in your recommendations and include code examples when relevant."""
        },
        "technical_writer": {
            "title": "Technical Documentation Expert",
            "prompt": """You are a technical writing expert. Your task is to:
1. Create clear, concise documentation
2. Explain complex technical concepts in simple terms
3. Structure information logically
4. Include relevant examples and use cases
5. Highlight important warnings or prerequisites
Focus on clarity and completeness while maintaining a professional tone."""
        },
        "code_teacher": {
            "title": "Programming Teacher & Mentor",
            "prompt": """You are a patient and knowledgeable programming teacher. Your task is to:
1. Explain concepts from fundamental principles
2. Provide helpful analogies and examples
3. Break down complex topics into manageable pieces
4. Encourage best practices and good habits
5. Answer questions thoroughly and clearly
Remember to check understanding and provide additional examples when needed."""
        },
        "system_admin": {
            "title": "System Administration Expert",
            "prompt": """You are an experienced system administrator. Your task is to:
1. Provide clear command-line solutions
2. Explain system configurations and best practices
3. Troubleshoot system issues
4. Recommend security measures
5. Optimize system performance
Always consider security implications and provide warnings about potentially dangerous operations."""
        },
        "api_designer": {
            "title": "API Design Consultant",
            "prompt": """You are an API design expert. Your task is to:
1. Design clear and intuitive API endpoints
2. Follow REST/GraphQL best practices
3. Suggest appropriate data structures
4. Consider security and performance
5. Provide example requests and responses
Focus on creating APIs that are both powerful and developer-friendly."""
        }
    }
}

PROMPT_STYLE = None

def load_config():
    """Load configuration from config file"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        return DEFAULT_CONFIG
    except Exception as e:
        console.print(f"[yellow]Warning: Could not load config, using defaults: {str(e)}[/yellow]")
        return DEFAULT_CONFIG

def save_config(config):
    """Save configuration to config file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        console.print("[green]Configuration saved successfully[/green]")
    except Exception as e:
        console.print(f"[red]Error saving config: {str(e)}[/red]")

def save_history(model: str, messages: list):
    """Save chat history to file"""
    config = load_config()
    if not config["save_history"]:
        return
    
    history_file = os.path.expanduser(config["history_file"])
    try:
        history = []
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                history = json.load(f)
        
        history.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "model": model,
            "messages": messages
        })
        
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=4)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not save history: {str(e)}[/yellow]")

def display_banner():
    f = Figlet(font='slant')
    banner = f.renderText('Ollama Shell')
    console.print(Panel(colored(banner, 'cyan'), border_style="cyan"))
    console.print(Panel("🚀 Your friendly neighborhood LLM interface", border_style="cyan"))

def send_message(model: str, message: str, system_prompt: Optional[str] = None, stream: bool = True):
    """Enhanced message sending with configuration options"""
    config = load_config()
    url = f"{OLLAMA_API}/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt} if system_prompt else None,
            {"role": "user", "content": message}
        ],
        "options": {
            "temperature": config["temperature"],
            "num_ctx": config["context_length"]
        },
        "stream": stream
    }
    # Remove None values from messages
    payload["messages"] = [msg for msg in payload["messages"] if msg is not None]
    
    try:
        response = requests.post(url, json=payload, stream=stream)
        response.raise_for_status()
        
        if stream:
            # Return the response object for streaming
            return response
        else:
            # Process non-streaming response
            try:
                result = response.json()
                if isinstance(result, dict) and "message" in result and "content" in result["message"]:
                    return result
                else:
                    raise Exception("Unexpected response format")
            except json.JSONDecodeError as e:
                # If JSON parsing fails, try to extract content from raw response
                content = response.text.strip()
                if content:
                    return {"message": {"content": content}}
                else:
                    raise Exception(f"Failed to parse response: {str(e)}")
    
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error sending message: {str(e)}")

def get_available_models():
    """Get list of available models from Ollama"""
    try:
        response = requests.get(f"{OLLAMA_API}/tags")
        if response.status_code == 200:
            return [model["name"] for model in response.json()["models"]]
        return []
    except Exception:
        return []

def validate_model(model: str) -> tuple[bool, str]:
    """Validate if a model exists and return (is_valid, error_message)"""
    try:
        available_models = get_available_models()
        if not available_models:
            return False, "Could not fetch available models. Is Ollama running?"
        
        if model not in available_models:
            message = f"Model '{model}' not found. Available models:\n"
            for i, m in enumerate(available_models, 1):
                message += f"  {i}. {m}\n"
            return False, message
        
        return True, ""
    except Exception as e:
        return False, f"Error validating model: {str(e)}"

def load_history():
    """Load chat history from file"""
    config = load_config()
    history_file = os.path.expanduser(config["history_file"])
    try:
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        console.print(f"[yellow]Warning: Could not load history: {str(e)}[/yellow]")
        return []

def view_history():
    """View and manage chat history"""
    history = load_history()
    
    while True:
        console.clear()
        display_banner()
        
        if not history:
            console.print("[yellow]No chat history found[/yellow]")
            Prompt.ask("\n[yellow]Press Enter to continue[/yellow]")
            return
        
        # Group chats by date
        from collections import defaultdict
        from datetime import datetime
        
        chats_by_date = defaultdict(list)
        for i, chat in enumerate(history):
            date = datetime.fromisoformat(chat["timestamp"]).strftime("%Y-%m-%d")
            chats_by_date[date].append((i, chat))
        
        # Display chats grouped by date
        table = Table(title="Chat History")
        table.add_column("Number", style="green")
        table.add_column("Date", style="cyan")
        table.add_column("Model", style="yellow")
        table.add_column("Messages", style="white")
        
        for date in sorted(chats_by_date.keys(), reverse=True):
            for i, chat in chats_by_date[date]:
                msg_count = len([m for m in chat["messages"] if m["role"] == "user"])
                preview = chat["messages"][1]["content"][:50] + "..." if len(chat["messages"]) > 1 else "Empty chat"
                table.add_row(
                    f"[green]{i + 1}[/green]",
                    date,
                    chat["model"],
                    f"{msg_count} messages - {preview}"
                )
        
        console.print(table)
        console.print("\n[cyan]Options:[/cyan]")
        console.print("[green]number[/green]: View chat details")
        console.print("[green]r number[/green]: Resume chat")
        console.print("[green]c[/green]: Clear all history")
        console.print("[green]x[/green]: Exit to main menu")
        console.print("[green]e number[/green]: Export chat")
        
        choice = Prompt.ask("\n[yellow]Enter your choice[/yellow]")
        
        if choice.lower() == 'x':
            break
        elif choice.lower() == 'c':
            if Prompt.ask("\n[red]Are you sure you want to clear all history?[/red] (y/n)", default="n").lower() == 'y':
                config = load_config()
                history_file = os.path.expanduser(config["history_file"])
                try:
                    with open(history_file, 'w') as f:
                        json.dump([], f)
                    console.print("[green]History cleared successfully[/green]")
                    history = []
                except Exception as e:
                    console.print(f"[red]Error clearing history: {str(e)}[/red]")
            Prompt.ask("\n[yellow]Press Enter to continue[/yellow]")
        elif choice.startswith('r ') and choice[2:].isdigit():
            chat_num = int(choice[2:])
            if 1 <= chat_num <= len(history):
                chat = history[chat_num - 1]
                console.clear()
                display_banner()
                
                # Resume chat with the same model and history
                console.print(f"\n[cyan]Resuming chat from {chat['timestamp']}[/cyan]")
                console.print(f"[yellow]Model: {chat['model']}[/yellow]\n")
                
                # Display previous messages
                for msg in chat["messages"]:
                    if msg["role"] == "system":
                        console.print(f"[yellow]System: {msg['content']}[/yellow]")
                    elif msg["role"] == "user":
                        console.print(f"\n[cyan]You:[/cyan]")
                        console.print(Panel(msg["content"], border_style="cyan"))
                    else:
                        console.print(f"\n[purple]Assistant:[/purple]")
                        console.print(Panel(Markdown(msg["content"]), border_style="purple"))
                
                # Start interactive chat with existing history
                interactive_chat(chat["model"], 
                              system_prompt=next((msg["content"] for msg in chat["messages"] if msg["role"] == "system"), None),
                              existing_history=chat["messages"])
                break
        elif choice.startswith('e ') and choice[2:].isdigit():
            chat_num = int(choice[2:])
            if 1 <= chat_num <= len(history):
                chat = history[chat_num - 1]
                console.clear()
                display_banner()
                
                # Export chat
                console.print(f"\n[cyan]Exporting chat from {chat['timestamp']}[/cyan]")
                console.print(f"[yellow]Model: {chat['model']}[/yellow]\n")
                
                # Ask for export format
                console.print("\n[cyan]Select export format:[/cyan]")
                console.print("[green]1[/green]. Markdown")
                console.print("[green]2[/green]. HTML")
                console.print("[green]3[/green]. PDF")
                
                choice = Prompt.ask("\n[yellow]Enter your choice[/yellow]", default="1")
                
                if choice == "1":
                    format = "markdown"
                elif choice == "2":
                    format = "html"
                elif choice == "3":
                    format = "pdf"
                else:
                    console.print("[red]Invalid choice. Defaulting to markdown.[/red]")
                    format = "markdown"
                
                # Ask for output file
                output_file = Prompt.ask("\n[cyan]Enter output file name (or press Enter for default)[/cyan]", default="")
                
                try:
                    output_path = export_chat(chat["messages"], format, output_file)
                    console.print(f"\n[green]Chat exported successfully to {output_path}![/green]")
                except Exception as e:
                    console.print(f"\n[red]Error exporting chat: {str(e)}[/red]")
                
                Prompt.ask("\n[yellow]Press Enter to continue[/yellow]")
        elif choice.isdigit() and 1 <= int(choice) <= len(history):
            chat = history[int(choice) - 1]
            console.clear()
            display_banner()
            
            # Display chat details
            console.print(f"\n[cyan]Chat from {chat['timestamp']}[/cyan]")
            console.print(f"[yellow]Model: {chat['model']}[/yellow]\n")
            
            for msg in chat["messages"]:
                if msg["role"] == "system":
                    console.print(f"[yellow]System: {msg['content']}[/yellow]")
                elif msg["role"] == "user":
                    console.print(f"\n[cyan]You:[/cyan]")
                    console.print(Panel(msg["content"], border_style="cyan"))
                else:
                    console.print(f"\n[purple]Assistant:[/purple]")
                    console.print(Panel(Markdown(msg["content"]), border_style="purple"))
            
            Prompt.ask("\n[yellow]Press Enter to continue[/yellow]")

def export_chat(chat_history: list, format: str = "markdown", output_file: str = None) -> str:
    """Export chat history to various formats
    
    Args:
        chat_history: List of chat messages
        format: Output format (markdown, html, or pdf)
        output_file: Optional output file path
    
    Returns:
        str: Path to the exported file
    """
    if not chat_history:
        raise ValueError("No chat history to export")
    
    # Generate timestamp for default filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Convert chat history to markdown
    markdown_content = "# Chat History\n\n"
    markdown_content += f"Exported on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    for msg in chat_history:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        
        if role == "system":
            markdown_content += f"### System\n{content}\n\n"
        elif role == "user":
            markdown_content += f"### You\n{content}\n\n"
        elif role == "assistant":
            markdown_content += f"### Assistant\n{content}\n\n"
    
    # Determine output path
    if not output_file:
        output_file = f"chat_export_{timestamp}.{format}"
    
    output_path = os.path.expanduser(output_file)
    
    try:
        if format == "markdown":
            # Save as markdown
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
        
        elif format == "html":
            # Convert markdown to HTML
            import markdown2
            html_content = markdown2.markdown(markdown_content, extras=["fenced-code-blocks", "tables"])
            
            # Add some basic styling
            html_template = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                    h1 {{ color: #2c3e50; }}
                    h3 {{ color: #34495e; margin-top: 20px; }}
                    pre {{ background-color: #f7f9fa; padding: 10px; border-radius: 5px; }}
                    code {{ font-family: Monaco, monospace; }}
                </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_template)
        
        elif format == "pdf":
            # First convert to HTML, then to PDF
            import markdown2
            from weasyprint import HTML, CSS
            from weasyprint.text.fonts import FontConfiguration
            
            html_content = markdown2.markdown(markdown_content, extras=["fenced-code-blocks", "tables"])
            
            # Add some basic styling with proper font configuration
            font_config = FontConfiguration()
            css = CSS(string='''
                @page {
                    size: letter;
                    margin: 2cm;
                }
                body {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                }
                h1 {
                    color: #2c3e50;
                    font-size: 24px;
                    margin-bottom: 20px;
                }
                h3 {
                    color: #34495e;
                    font-size: 18px;
                    margin-top: 20px;
                    margin-bottom: 10px;
                }
                pre {
                    background-color: #f7f9fa;
                    padding: 10px;
                    border-radius: 5px;
                    font-family: "SF Mono", Consolas, "Liberation Mono", Menlo, Courier, monospace;
                    font-size: 14px;
                    white-space: pre-wrap;
                }
                code {
                    font-family: "SF Mono", Consolas, "Liberation Mono", Menlo, Courier, monospace;
                    font-size: 14px;
                }
            ''', font_config=font_config)
            
            html_template = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
            
            # Create PDF with proper font configuration
            HTML(string=html_template).write_pdf(output_path, stylesheets=[css], font_config=font_config)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
            
    except Exception as e:
        raise Exception(f"Error exporting chat: {str(e)}")

def interactive_chat(model: str, system_prompt: Optional[str] = None, context_files: Optional[list[str]] = None, existing_history: Optional[list] = None):
    """Start an interactive chat session with the specified model"""
    config = load_config()
    
    # Validate model before starting chat
    is_valid, error_message = validate_model(model)
    if not is_valid:
        console.print(f"\n[red]Error: {error_message}[/red]")
        return
    
    console.clear()
    display_banner()
    console.print(f"\n[green]Starting chat with model: [bold]{model}[/bold][/green]")
    
    # Set up key bindings for drag-and-drop
    kb = KeyBindings()
    drag_drop_active = False

    # Create a class to hold mutable state
    class ChatState:
        def __init__(self):
            self.document_context = ""
            
    chat_state = ChatState()

    @kb.add('c-v')
    def _(event):
        nonlocal drag_drop_active
        drag_drop_active = not drag_drop_active
        if drag_drop_active:
            console.print("\n[cyan]Drag & Drop mode activated (Ctrl+V to toggle)[/cyan]")
            console.print("[cyan]Drag a file into the terminal...[/cyan]")
        else:
            console.print("\n[cyan]Drag & Drop mode deactivated[/cyan]")
    
    # Create prompt session with key bindings
    session = PromptSession(key_bindings=kb)
    
    # Initialize base system prompt
    base_system_prompt = """You are a helpful assistant that can engage in general conversation while also referencing 
    documents that have been shared. When discussing shared documents, be specific and reference their content when relevant.
    However, you can also discuss other topics naturally."""
    
    if system_prompt:
        base_system_prompt = system_prompt + "\n\n" + base_system_prompt
    
    # Prepare initial document context if files are provided
    if context_files:
        try:
            chat_state.document_context = prepare_document_context(context_files)
            console.print(f"[yellow]Loaded {len(context_files)} document(s) into context[/yellow]")
        except Exception as e:
            console.print(f"[red]Error loading documents: {str(e)}[/red]")
            return

    # Function to get current system prompt with document context
    def get_current_system_prompt():
        current_prompt = base_system_prompt
        if chat_state.document_context:
            current_prompt += f"\n\nAvailable document context:\n{chat_state.document_context}"
        return current_prompt

    if not system_prompt and config["stored_prompts"]:
        # Offer to use a stored prompt
        console.print("\n[bold yellow]Stored System Prompts[/bold yellow]")
        prompts = list(config["stored_prompts"].items())
        
        # Add "none" option
        console.print("[green]0[/green]. No system prompt")
        
        # List available prompts
        for i, (name, prompt) in enumerate(prompts, 1):
            preview = prompt["prompt"][:50] + "..." if len(prompt["prompt"]) > 50 else prompt["prompt"]
            console.print(f"[green]{i}[/green]. {name}: {preview}")
        
        choice = Prompt.ask("\nSelect a system prompt", choices=[str(i) for i in range(len(prompts) + 1)])
        choice = int(choice)
        
        if choice > 0:
            base_system_prompt = prompts[choice - 1][1]["prompt"] + "\n\n" + base_system_prompt
            console.print(f"\n[cyan]Using stored prompt: {prompts[choice - 1][0]}[/cyan]")
    
    chat_history = existing_history if existing_history else []
    chat_history.append({"role": "system", "content": get_current_system_prompt()})

    console.print("\n[cyan]Chat started. Type 'exit' to end. Press Ctrl+V to toggle drag & drop mode.[/cyan]")

    while True:
        try:
            # Use prompt_toolkit session for input
            console.print("\nYou:", style="cyan")
            user_input = session.prompt("  ").strip()  # Two spaces for proper alignment
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                # Offer to export chat before exiting
                if chat_history and Prompt.ask("\nWould you like to export this chat? [y/N]").lower() == 'y':
                    format_choice = Prompt.ask(
                        "Choose format",
                        choices=["markdown", "html", "pdf"],
                        default="markdown"
                    )
                    try:
                        output_file = export_chat(chat_history, format=format_choice)
                        console.print(f"[green]Chat exported to: {output_file}[/green]")
                    except Exception as e:
                        console.print(f"[red]Error exporting chat: {str(e)}[/red]")
                break

            # Handle drag & drop mode
            if drag_drop_active and user_input:
                # Clean up the file path by removing escape characters and expanding user path
                cleaned_path = os.path.expanduser(user_input.replace('\\', ''))
                if os.path.exists(cleaned_path):
                    try:
                        content, file_type = read_file_content(cleaned_path)
                        # Update document context
                        chat_state.document_context += f"\n\nContent from {os.path.basename(cleaned_path)} ({file_type}):\n{content}"
                        
                        # Create a message about the file being shared
                        file_message = f"I've added a {file_type} to our conversation. Please analyze it and provide key insights. The content is:\n\n{content}"
                        
                        # Send message to model (non-streaming for file analysis)
                        with console.status("[cyan]Analyzing document...[/cyan]"):
                            try:
                                response = send_message(model, file_message, get_current_system_prompt(), stream=False)
                                if response and "message" in response and "content" in response["message"]:
                                    assistant_message = response["message"]["content"]
                                    chat_history.append({"role": "user", "content": file_message})
                                    chat_history.append({"role": "assistant", "content": assistant_message})
                                    console.print(f"\n[green]Successfully loaded file: {os.path.basename(cleaned_path)}[/green]")
                                    console.print("\n[green]Assistant:[/green]")
                                    console.print(Markdown(assistant_message))
                                else:
                                    console.print("[red]Error: Unexpected response format from model[/red]")
                            except Exception as e:
                                console.print(f"[red]Error getting model response: {str(e)}[/red]")
                        continue
                    except Exception as e:
                        console.print(f"[red]Error reading file: {str(e)}[/red]")
                        continue

            chat_history.append({"role": "user", "content": user_input})
            
            # Regular chat - use streaming response with current context
            try:
                with console.status("[cyan]Thinking...[/cyan]"):
                    response = send_message(model, user_input, get_current_system_prompt(), stream=True)
                    assistant_message = ""
                    console.print("\n[green]Assistant:[/green]")
                
                # Stream the response outside the loading animation
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "message" in data:
                                content = data["message"].get("content", "")
                                assistant_message += content
                                console.print(content, end="")
                        except json.JSONDecodeError:
                            continue
                
                console.print()  # New line after streaming
                chat_history.append({"role": "assistant", "content": assistant_message})
                
                if config["save_history"]:
                    save_history(model, chat_history)
            except Exception as e:
                console.print(f"\n[red]Error: {str(e)}[/red]")
        
        except KeyboardInterrupt:
            console.print("\n[yellow]Exiting chat...[/yellow]")
            break
        except requests.exceptions.ConnectionError:
            console.print("\n[red]Error: Could not connect to Ollama. Is it running?[/red]")
            break
        except Exception as e:
            console.print(f"\n[red]Error: {str(e)}[/red]")
            if config["verbose"]:
                import traceback
                console.print(f"\n[red]Traceback: {traceback.format_exc()}[/red]")
            continue

def display_help():
    """Display comprehensive help information"""
    # Title
    f = Figlet(font='slant')
    title = f.renderText('Ollama Shell')
    console.print(Panel(colored(title, 'cyan'), border_style="cyan"))
    console.print(Panel("A powerful interface for chatting with and managing your Ollama models", border_style="cyan"))
    
    # Chat Commands
    console.print("\n[bold yellow]Chat Commands[/bold yellow]")
    chat_commands = [
        ("chat", "Start an interactive chat session", "chat [--model MODEL] [--system-prompt PROMPT]"),
        ("prompt", "Send a single prompt", "prompt [--model MODEL] PROMPT_TEXT"),
        ("history", "View chat history", "history"),
        ("export", "Export chat to file", "export [--format FORMAT] [--output FILE] [--history-id ID]")
    ]
    
    for cmd, desc, usage in chat_commands:
        console.print(f"[cyan]{cmd}[/cyan]: {desc}")
        console.print(f"  Usage: {usage}\n")
    
    # Model Management
    console.print("\n[bold yellow]Model Management[/bold yellow]")
    model_commands = [
        ("models", "List available models", "models"),
        ("pull", "Download a new model", "pull MODEL_NAME"),
        ("delete", "Delete an installed model", "delete MODEL_NAME")
    ]
    
    for cmd, desc, usage in model_commands:
        console.print(f"[cyan]{cmd}[/cyan]: {desc}")
        console.print(f"  Usage: {usage}\n")
    
    # System Prompts
    console.print("\n[bold yellow]System Prompts[/bold yellow]")
    prompt_commands = [
        ("prompts", "Manage system prompts", "prompts")
    ]
    
    console.print("[cyan]prompts[/cyan]: Manage your stored system prompts")
    console.print("  Features:")
    console.print("  • Save frequently used system prompts")
    console.print("  • View and edit existing prompts")
    console.print("  • Delete unused prompts")
    console.print("  • Select saved prompts when starting a chat")
    console.print("  Usage: prompts\n")
    
    # Configuration
    console.print("\n[bold yellow]Configuration[/bold yellow]")
    config_commands = [
        ("settings", "View or modify settings", "settings [--show] [OPTIONS...]")
    ]
    
    for cmd, desc, usage in config_commands:
        console.print(f"[cyan]{cmd}[/cyan]: {desc}")
        console.print(f"  Usage: {usage}\n")
    
    # Special Features
    console.print("\n[bold yellow]Special Features[/bold yellow]")
    features = [
        "💡 Use arrow keys to navigate through command history in chat",
        "💡 Set your preferred model in config to avoid specifying it each time",
        "💡 Enable verbose mode in config for detailed API responses",
        "💡 Save frequently used system prompts for quick access",
        "💡 Check the history command to continue previous conversations",
        "💡 Use Ctrl+V to toggle drag-and-drop mode for files",
        "💡 Export chats to markdown, HTML, or PDF formats"
    ]
    
    for feature in features:
        console.print(f"  {feature}")
    
    # Additional Resources
    console.print("\n[bold yellow]Additional Resources[/bold yellow]")
    console.print("📚 Ollama Documentation: [link]https://ollama.ai/docs[/link]")
    console.print("🐙 Project Repository: [link]https://github.com/sunkencity999/ollama_shell[/link]")
    
    # Wait for user input
    Prompt.ask("\n[dim]Press Enter to return to menu...[/dim]")

@app.command()
def help():
    """Show help information about available commands"""
    display_help()

@app.command()
def chat(
    model: Optional[str] = typer.Option(None, help="Model to use for chat"),
    system_prompt: Optional[str] = typer.Option(None, help="System prompt to use"),
    context_files: Optional[list[str]] = typer.Option(None, help="List of files to include in context")
):
    """Start an interactive chat session with the specified model"""
    config = load_config()
    model = model or config["default_model"]
    interactive_chat(model, system_prompt, context_files)

@app.command()
def models():
    """List available models and their details"""
    try:
        response = requests.get(f"{OLLAMA_API}/tags")
        if response.status_code == 200:
            models = response.json()["models"]
            
            # Create a table of models
            table = Table(title="Available Models")
            table.add_column("Name", style="cyan")
            table.add_column("Size", style="green")
            table.add_column("Modified", style="yellow")
            
            for model in models:
                size = f"{model['size'] / 1024 / 1024 / 1024:.1f}GB"
                table.add_row(
                    model['name'],
                    size,
                    model.get('modified', 'N/A')
                )
            
            display_banner()
            console.print(table)
        else:
            console.print("[red]Error fetching models[/red]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

@app.command()
def pull(
    model: str = typer.Argument(..., help="Name of the model to download")
):
    """Download a new model from Ollama"""
    try:
        console.print(f"\n[cyan]Downloading model: {model}[/cyan]")
        
        # Track unique statuses to avoid repetition
        seen_statuses = set()
        current_status = None
        
        with console.status("[cyan]Starting download...[/cyan]") as status:
            response = requests.post(
                f"{OLLAMA_API}/pull",
                json={"name": model},
                stream=True
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line)
                        if 'status' in data:
                            # Only show new or changed status messages
                            if data['status'] != current_status:
                                current_status = data['status']
                                if current_status not in seen_statuses:
                                    seen_statuses.add(current_status)
                                    # Format the status message
                                    if "pulling" in current_status:
                                        status.update(f"[cyan]Pulling model files...[/cyan]")
                                    elif "verifying" in current_status:
                                        status.update(f"[yellow]Verifying download...[/yellow]")
                                    elif "writing" in current_status:
                                        status.update(f"[green]Writing model to disk...[/green]")
                                    else:
                                        status.update(f"[cyan]{current_status}[/cyan]")
                        
                        if 'error' in data:
                            console.print(f"\n[red]Error: {data['error']}[/red]")
                            return
                
                console.print(f"\n[green]Successfully downloaded {model}![/green]")
            else:
                console.print(f"\n[red]Error downloading model: {response.text}[/red]")
    except Exception as e:
        console.print(f"\n[red]Error: {str(e)}[/red]")

@app.command()
def delete(
    model: str = typer.Argument(..., help="Name of the model to delete")
):
    """Delete a model from Ollama"""
    try:
        # If no model specified, show list of installed models
        if not model or model == "list":
            available_models = get_available_models()
            if not available_models:
                console.print("[yellow]No models installed. Is Ollama running?[/yellow]")
                return
            
            console.print("\n[cyan]Installed Models:[/cyan]")
            for i, m in enumerate(available_models, 1):
                console.print(f"[green]{i}[/green]. {m}")
            
            choice = Prompt.ask("\nSelect model to delete (number or name)", default="")
            if not choice:
                console.print("[yellow]Operation cancelled.[/yellow]")
                return
            
            # Handle numeric choice
            if choice.isdigit() and 1 <= int(choice) <= len(available_models):
                model = available_models[int(choice) - 1]
            else:
                model = choice
        
        # Confirm deletion
        if not Prompt.ask(f"\n[yellow]Are you sure you want to delete {model}?[/yellow]", choices=["y", "n"]) == "y":
            console.print("[yellow]Operation cancelled.[/yellow]")
            return
        
        with console.status(f"[cyan]Deleting model: {model}...[/cyan]"):
            response = requests.delete(
                f"{OLLAMA_API}/delete",
                json={"name": model}
            )
            
            if response.status_code == 200:
                console.print(f"\n[green]Successfully deleted {model}![/green]")
            else:
                console.print(f"\n[red]Error deleting model: {response.text}[/red]")
    except Exception as e:
        console.print(f"\n[red]Error: {str(e)}[/red]")

@app.command()
def prompt(
    model: str = typer.Option("llama2", help="Model to use"),
    prompt_text: str = typer.Argument(..., help="The prompt to send")
):
    """Send a single prompt to the model"""
    with console.status("[cyan]Thinking...[/cyan]"):
        response = send_message(model, prompt_text)
        if response:
            console.print(Panel(Markdown(response["message"]["content"]), border_style="purple"))

@app.command()
def config_settings(
    default_model: Optional[str] = typer.Option(None, help="Set default model"),
    verbose: Optional[bool] = typer.Option(None, help="Toggle verbose mode"),
    save_history: Optional[bool] = typer.Option(None, help="Toggle history saving"),
    temperature: Optional[float] = typer.Option(None, help="Set temperature (0.0-1.0)"),
    context_length: Optional[int] = typer.Option(None, help="Set context length"),
    show: bool = typer.Option(False, help="Show current configuration")
):
    """View or modify configuration settings"""
    current_config = load_config()
    
    if show:
        table = Table(title="Current Configuration")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in current_config.items():
            table.add_row(key, str(value))
        
        display_banner()
        console.print(table)
        return
    
    # Update configuration if any options provided
    if any(x is not None for x in [default_model, verbose, save_history, temperature, context_length]):
        if default_model:
            current_config["default_model"] = default_model
        if verbose is not None:
            current_config["verbose"] = verbose
        if save_history is not None:
            current_config["save_history"] = save_history
        if temperature is not None:
            current_config["temperature"] = max(0.0, min(1.0, temperature))
        if context_length is not None:
            current_config["context_length"] = context_length
        
        save_config(current_config)
        console.print("\n[green]Configuration updated:[/green]")
        config_settings(show=True)

def interactive_config():
    """Interactive configuration editor"""
    current_config = load_config()
    
    while True:
        console.clear()
        display_banner()
        
        # Display current configuration
        table = Table(title="Current Configuration")
        table.add_column("Number", style="green")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="white")
        
        # Convert config items to list for numbered access
        config_items = list(current_config.items())
        for i, (key, value) in enumerate(config_items, 1):
            table.add_row(f"[green]{i}[/green]", key, str(value))
        
        console.print(table)
        console.print("\n[cyan]Options:[/cyan]")
        console.print("[green]1-7[/green]: Edit setting")
        console.print("[green]s[/green]: Save and exit")
        console.print("[green]x[/green]: Exit without saving")
        
        choice = Prompt.ask("\n[yellow]Enter your choice[/yellow]")
        
        if choice.lower() == 'x':
            break
        elif choice.lower() == 's':
            save_config(current_config)
            break
        elif choice.isdigit() and 1 <= int(choice) <= len(config_items):
            index = int(choice) - 1
            key, current_value = config_items[index]
            
            if key == "default_model":
                # Show available models for selection
                response = requests.get(f"{OLLAMA_API}/tags")
                if response.status_code == 200:
                    models = [model["name"] for model in response.json()["models"]]
                    console.print("\nAvailable models:")
                    for i, model in enumerate(models, 1):
                        console.print(f"[green]{i}[/green]. {model}")
                    model_choice = Prompt.ask("\nSelect model number", default="1")
                    if model_choice.isdigit() and 1 <= int(model_choice) <= len(models):
                        current_config[key] = models[int(model_choice) - 1]
            
            elif isinstance(current_value, bool):
                current_config[key] = not current_value
                console.print(f"\n[green]{key} set to {current_config[key]}[/green]")
            
            elif isinstance(current_value, (int, float)):
                if key == "temperature":
                    new_value = Prompt.ask(f"\nEnter new {key} (0.0-1.0)", default=str(current_value))
                    try:
                        current_config[key] = max(0.0, min(1.0, float(new_value)))
                    except ValueError:
                        console.print("[red]Invalid value. Must be between 0.0 and 1.0[/red]")
                else:
                    new_value = Prompt.ask(f"\nEnter new {key}", default=str(current_value))
                    try:
                        current_config[key] = int(new_value) if isinstance(current_value, int) else float(new_value)
                    except ValueError:
                        console.print("[red]Invalid value[/red]")
            
            else:  # string values
                new_value = Prompt.ask(f"\nEnter new {key}", default=str(current_value))
                current_config[key] = new_value
            
            Prompt.ask("\n[yellow]Press Enter to continue[/yellow]")

def manage_prompts():
    """Manage stored system prompts"""
    while True:
        console.clear()
        display_banner()
        
        # Display current prompts
        console.print("\n[bold yellow]Stored System Prompts[/bold yellow]")
        config = load_config()
        if not config["stored_prompts"]:
            console.print("[dim]No stored prompts. Add one to get started![/dim]")
        else:
            table = Table(show_header=True)
            table.add_column("Name", style="cyan")
            table.add_column("Title", style="yellow")
            table.add_column("Preview", style="white")
            
            for name, prompt_data in config["stored_prompts"].items():
                # Truncate long prompts for display
                preview = prompt_data["prompt"][:80] + "..." if len(prompt_data["prompt"]) > 80 else prompt_data["prompt"]
                preview = preview.replace("\n", " ")  # Make it single line
                table.add_row(name, prompt_data["title"], preview)
            
            console.print(table)
        
        # Display options
        console.print("\n[bold yellow]Options[/bold yellow]")
        options = [
            ("1", "Add new prompt"),
            ("2", "Delete prompt"),
            ("3", "View full prompt"),
            ("4", "Search prompts"),
            ("5", "Return to main menu")
        ]
        
        for num, desc in options:
            console.print(f"[green]{num}[/green]. {desc}")
        
        choice = Prompt.ask("\nEnter your choice", choices=[str(i) for i in range(1, 6)])
        
        if choice == "1":
            name = Prompt.ask("\nEnter a name for the prompt (used for selection)")
            if name in config["stored_prompts"]:
                if not Prompt.ask(f"[yellow]Prompt '{name}' already exists. Overwrite?[/yellow]", choices=["y", "n"]) == "y":
                    continue
            
            title = Prompt.ask("Enter a descriptive title for the prompt")
            
            console.print("\nEnter the prompt text (press Enter twice to finish):")
            lines = []
            while True:
                line = input()
                if not line and lines and not lines[-1]:
                    break
                lines.append(line)
            
            prompt_text = "\n".join(lines[:-1])  # Remove the last empty line
            config["stored_prompts"][name] = {
                "title": title,
                "prompt": prompt_text
            }
            save_config(config)
            console.print("[green]Prompt saved successfully![/green]")
        
        elif choice == "2":
            if not config["stored_prompts"]:
                console.print("[yellow]No prompts to delete![/yellow]")
                Prompt.ask("\nPress Enter to continue")
                continue
            
            console.print("\n[dim]Available prompts (press Enter to cancel):[/dim]")
            for name, prompt_data in config["stored_prompts"].items():
                console.print(f"  [cyan]{name}[/cyan]: {prompt_data['title']}")
            
            name = Prompt.ask("\nEnter the name of the prompt to delete", default="", show_default=False)
            if not name:
                console.print("[yellow]Operation cancelled.[/yellow]")
                continue
            
            if name not in config["stored_prompts"]:
                console.print(f"[red]Prompt '{name}' not found.[/red]")
                continue
                
            if Prompt.ask(f"[yellow]Are you sure you want to delete '{config['stored_prompts'][name]['title']}'?[/yellow]", choices=["y", "n"]) == "y":
                del config["stored_prompts"][name]
                save_config(config)
                console.print("[green]Prompt deleted successfully![/green]")
        
        elif choice == "3":
            if not config["stored_prompts"]:
                console.print("[yellow]No prompts to view![/yellow]")
                Prompt.ask("\nPress Enter to continue")
                continue
            
            name = Prompt.ask("Enter the name of the prompt to view", choices=list(config["stored_prompts"].keys()))
            prompt_data = config["stored_prompts"][name]
            console.print(f"\n[bold cyan]{prompt_data['title']}[/bold cyan]")
            console.print(Panel(prompt_data["prompt"], border_style="cyan"))
            Prompt.ask("\nPress Enter to continue")
        
        elif choice == "4":
            if not config["stored_prompts"]:
                console.print("[yellow]No prompts to search![/yellow]")
                Prompt.ask("\nPress Enter to continue")
                continue
            
            search_term = Prompt.ask("\nEnter search term").lower()
            matches = []
            
            for name, prompt_data in config["stored_prompts"].items():
                if (search_term in name.lower() or 
                    search_term in prompt_data["title"].lower() or 
                    search_term in prompt_data["prompt"].lower()):
                    matches.append((name, prompt_data))
            
            if not matches:
                console.print("[yellow]No matching prompts found.[/yellow]")
            else:
                console.print("\n[bold cyan]Matching Prompts:[/bold cyan]")
                table = Table(show_header=True)
                table.add_column("Name", style="cyan")
                table.add_column("Title", style="yellow")
                table.add_column("Preview", style="white")
                
                for name, prompt_data in matches:
                    preview = prompt_data["prompt"][:80] + "..." if len(prompt_data["prompt"]) > 80 else prompt_data["prompt"]
                    preview = preview.replace("\n", " ")
                    table.add_row(name, prompt_data["title"], preview)
                
                console.print(table)
            
            Prompt.ask("\nPress Enter to continue")
        
        elif choice == "5":
            break
        
        if choice != "5":
            Prompt.ask("\nPress Enter to continue")

def read_file_content(file_path: str) -> tuple[str, str]:
    """Read and process file content based on file type"""
    file_path = os.path.expanduser(file_path)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Get file extension
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    
    try:
        if ext in ['.pdf']:
            # For PDF files, we'll need PyPDF2
            try:
                import PyPDF2
                with open(file_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    text = '\n'.join(page.extract_text() for page in reader.pages)
                    return text, "PDF document"
            except ImportError:
                raise ImportError("PyPDF2 is required for PDF support. Install it with: pip install PyPDF2")
        
        elif ext in ['.docx', '.doc']:
            # For Word documents, we'll need python-docx
            try:
                from docx import Document
                doc = Document(file_path)
                # Extract text from paragraphs and tables
                text_parts = []
                
                # Get text from paragraphs
                for para in doc.paragraphs:
                    text_parts.append(para.text)
                
                # Get text from tables
                for table in doc.tables:
                    for row in table.rows:
                        row_text = []
                        for cell in row.cells:
                            row_text.append(cell.text.strip())
                        text_parts.append(" | ".join(row_text))
                
                text = "\n".join(text_parts)
                return text, "Word document"
            except ImportError:
                raise ImportError("python-docx is required for Word document support. Install it with: pip install python-docx")
        
        elif ext in ['.md', '.txt', '.py', '.js', '.html', '.css', '.json', '.yaml', '.yml']:
            # Text files can be read directly
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
                return text, f"{ext[1:].upper()} file"
        
        else:
            raise ValueError(f"Unsupported file type: {ext}")
            
    except Exception as e:
        raise Exception(f"Error reading file: {str(e)}")

def prepare_document_context(files: list[str]) -> str:
    """Prepare context from multiple documents"""
    context = []
    for file_path in files:
        try:
            content, file_type = read_file_content(file_path)
            context.append(f"\n--- {file_type}: {os.path.basename(file_path)} ---\n{content}")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not read {file_path}: {str(e)}[/yellow]")
    
    return "\n".join(context)

def display_menu():
    """Display interactive menu and handle command selection"""
    commands = [
        ("chat", "Start an interactive chat session with a model", chat),
        ("models", "List all available models", models),
        ("pull", "Download a new model", pull),
        ("delete", "Delete an installed model", lambda: delete(None)),
        ("history", "View chat history", view_history),
        ("settings", "View or modify configuration settings", interactive_config),
        ("prompts", "Manage stored system prompts", manage_prompts),
        ("help", "Show help information", help),
        ("exit", "Exit the application", None)
    ]
    
    while True:
        console.clear()
        display_banner()
        console.print("\n[cyan]Available Commands:[/cyan]")
        
        # Create a table for better visualization
        table = Table(show_header=False, box=None)
        table.add_column("Number", style="green")
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="white")
        
        for i, (cmd, desc, _) in enumerate(commands, 1):
            table.add_row(f"[green]{i}[/green]", cmd, desc)
        
        console.print(table)
        
        try:
            choice = Prompt.ask("\n[yellow]Enter a number to select a command[/yellow]", default="1")
            if not choice.isdigit() or int(choice) < 1 or int(choice) > len(commands):
                console.print("[red]Invalid choice. Please enter a number between 1 and {len(commands)}[/red]")
                continue
            
            index = int(choice) - 1
            command_name, _, command_func = commands[index]
            
            if command_name == "exit":
                console.print("[yellow]Goodbye![/yellow]")
                break
            
            # Clear screen for better UI
            console.clear()
            
            if command_name == "chat":
                # Special handling for chat to prompt for model
                config = load_config()
                available_models = get_available_models()
                
                if not available_models:
                    console.print("[red]Error: Could not fetch available models. Is Ollama running?[/red]")
                    Prompt.ask("\n[yellow]Press Enter to continue[/yellow]")
                    continue
                
                # Show available models
                console.print("\n[cyan]Available models:[/cyan]")
                for i, m in enumerate(available_models, 1):
                    console.print(f"[green]{i}[/green]. {m}")
                
                model = Prompt.ask("\n[cyan]Enter model name or number[/cyan]", default=config["default_model"])
                
                # Handle numeric choice
                if model.isdigit() and 1 <= int(model) <= len(available_models):
                    model = available_models[int(model) - 1]
                
                system_prompt = Prompt.ask("[cyan]Enter system prompt (optional)[/cyan]", default="")
                
                # Ask for document context
                use_docs = Prompt.ask("[cyan]Would you like to include documents in the chat context?[/cyan] (y/n)", default="n")
                context_files = []
                if use_docs.lower() == 'y':
                    while True:
                        file_path = Prompt.ask("[cyan]Enter path to document (or press Enter to finish)[/cyan]")
                        if not file_path:
                            break
                        context_files.append(file_path)
                
                chat(model=model, system_prompt=system_prompt if system_prompt else None, context_files=context_files if context_files else None)
            elif command_name == "pull":
                # Special handling for pull to prompt for model name
                model = Prompt.ask("[cyan]Enter model name to download[/cyan]")
                pull(model=model)
            elif command_name == "prompt":
                # Special handling for prompt to get model and prompt text
                config = load_config()
                model = Prompt.ask("[cyan]Enter model name[/cyan]", default=config["default_model"])
                prompt_text = Prompt.ask("[cyan]Enter your prompt[/cyan]")
                prompt(model=model, prompt_text=prompt_text)
            else:
                # Execute the command function
                command_func()
            
            # Pause before showing menu again
            if command_name != "settings":  # Don't show extra prompt for settings
                Prompt.ask("\n[yellow]Press Enter to continue[/yellow]")
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            Prompt.ask("\n[yellow]Press Enter to continue[/yellow]")

def perform_web_search(query: str) -> tuple[list, str]:
    """Perform a web search and return results with content"""
    try:
        print("Starting search...")  # Debug print
        with DDGS() as ddgs:
            # Get search results
            search_results = []
            raw_results = list(ddgs.text(query, max_results=10))
            print(f"Raw results: {raw_results}")  # Debug print
            
            for r in raw_results:
                print(f"Processing result: {r}")  # Debug print
                search_results.append({
                    "title": r.get("title", "No title"),
                    "link": r.get("link", ""),
                    "snippet": r.get("body", "No description available")
                })
            
            if not search_results:
                return [], ""
            
            # Prepare context for LLM
            context = "Here are the search results:\n\n"
            for i, result in enumerate(search_results, 1):
                context += f"{i}. {result['title']}\n"
                context += f"   URL: {result['link']}\n"
                context += f"   Summary: {result['snippet']}\n\n"
            
            return search_results, context
    except Exception as e:
        print(f"Search error: {str(e)}")  # Debug print
        console.print(f"[red]Error performing web search: {str(e)}[/red]")
        return [], ""

def fetch_webpage_content(url: str) -> str:
    """Fetch and extract text content from a webpage"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an error for bad status codes
        
        if response.status_code == 200:
            # Try to detect the encoding
            if 'charset' in response.headers.get('content-type', '').lower():
                response.encoding = response.apparent_encoding
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'header', 'footer', 'nav']):
                element.decompose()
            
            # Convert HTML to markdown-like text
            h = html2text.HTML2Text()
            h.ignore_links = True
            h.ignore_images = True
            h.ignore_tables = True
            h.body_width = 0  # Don't wrap text
            text = h.handle(str(soup))
            
            # Clean up the text
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = ' '.join(lines)
            
            # Remove multiple spaces and normalize whitespace
            text = ' '.join(text.split())
            
            # Limit text length
            return text[:2000]  # Limit to first 2000 chars to avoid overloading the LLM
    except requests.RequestException as e:
        console.print(f"[dim red]Network error fetching {url}: {str(e)}[/dim red]")
    except Exception as e:
        console.print(f"[dim red]Error processing {url}: {str(e)}[/dim red]")
    return ""

def process_enhanced_search(query: str, model: str) -> None:
    """Process an enhanced search query with web results"""
    try:
        # Strip the "search:" prefix
        search_query = query.replace("search:", "", 1).strip()
        
        with console.status("[cyan]Searching the web...[/cyan]"):
            results, context = perform_web_search(search_query)
        
        if not results:
            console.print("[red]No search results found.[/red]")
            return
        
        # Prepare system prompt for analysis
        system_prompt = """You are a helpful AI assistant that analyzes search results and provides comprehensive summaries. 
        For the given query, analyze the search results and provide:
        1. A clear, concise answer or summary
        2. Key points from multiple sources
        3. Any relevant caveats or limitations
        Base your response only on the provided search results."""
        
        # Prepare the prompt for the LLM
        prompt = f"Query: {search_query}\n\nPlease analyze these search results and provide a comprehensive summary:\n\n{context}"
        
        # Send to Ollama
        with console.status("[cyan]Analyzing search results...[/cyan]"):
            response = requests.post(
                f"{OLLAMA_API}/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "stream": False
                }
            )
        
        if response.status_code == 200:
            # Print the analysis
            console.print("\n[bold cyan]Analysis:[/bold cyan]")
            console.print(Markdown(response.json()["message"]["content"]))
            
            # Print sources
            console.print("\n\n[bold cyan]Sources:[/bold cyan]")
            for i, result in enumerate(results, 1):
                console.print(f"[green]{i}.[/green] {result['title']}")
                console.print(f"   [blue]{result['link']}[/blue]")
        else:
            console.print(f"[red]Error: Failed to analyze results. Status code: {response.status_code}[/red]")
    
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        display_menu()
    else:
        app()
