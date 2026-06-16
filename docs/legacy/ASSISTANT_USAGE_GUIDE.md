# Enhanced Agentic Assistant Usage Guide

This guide provides practical examples and tips for using the Enhanced Agentic Assistant in Ollama Shell.

## Getting Started

To use the Enhanced Agentic Assistant:

1. Launch Ollama Shell:
   ```bash
   ./ollama_shell.py
   ```

2. Select option `13` for "Enhanced Agentic Assistant"

3. Enter your task in natural language

## Effective Task Formulation

The Enhanced Assistant works best when tasks are clearly described. Here are some tips:

### Be Specific

Instead of:
```
Find information about AI
```

Try:
```
Find information about the latest AI advancements in natural language processing from the past year
```

### Include Desired Output Format

Instead of:
```
Research quantum computing
```

Try:
```
Research quantum computing and create a markdown document with key concepts, recent breakthroughs, and future applications
```

### Specify Steps When Helpful

Instead of:
```
Help me analyze this data
```

Try:
```
Analyze the data in sales.csv, create a chart showing monthly trends, and write a summary of key insights
```

## Task Categories and Examples

### Web Research

```
Research the latest developments in renewable energy and create a summary document with key innovations
```

```
Find information about healthy Mediterranean diet recipes and save them to a markdown file
```

```
Get the latest tech headlines from major technology news sites
```

### File Creation and Management

```
Create a Python script that analyzes CSV data and generates statistics
```

```
Write a bash script that backs up important files to a specified directory
```

```
Create a markdown document explaining the basics of machine learning with examples
```

### Data Analysis

```
Analyze the data in performance.csv, identify trends, and create a summary report
```

```
Review the sales figures in quarterly_results.xlsx and create a presentation with key insights
```

```
Extract the main points from meeting_notes.txt and organize them by topic
```

### Multi-step Tasks

```
Research the top 5 machine learning frameworks, compare their features, and create a recommendation document
```

```
Find information about climate change impacts, organize it by region, and create a visual representation of the data
```

```
Analyze the code in app.py, identify potential bugs, and suggest improvements with code examples
```

## Web Browsing Features

The Enhanced Assistant has specialized handling for different content types:

### News Headlines

```
Get me the latest news headlines
```

Saves to: `newsSummary.txt` in your Documents folder

### Gaming Information

```
Find the latest gaming news and reviews
```

Saves to: `gameSummary.txt` in your Documents folder

### Technology Updates

```
Get me the latest tech news
```

Saves to: `techSummary.txt` in your Documents folder

### Custom Topics

```
Find information about fishing techniques for beginners
```

The system will automatically:
1. Detect "fishing" as the topic
2. Find appropriate websites
3. Extract relevant information
4. Save to an appropriately named file in your Documents folder

## Advanced Usage

### Task History

To view your task history:

```bash
./assistant_cli.py history
```

### Workflow Management

To list all workflows:

```bash
./assistant_cli.py workflows
```

To view a specific workflow:

```bash
./assistant_cli.py workflow <workflow_id>
```

### Debugging

If a task doesn't produce the expected results, try:

1. Breaking it down into smaller, more specific tasks
2. Checking the task history for any errors
3. Reviewing the generated files in your Documents folder

## Tips and Best Practices

1. **Start Simple**: Begin with straightforward tasks before moving to complex ones
2. **Be Clear**: Clearly state what you want to accomplish
3. **Provide Context**: Include relevant information that might help with the task
4. **Review Results**: Always review the output to ensure it meets your needs
5. **Iterate**: If needed, refine your request based on the initial results
