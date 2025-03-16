# Agentic Mode Integration for Ollama Shell

This guide provides detailed information on using the Agentic Mode integration with Ollama Shell to perform complex agentic tasks using local LLMs.

## Overview

Agentic Mode is a powerful agent framework that enables LLMs to perform complex tasks by breaking them down into smaller steps and executing them. The integration with Ollama Shell allows you to leverage this capability using your local Ollama models, providing a privacy-focused alternative to cloud-based agent services.

## Installation

### Prerequisites

- Ollama installed and running
- Python 3.10 or higher
- Ollama Shell installed

### Installing Agentic Mode

You can install Agentic Mode directly from within Ollama Shell:


```bash
/agentic --install

```


You'll be prompted to choose between two installation methods:

1. **uv** (recommended): A fast Python package installer
2. **conda**: Useful if you're already using a conda environment

The installation process will:

- Clone the Agentic Mode repository
- Install required dependencies
- Set up the necessary configuration files


## Configuration

After installation, you need to configure Agentic Mode to work with your Ollama models:


```bash
/agentic --configure --model llama3

```


This will:

1. Create a configuration file in the `.agentic_mode` directory
2. Set up the connection to your local Ollama instance
3. Configure the specified model as the default for task execution


You can view and manually edit the configuration file at `~/.agentic_mode/config.toml` if needed.

## Using Agentic Mode

### Command Syntax

The basic syntax for using the Agentic Mode integration is:

```bash
/agentic [task description]
```

Additional options include:
- `--mode` or `-m`: Enter interactive agentic mode
- `--model [model_name]`: Specify which Ollama model to use
- `--install` or `-i`: Install Agentic Mode
- `--configure` or `-c`: Configure Agentic Mode

### Interactive Mode

Interactive mode provides a dedicated interface for working with the agent:


```bash
/agentic --mode

```


In this mode, you can:
- Have multi-turn conversations with the agent
- Execute multiple related tasks
- Provide feedback on task execution
- Access the agent's working memory

To exit interactive mode, type `exit` or `quit`.

## Task Types

Agentic Mode can handle a wide variety of tasks:

### File System Operations


```bash
# List and organize files
/agentic Find all PDF files in my Downloads folder and organize them by date

# Search for specific content
/agentic Find all Python files containing database connection code

# Create directory structures
/agentic Create a project structure for a new React application

```


### Code Generation and Analysis


```bash
# Generate new code
/agentic Create a Python script that downloads stock data and creates a chart

# Analyze existing code
/agentic Analyze my JavaScript file and suggest performance improvements

# Refactoring
/agentic Refactor my Python script to use async/await instead of callbacks

```


### Data Processing


```bash
# Data extraction
/agentic Extract all email addresses from this text file

# Data transformation
/agentic Convert this CSV file to JSON format

# Data analysis
/agentic Analyze this sales data and create a summary report

```


### Web Interactions


```bash
# Information gathering
/agentic Find the latest news about artificial intelligence

# Content summarization
/agentic Summarize the content of this webpage

# Research
/agentic Research the top 5 Python libraries for machine learning

```


## Advanced Usage

### Chaining Tasks

You can chain multiple tasks together in interactive mode:


```

> /agentic --mode
Agent: I'm ready to help you with complex tasks. What would you like me to do?

You: First, find all Python files in my project
Agent: [executes task and shows results]

You: Now analyze their complexity
Agent: [analyzes files and provides complexity metrics]

You: Create a report summarizing your findings
Agent: [generates a report based on the analysis]

```


### Using Different Models

Different models have different strengths. Here are some recommendations:

- **llama3**: Good general-purpose model for most tasks
- **codellama**: Excellent for code-related tasks
- **mistral**: Good balance of speed and capability
- **llama3.2-vision**: Required for tasks involving image analysis

Example:

```bash
/agentic --model codellama Refactor this Python code to be more efficient

```


### Working with Files

When working with files, you can:

1. **Reference specific files**:
   
```bash
   /agentic Analyze the code in app.py
   
```


2. **Use wildcards**:
   
```bash
   /agentic Find all *.log files older than 30 days
   
```


3. **Specify paths**:
   
```bash
   /agentic Create a backup of ~/Documents/important_files
   
```


## Troubleshooting

### Common Issues

1. **Model Not Found**:
   - Error: "Model [model_name] not found"
   - Solution: Pull the model using `/pull [model_name]`

2. **Task Execution Timeout**:
   - Error: "Task execution timed out"
   - Solution: Break down the task into smaller steps or use a more capable model

3. **Permission Errors**:
   - Error: "Permission denied when accessing [file/directory]"
   - Solution: Ensure Ollama Shell has the necessary permissions

4. **Configuration Issues**:
   - Error: "Failed to load Agentic Mode configuration"
   - Solution: Run `/agentic --configure` to recreate the configuration

### Getting Help

If you encounter issues not covered in this guide:

1. Check the Agentic Mode documentation
2. Use the `/help` command in Ollama Shell for a quick reference
3. Join the Ollama community for support

## Best Practices

1. **Start Simple**: Begin with straightforward tasks before attempting complex ones
2. **Be Specific**: Provide clear and detailed instructions
3. **Use the Right Model**: Choose models based on the task requirements
4. **Provide Context**: In interactive mode, give context for better results
5. **Review Results**: Always review the agent's output before using it

## Examples

### Example 1: File Organization


```bash
/agentic Find all images in my Downloads folder, create a new folder called 'Images' in my Documents, and move them there

```


### Example 2: Code Generation


```bash
/agentic Create a Python script that connects to a PostgreSQL database, queries the 'users' table, and exports the results to a CSV file

```


### Example 3: Data Analysis


```bash
/agentic Analyze the sales.csv file, calculate monthly revenue trends, and create a summary report with the top 5 products

```


### Example 4: Research and Summarization


```bash
/agentic Research the latest advancements in quantum computing and create a brief summary

```


## Conclusion

The Agentic Mode integration brings powerful agentic capabilities to Ollama Shell, allowing you to perform complex tasks using natural language commands and local LLMs. By following this guide, you can leverage the full potential of this integration to automate and streamline your workflow.
