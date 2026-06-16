# Ollama Shell

![Ollama Shell Logo](resources/ollama_shell_logo.png)

A powerful interactive shell for Ollama, featuring enhanced chat capabilities, document analysis, image analysis, and real-time web search integration.

Created by Christopher Bradford

Contact: [contact@christopherdanielbradford.com](mailto:contact@christopherdanielbradford.com)

## Features

### Core Features

- Interactive chat with any Ollama model
- Model management (download, delete, list)
- System prompt management and storage
- Chat history with export capabilities (Markdown, HTML, PDF)
- Configurable settings and preferences

### Advanced Features

- Document analysis and question answering
- Image analysis with vision models
- Web search integration
- File creation and management
- Agentic mode for complex tasks
- Enhanced task management for multi-step operations
- Knowledge base integration

## Getting Started

### Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/yourusername/ollama_shell.git
   cd ollama_shell
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Run Ollama Shell**:

   ```bash
   ./ollama_shell.py
   ```

### Requirements

- Python 3.9+
- Ollama installed and running
- Required Python packages (see requirements.txt)

## Usage

### Basic Commands

- `/help` - Display help information
- `/models` - List available models
- `/use [model]` - Switch to a different model
- `/system [prompt]` - Set a system prompt
- `/clear` - Clear the current conversation
- `/exit` - Exit Ollama Shell

### Chat Mode

The default mode is chat, where you can have a conversation with the selected Ollama model:

```bash
You: What is the capital of France?
Ollama: The capital of France is Paris.
```

### Document Analysis

Analyze documents and ask questions about their content:

1. **From Menu**:

   - Select "Analyze Document" from the menu
   - Choose a document file
   - Ask questions about the document

2. **Using Commands**:

   ```bash
   /doc analyze [filename]
   /doc ask [question]
   ```

### Image Analysis

Analyze images using vision models:

1. **From Menu**:

   - Select "Analyze Image" from the menu
   - Choose an image file
   - The model will describe the image

2. **Using Commands**:

   ```bash
   /image analyze [filename]
   ```

### Web Search Integration

Perform web searches directly from Ollama Shell:

1. **Basic Search**:

   ```bash
   /search [query]
   ```

2. **Focused Search**:

   ```bash
   /search --site=wikipedia.org [query]
   ```

3. **Search and Summarize**:

   ```bash
   /search --summarize [query]
   ```

### Agentic Assistant

The Agentic Assistant provides a user-friendly interface for executing complex tasks through natural language instructions:

1. **Basic Usage**:

   ```bash
   # From the main menu, select the "Agentic Assistant" option
   # Or use the command line
   ollama_shell.py assistant
   ```

2. **Example Tasks**:

   - Create files with specific content:

     ```bash
     # In the Agentic Assistant mode
     > Create a Python script that calculates prime numbers and save it to primes.py
     ```

   - Analyze images:

     ```bash
     # In the Agentic Assistant mode
     > Analyze the image sunset.jpg and describe what you see
     ```

   - General task assistance:

     ```bash
     # In the Agentic Assistant mode
     > Help me write a regular expression to match email addresses
     ```

3. **Features**:

   - Intelligent task recognition and routing
   - Support for file creation with natural language descriptions
   - Image analysis capabilities
   - Step-by-step guidance for complex tasks
   - Integration with existing Ollama models

### Enhanced Task Management

The Enhanced Task Management system extends the Agentic Assistant with capabilities for handling complex, multi-step tasks:

1. **Basic Usage**:

   ```bash
   # Use the enhanced assistant CLI
   ./assistant_cli.py interactive
   
   # Or execute a specific task
   ./assistant_cli.py execute "Research the latest gaming news, create a summary document, and find images of the top 3 games mentioned"
   ```

2. **Example Complex Tasks**:

   - Research and document creation:

     ```bash
     # In the Enhanced Assistant mode
     > Research the latest AI advancements and create a report with key findings and images
     ```

   - Multi-step web tasks:

     ```bash
     # In the Enhanced Assistant mode
     > Find the top 5 fishing spots in California, create a guide with details about each location, and include images
     ```

   - File organization with analysis:

     ```bash
     # In the Enhanced Assistant mode
     > Analyze my Python scripts in the src directory, organize them by functionality, and create a summary document
     ```

3. **Key Features**:

   - Task planning and breakdown of complex requests
   - Dependency management between subtasks
   - State persistence across task execution
   - Progress tracking and visualization
   - Workflow management (save, resume, view)

4. **Command-Line Interface**:

   ```bash
   # List saved workflows
   ./assistant_cli.py list
   
   # View workflow details
   ./assistant_cli.py view <workflow_id>
   
   # Resume a workflow
   ./assistant_cli.py resume <workflow_id>
   ```

5. **For more details**:

   See the [Task Management Documentation](TASK_MANAGEMENT.md) for a comprehensive guide to the enhanced task management system.

### Capabilities

The Agentic Mode and Agentic Assistant enable a wide range of complex tasks:

1. **File Operations**:

   - Create, read, update, and delete files
   - Search for files with specific patterns
   - Organize and categorize files

2. **Code Generation and Analysis**:

   - Generate code based on natural language descriptions
   - Analyze and explain existing code
   - Debug and fix issues in code

3. **Web Browsing and Research**:

   - Browse websites and gather information
   - Collect news headlines and summaries
   - Research topics and create reports

