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

- 🔍 **Enhanced Search & Analysis**: Real-time web search integration with DuckDuckGo
- 🖼️ **Image Analysis**: Support for analyzing images using vision models
- 📄 **Document Analysis**: Support for various document formats
- 🌐 **Real-time Information**: Combine search results with model analysis
- 🏢 **Confluence Integration**: Search and analyze Confluence content with LLM-powered insights
- 💾 **Export Capabilities**: Export chats in multiple formats
- ⚡ **Drag & Drop**: Easy file sharing in chat
- 🧠 **Context Management**: Intelligent management of conversation context
- 📚 **Knowledge Base**: Local vector database for persistent information storage
- 🔧 **Fine-Tuning**: Fine-tune models with Unsloth (NVIDIA) or MLX (Apple Silicon)

## Quick Start

### Unix/Mac Installation

1. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # Unix/Mac
```

1. Install dependencies:

```bash
pip install -r requirements.txt
```

1. Run the application:

```bash
python ollama_shell.py
```

## Tutorial

### Context Management

The Context Management feature allows you to optimize token usage and maintain important information in long conversations:

1. **Pin Important Messages**:

   ```bash
   /pin 5
   ```

   This pins message #5 to ensure it stays in context even as the conversation grows.

2. **Exclude Irrelevant Messages**:

   ```bash
   /exclude 3
   ```

   This excludes message #3 from the context, saving tokens for more relevant information.

3. **Summarize Conversations**:

   ```bash
   /summarize
   ```

   This creates a concise summary of the conversation to save tokens while maintaining context.

4. **View Context Status**:

   ```bash
   /context
   ```

   Shows the current status of your context management, including pinned and excluded messages.

5. **Check Token Usage**:

   ```bash
   /tokens
   ```

   Displays detailed token usage information for each message.

### Enhanced Search Queries

The Enhanced Search feature allows you to combine real-time web information with model analysis:

1. **Basic Search**:

   ```bash
   search: What are the latest developments in AI?
   ```

   This will search the web and provide an analyzed summary.

2. **Focused Questions**:

   ```bash
   search: Who won the latest Super Bowl and what was the score?
   ```

   Gets real-time information and provides accurate, up-to-date answers.

3. **Technical Queries**:

   ```bash
   search: How to implement rate limiting in Python?
   ```

   Combines web search results with model expertise for comprehensive answers.

### Image Analysis

Analyze images using vision models:

1. **From Menu**:
   - Select "Analyze Image" from the menu
   - Enter the path to your image
   - Optionally provide a custom prompt

2. **Drag & Drop**:
   - Press Ctrl+V to toggle drag & drop mode
   - Drag an image file into the terminal
   - The vision model will analyze the image

3. **In Chat Context**:
   - Images can be included in chat for analysis
   - Supported formats: JPG, PNG, GIF, BMP, WebP

### Document Analysis

Analyze various document types:

1. **Supported Formats**:
   - Word Documents (.docx, .doc)
   - Excel Spreadsheets (.xlsx, .xls)
   - PDF Files (.pdf)
   - Text Files (.txt, .md)
   - Code Files (.py, .js, .html, etc.)

2. **Drag & Drop**:
   - Press Ctrl+V to toggle drag & drop mode
   - Drag a document into the terminal
   - The model will analyze the document content

3. **File Creation**:
   - Create files directly from the chat using the `/create` command
   - Standard syntax: `/create [filename] [content]`
   - Natural language syntax: `/create a haiku about nature and save to nature.txt`
   - Example: `/create data.csv "Name,Age,City\nJohn,30,New York\nJane,25,Boston"`
   - Supported formats: TXT, CSV, DOC/DOCX, XLS/XLSX, PDF

### Natural Language Filesystem Operations

Interact with your filesystem using natural language commands through the Filesystem MCP Protocol integration:

1. **Basic Usage**:

   ```bash
   /fsnl list files in my Documents folder
   ```

   This will list all files and directories in your Documents folder.

2. **Supported Operations**:
   - **List Directories**: View contents of directories

     ```bash
     /fsnl show me what's in my Downloads folder
     ```

   - **Create Directories**: Create new folders

     ```bash
     /fsnl create a new folder called 'ProjectData' in my Documents
     ```

   - **Read Files**: View the contents of text files

     ```bash
     /fsnl show me the contents of config.json
     ```

   - **Write Files**: Create or modify text files

     ```bash
     /fsnl create a file called notes.txt in Documents with the text "Meeting notes for today"
     ```

   - **Find Files**: Search for files matching patterns

     ```bash
     /fsnl find all PDF files in my Documents folder
     ```

   - **Delete Files**: Remove files (use with caution)

     ```bash
     /fsnl delete the temporary file temp.txt
     ```

3. **Path Handling**:
   - Supports absolute paths: `/Users/username/Documents`
   - Supports relative paths: `Documents/ProjectData`
   - Supports user home shortcuts: `~/Documents` or just `Documents`
   - Handles special paths like `/Documents` (automatically maps to user's Documents folder)

4. **Best Practices**:
   - Be specific about file and directory names to avoid ambiguity
   - Use full paths when working with files outside common directories
   - Verify operations before deleting files or overwriting important data
   - For complex operations, break them down into multiple commands
   - Use the model's capabilities to explain file contents or summarize directory listings

5. **Security Features**:
   - Operations are limited to user-accessible directories
   - Sensitive system directories are protected
   - All operations are executed with user permissions

### Confluence Integration

Interact with your Confluence instance (both Cloud and Server) using natural language commands through the Confluence MCP Protocol integration:

1. **Automatic Setup During Installation**:
   - During installation, you'll be prompted to set up the Confluence integration
   - If you choose to set it up, a configuration file will be created at `Created Files/confluence_config.env`
   - You can edit this file to provide your Confluence details

2. **Manual Setup**:
   - Copy the template file from `Created Files/config/confluence_config_template.env` to `Created Files/confluence_config.env`
   - Edit the file to provide your Confluence details:
   - For detailed instructions, see the [Comprehensive Setup Guide](docs/confluence_setup_guide.md)

     ```env
     # Confluence Configuration
     
     # Confluence URL (e.g., https://wiki.example.com or https://your-domain.atlassian.net)
     CONFLUENCE_URL=https://your-confluence-url
     
     # Your username/email for Confluence
     CONFLUENCE_EMAIL=your.email@example.com
     
     # Your Personal Access Token (PAT) or API token
     CONFLUENCE_API_TOKEN=your_token_here
     
     # Authentication method (basic, bearer, or pat)
     CONFLUENCE_AUTH_METHOD=pat
     
     # Is this a Confluence Cloud instance? (true/false)
     CONFLUENCE_IS_CLOUD=false
     ```


3. **Authentication Methods**:
   - **Confluence Server**: Use a Personal Access Token (PAT) with the `pat` authentication method
   - **Confluence Cloud**: Use an API token with the `basic` authentication method

4. **Using the Integration**:
   - Run the `/confluence` command to activate the integration
   - Use natural language to interact with your Confluence instance, for example:
     - "List all spaces in Confluence"
     - "Create a new page titled 'Meeting Notes' in the 'Team' space"
     - "Search for pages about 'project planning'"
     - "Get the content of the 'Home' page in the 'Documentation' space"

5. **API Tokens**:
   - For Confluence Cloud: Generate an API token at [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
   - For Confluence Server: Generate a Personal Access Token in your Confluence Server instance
   - Configuration will be saved securely as environment variables

6. **Testing Your Configuration**:
   - Run the test script to verify your Confluence setup:

     ```bash
     python test_confluence_setup.py
     ```


   - The script will check your configuration file, validate settings, and test the connection to your Confluence instance

7. **Troubleshooting**:
   - If you encounter issues with the Confluence integration, refer to the [Confluence Troubleshooting Guide](docs/confluence_troubleshooting.md)
   - The guide covers common problems with connection, authentication, and permissions

8. **Example Script**:
   - An example script is provided to demonstrate how to use the Confluence integration programmatically
   - Located at `examples/confluence_example.py`
   - Run the script to see how to connect to Confluence, list spaces, and search for content:

     ```bash
     python examples/confluence_example.py
     ```

9. **Supported Operations**:
   - **List Spaces**: View all accessible spaces in your Confluence instance

     ```bash
     list all spaces
     ```
   - **Get Space Details**: View details about a specific space

     ```bash
     show me details about the Engineering space
     ```
   - **List Pages**: View pages in a specific space

     ```bash
     list all pages in the Marketing space
     ```
   - **Get Page Content**: View the content of a specific page

     ```bash
     show me the content of the "Project Roadmap" page
     ```
   - **Create Pages**: Create new pages in a space

     ```bash
     create a new page titled "Meeting Notes" in the Team space with content "Notes from today's meeting"
     ```
   - **Update Pages**: Update existing pages

     ```bash
     update the "Weekly Status" page in the Project space with new content
     ```
   - **Search Content**: Search for content using Confluence Query Language (CQL)

     ```text
     search for pages containing "budget proposal"
     ```

     For more targeted searches, use specific query formats:

     ```text
     search Confluence for information about Polarion
     ```

     ```text
     find all Confluence pages containing "API documentation"
     ```

     ```text
     search Confluence for "release planning"
     ```

   - **Content Analysis**: Get AI-powered analysis of search results

     ```text
     analyze Confluence content about "deployment procedures"
     ```

     ```text
     explain the information in Confluence about SSL certificates
     ```

     The LLM will automatically analyze search results to provide direct answers to your queries, extracting relevant information from multiple pages.

   - **Manage Labels**: Add or remove labels from pages

     ```text
     add labels "important,review" to the "Quarterly Report" page
     ```

3. **Best Practices**:
   - Be specific about space and page names to avoid ambiguity
   - For complex operations, break them down into multiple commands
   - Use the model's capabilities to summarize or explain page content

### Jira Integration

Ollama Shell includes a powerful Jira integration that allows you to interact with Jira through natural language commands.

1. **Setup**:
   - Run the `/jira setup` command to configure the integration
   - You'll be prompted to enter your Jira URL, user email, and API token
   - For detailed setup instructions, see the [Jira Setup Guide](docs/jira_setup_guide.md)

2. **Authentication**:
   - Generate an API token at [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
   - Use your Atlassian account email address
   - Configuration will be saved securely as environment variables

3. **Testing Your Configuration**:
   - After setup, test your configuration with:

     ```bash
     /jira status
     ```

4. **Troubleshooting**:
   - If you encounter issues with the Jira integration, refer to the [Jira Troubleshooting Guide](docs/jira_troubleshooting.md)
   - The guide covers common problems with connection, authentication, and JQL queries

5. **Example Script**:
   - An example script is provided to demonstrate how to use the Jira integration programmatically
   - Located at `examples/jira_example.py`
   - Run the script to see how to search for issues, get issue details, add comments, and update issues:

     ```bash
     python examples/jira_example.py
     ```

6. **Supported Operations**:
   - **Natural Language Search**: Find issues using intuitive natural language queries

     ```text
     /jira search highest priority bugs
     ```

     ```text
     /jira find issues assigned to me and status = "In Progress"
     ```

     The natural language query processor supports a wide range of query patterns:
     
     ```text
     /jira show high priority issues assigned to me
     ```
     
     ```text
     /jira display issues assigned to John Smith except for closed items
     ```
     
     ```text
     /jira find open bugs with high priority in the PROJECT project
     ```
     
     ```text
     /jira list all unresolved issues created this week
     ```
     
     The system intelligently handles various priority formats (P2, High Priority), resolution statuses, and assignee specifications to generate the correct JQL query.

   - **Get Issue Details**: View detailed information about a specific issue

     ```text
     /jira get PROJECT-123
     ```

   - **Add Comments**: Add comments to issues

     ```text
     /jira comment PROJECT-123 This is a comment added via Ollama Shell
     ```

   - **Update Issues**: Update issue fields such as status, priority, or assignee

     ```text
     /jira update PROJECT-123 status "In Progress"
     ```

   - **Issue Analysis**: Get AI-powered analysis of issues

     ```text
     /jira analyze PROJECT-123
     ```

     The LLM will automatically analyze the issue details to provide insights, identify key points from the description, current status, next steps, and recommendations for resolution.

### Context Management

The Context Management feature allows you to optimize token usage and maintain important information in long conversations:

1. **Pin Important Messages**:

   ```bash
   /pin 5
   ```

   This pins message #5 to ensure it stays in context even as the conversation grows.

2. **Exclude Irrelevant Messages**:

   ```bash
   /exclude 3
   ```

   This excludes message #3 from the context, saving tokens for more relevant information.

3. **Summarize Conversations**:

   ```bash
   /summarize
   ```

   This creates a concise summary of the conversation to save tokens while maintaining context.

4. **View Context Status**:

   ```bash
   /context
   ```

   Shows the current status of your context management, including pinned and excluded messages.

5. **Check Token Usage**:

   ```bash
   /tokens
   ```

   Displays detailed token usage information for each message.

### Knowledge Base
Store and retrieve information using a local vector database:

1. **Features**:
   - Persistent storage across sessions
   - Semantic search for relevant information
   - Automatic integration with chat context
   - Vector embeddings for similarity matching

2. **Usage**:
   - Add important information with `/kb add [text]`
   - Search the knowledge base with `/kb search [query]`
   - Enable/disable with `/kb toggle`
   - View status with `/kb status`

3. **Benefits**:
   - Remember important facts between sessions
   - Build a personalized knowledge repository
   - Automatically enhance responses with relevant context
   - Reduce repetitive questions

4. **Adding Documents**:
   - Drag & drop documents directly into the chat
   - Choose to add them to the knowledge base when prompted
   - Documents are automatically chunked for optimal storage
   - Search across all documents with `/kb search [query]`

### Fine-Tuning
Fine-tune models using a modular system that supports Unsloth (for NVIDIA GPUs) or MLX (for Apple Silicon):

1. **Features**:
   - Modular architecture for better maintainability and extensibility
   - Automatic hardware detection for optimal framework selection
   - Support for Unsloth on NVIDIA GPUs
   - Support for MLX on Apple Silicon
   - Direct integration with Ollama models
   - CPU fallback for other systems
   - Dataset preparation from various formats
   - Detailed progress tracking with ETA estimation
   - Job control (pause, resume, delete)
   - Easy export to Ollama

2. **Prerequisites**:
   - For macOS users:
     - Homebrew (`brew`) is required
     - `cmake` is needed (will be installed automatically if missing)
   - For NVIDIA GPU users:
     - CUDA drivers must be installed
     - `nvidia-smi` should be available in your path

3. **Fine-Tuning Workflow**:
   ```
   # Install required dependencies based on your hardware
   /finetune install
   
   # Check system status and hardware detection
   /finetune status
   
   # Prepare a dataset for fine-tuning
   /finetune dataset /path/to/your/dataset.json
   
   # List available datasets
   /finetune datasets
   
   # Create a fine-tuning job
   /finetune create my_job_name llama3.2:latest
   
   # Change dataset for the job (optional)
   /finetune dataset-set my_job_name another_dataset_id
   
   # Start the fine-tuning process
   /finetune start my_job_name
   
   # Monitor progress
   /finetune list
   
   # Export the fine-tuned model to Ollama
   /finetune export my_job_name
   
   # Remove unused datasets (optional)
   /finetune dataset-remove dataset_id
   ```

4. **Supported Dataset Formats**:
   - JSON: List of objects with "text" field or "prompt"/"completion" fields
   - JSONL: One JSON object per line
   - CSV: With header row and text column
   - TXT: Plain text files (one sample per line)

5. **Framework-Specific Notes**:
   - **MLX (Apple Silicon)**:
     - Uses MLX-LM for efficient fine-tuning on Apple Silicon
     - Automatically installed from source to ensure compatibility
     - Directly integrates with Ollama models via the API
     - Optimized for M1/M2/M3 chips
   - **Unsloth (NVIDIA)**:
     - Uses Unsloth for 2-3x faster fine-tuning on NVIDIA GPUs
     - Supports QLoRA for memory-efficient training
     - Compatible with most Hugging Face models

6. **Testing Your Fine-Tuned Model**:
   ```
   # Switch to your fine-tuned model
   /model my_job_name
   
   # Test with different prompts to see how it performs
   What is the capital of France?
   
   # Compare with the original model
   /model llama3.2:latest
   What is the capital of France?
   
   # You can also use the /compare command to test both models side by side
   /compare my_job_name llama3.2:latest "What is the capital of France?"
   ```

## Supported File Formats

### Documents
- 📝 Word Documents (.docx, .doc)
- 📊 Excel Spreadsheets (.xlsx, .xls)
- 📄 PDF Files (.pdf)
- ✍️ Text Files (.txt, .md)
- 💻 Code Files (.py, .js, .html, .css, .json, .yaml, .yml)

### Images
- 🖼️ JPEG/JPG
- 🎨 PNG
- 🎭 GIF
- 🖌️ BMP
- 🌅 WebP

### Export Formats
- 📝 Markdown
- 🌐 HTML
- 📑 PDF

## Dependencies
- Python 3.8+
- Ollama with compatible models
- See `requirements.txt` for full list

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ollama_shell.git
   cd ollama_shell
   ```

