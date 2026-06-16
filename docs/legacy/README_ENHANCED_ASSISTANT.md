# Enhanced Agentic Assistant for Ollama Shell

This document provides information about the Enhanced Agentic Assistant feature in Ollama Shell, which enables complex task execution through natural language commands.

## Overview

The Enhanced Agentic Assistant extends the original Assistant with advanced task management capabilities, allowing it to:

1. Break down complex tasks into manageable subtasks
2. Execute tasks with dependencies in the correct order
3. Maintain state between task steps
4. Handle errors and recovery gracefully
5. Provide detailed progress and results

## Using the Enhanced Assistant

You can access the Enhanced Agentic Assistant in two ways:

### 1. Through the Ollama Shell Menu

1. Launch Ollama Shell:
   ```bash
   ./ollama_shell.py
   ```

2. Select option `13` (or the corresponding number) for "Enhanced Agentic Assistant"

3. Enter your task in natural language, for example:
   - "Research the latest AI advancements, create a summary document, and find images of the top 3 AI systems mentioned"
   - "Analyze the performance data in my spreadsheet, create a chart, and write a report with recommendations"
   - "Find information about fishing techniques, organize it by difficulty level, and save it to a markdown file"

### 2. Through the Command-Line Interface

For direct access to the Enhanced Assistant, use:

```bash
./assistant_cli.py interactive
```

Or execute a specific task:

```bash
./assistant_cli.py execute "Research the latest AI advancements and create a summary"
```

## Features

### Complex Task Detection

The Enhanced Assistant automatically detects complex tasks that require multiple steps. It looks for:

- Multiple action verbs (create, find, analyze, etc.)
- Sequence indicators (and then, followed by, etc.)
- Multiple objectives (and also, additionally, etc.)
- Explicit multi-step requests

### Task Planning

When a complex task is detected, the Assistant:

1. Analyzes the task using an LLM
2. Breaks it down into subtasks
3. Determines dependencies between subtasks
4. Creates a visual execution plan
5. Executes the tasks in the correct order

### Web Integration

The Enhanced Assistant includes improved web browsing capabilities:

- Intelligent topic detection for different content types (news, gaming, tech, etc.)
- Dynamic category detection without requiring hardcoded patterns
- Expanded website selection system with more categories
- Better information gathering with structured, actionable information
- Improved headline extraction with direct HTML parsing

### File Management

All files created by the Enhanced Assistant are saved to the Documents folder by default, making them easy to find. The system:

- Creates appropriate default filenames based on content type
- Respects user-specified filenames when provided
- Returns full paths in responses for better user feedback
- Creates any necessary parent directories automatically

## Examples

### Example 1: Research Task

```
Research the latest advancements in quantum computing and create a summary document
```

The Enhanced Assistant will:
1. Research quantum computing advancements from reliable sources
2. Extract key information and organize it
3. Create a well-formatted summary document in your Documents folder
4. Provide a preview of the content

### Example 2: Web Browsing Task

```
Get me the latest gaming headlines
```

The Enhanced Assistant will:
1. Identify this as a gaming content request
2. Visit appropriate gaming websites (IGN, GameSpot, Polygon, etc.)
3. Extract headlines using direct HTML parsing
4. Save the results to "gameSummary.txt" in your Documents folder
5. Display sample headlines in the output

### Example 3: Multi-step Analysis

```
Analyze the data in performance.csv, create a visualization, and write a report with recommendations
```

The Enhanced Assistant will:
1. Read and analyze the CSV data
2. Generate appropriate visualizations
3. Create a report with insights and recommendations
4. Save both the report and visualizations to your Documents folder

## Technical Details

For more information about the technical implementation, see the [TASK_MANAGEMENT.md](TASK_MANAGEMENT.md) file.