4. **Image Analysis and Processing**:

   - Analyze images and describe content
   - Search for and download relevant images
   - Generate image descriptions and captions

5. **Multi-step Task Execution**:

   - Break down complex tasks into manageable steps
   - Track dependencies between subtasks
   - Maintain state across task execution
   - Provide progress updates during execution

## Integrations

### Confluence Integration

Integrate with Atlassian Confluence for document management:

1. **Setup**:

   ```bash
   # Configure Confluence integration
   /confluence setup
   ```

2. **Authentication**:

   ```bash
   # Authenticate with your Confluence instance
   /confluence auth
   ```

3. **Usage**:

   ```bash
   # Search for pages
   /confluence search [query]
   
   # Get page content
   /confluence get [page-id]
   ```

4. **Using the Integration**:
   - Run the `/confluence` command to activate the integration
   - Use natural language to interact with your Confluence instance, for example:
     - "List all spaces in Confluence"
     - "Create a new page titled 'Meeting Notes' in the 'Team' space"

### Jira Integration

Integrate with Atlassian Jira for issue tracking:

1. **Setup**:

   ```bash
   # Configure Jira integration
   /jira setup
   ```

2. **Authentication**:

   ```bash
   # Authenticate with your Jira instance
   /jira auth
   ```

3. **Usage**:

   ```bash
   # Search for issues
   /jira search [query]
   
   # Get issue details
   /jira get [issue-key]
   
   # Create a new issue
   /jira create
   ```

4. **Using the Integration**:
   - Run the `/jira` command to activate the integration
   - Use natural language to interact with your Jira instance, for example:
     - "Show me all open bugs assigned to me"
     - "Create a new task with priority high"

5. **Example Script**:
   - An example script is provided to demonstrate how to use the Jira integration programmatically
   - Located at `examples/jira_example.py`
   - Run the script to see how to search for issues, get issue details, add comments, and update issues:
     ```bash
     python examples/jira_example.py
     ```

### GitHub Integration

Integrate with GitHub for repository management:

1. **Setup**:

   ```bash
   # Configure GitHub integration
   /github setup
   ```

2. **Authentication**:

   ```bash
   # Authenticate with GitHub
   /github auth
   ```

3. **Usage**:

   ```bash
   # List repositories
   /github repos
   
   # Search for code
   /github search [query]
   
   # Get file content
   /github get [repo] [path]
   ```

4. **Using the Integration**:
   - Run the `/github` command to activate the integration
   - Use natural language to interact with GitHub, for example:
     - "Show me my repositories"
     - "Search for 'authentication' in my code"
     - "Get the README from my project"

## Advanced Features

### Fine-Tuning

Fine-tune Ollama models for specific use cases:

1. **Preparing Data**:

   ```bash
   # Create a dataset for fine-tuning
   /finetune create-dataset
   ```

2. **Starting Fine-Tuning**:

   ```bash
   # Start the fine-tuning process
   /finetune start [model] [dataset]
   ```

3. **Fine-Tuning Workflow**:

   ```
   # Install required dependencies based on your hardware
   /finetune install
   
   # Prepare your dataset
   /finetune prepare data.jsonl
   
   # Start fine-tuning
   /finetune start llama2 data.jsonl
   
   # Monitor progress
   /finetune status
   
   # Use the fine-tuned model
   /use my-fine-tuned-model
   ```

### Knowledge Base Integration

Create and use a personal knowledge base:

1. **Setup**:

   ```bash
   # Initialize the knowledge base
   /kb init
   ```

2. **Adding Documents**:

   ```bash
   # Add a document to the knowledge base
   /kb add-doc [filename]
   ```

3. **Querying**:

   ```bash
   # Query the knowledge base
   /kb query [question]
   ```

4. **Commands**:
- `/kb init` - Initialize a new knowledge base
- `/kb add-doc [filename]` - Add a document to your knowledge base
- `/kb add [text]` - Add text to your knowledge base
- `/kb search [query]` - Search your knowledge base for relevant information
- `/kb toggle` - Enable or disable knowledge base integration

## File Creation Commands

Create various types of files using natural language descriptions:

1. **Basic File Creation**:

   ```bash
   /create [filename] [description]
   ```

2. **Code Files**:

   ```bash
   /create-code [filename] [description]
   ```

3. **Document Files**:

   ```bash
   /create-doc [filename] [description]
   ```

4. **Examples**:

   ```bash
   # Create a Python script
   /create script.py "A script that downloads images from a URL"
   
   # Create a configuration file
   /create config.json "Configuration for a web server with the following options: port, host, debug mode"
   
   # Create a documentation file
   /create-doc README.md "Documentation for my project explaining installation and usage"
   ```

## Configuration

Configure Ollama Shell to suit your preferences:

1. **Settings File**:

   The settings are stored in `~/.config/ollama_shell/settings.json`

2. **Configurable Options**:

   - Default model
   - System prompts
   - UI preferences
   - Integration settings
   - Advanced features

3. **Command-Line Configuration**:

   ```bash
   # Set the default model
   /config set default_model llama2
   
   # Enable or disable features
   /config set enable_web_search true
   
   # View current configuration
   /config view
   ```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Ollama](https://github.com/ollama/ollama) for the amazing local LLM runtime
- All contributors who have helped to improve this project