2. Run the installation script:

   **On macOS/Linux:**
   ```bash
   ./install.sh
   ```

   **On Windows:**
   ```bash
   install.bat
   ```
   
   This will:
   - Create the `Created Files` directory for storing user data
   - Set up a virtual environment (if not already present)
   - Install all required dependencies
   - Configure the application for first use

## Configuration
Configuration is stored in `config.json` and includes:
- Default model settings
- Vision model preferences
- History and logging preferences
- UI customization options

## Tips & Tricks
- Use `Ctrl+V` to toggle drag & drop mode
- Combine search and document analysis for comprehensive answers
- Save frequently used prompts for quick access
- Export important conversations for future reference
- Use custom prompts with image analysis for specific insights
- Use `/pin` to keep important context in long conversations
- Use `/summarize` to condense long conversations while maintaining context
- Use the knowledge base to store and retrieve important information across sessions
- Add documents to your knowledge base via drag & drop for persistent access to their content

## User Data and Files

Ollama Shell stores user-specific data in the `Created Files` directory, which is excluded from Git to protect your privacy and prevent accidental sharing of personal data. This includes:

- **Fine-tuning jobs**: All fine-tuning job data, including models and logs
- **Datasets**: Prepared datasets for fine-tuning
- **Configuration**: User-specific configuration files
- **Generated models**: Model files created during fine-tuning

This separation ensures that your personal models, datasets, and configurations remain private and are not accidentally committed to version control.

## Context Management Commands
- `/pin [message_number]` - Pin a message to keep it in context
- `/unpin [message_number]` - Unpin a previously pinned message
- `/exclude [message_number]` - Exclude a message from context
- `/include [message_number]` - Include a previously excluded message
- `/summarize` - Summarize the conversation to save tokens
- `/context` - Show current context management status
- `/tokens` - Show token usage information
- `/help` - Show context management help

## Knowledge Base Commands
- `/kb status` - Show knowledge base status and statistics
- `/kb add [text]` - Add text to your knowledge base
- `/kb search [query]` - Search your knowledge base for relevant information
- `/kb toggle` - Enable or disable knowledge base integration

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License
MIT License - See LICENSE file for details
