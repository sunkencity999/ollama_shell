# Fine-Tuning Guide for Ollama Shell

This step-by-step guide will walk you through the process of fine-tuning a language model using Ollama Shell. No prior machine learning experience is required!

## Table of Contents

1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Preparing Your Dataset](#preparing-your-dataset)
4. [Fine-Tuning Process](#fine-tuning-process)
5. [Using Your Fine-Tuned Model](#using-your-fine-tuned-model)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Options](#advanced-options)
8. [Using Datasets from External Sources](#using-datasets-from-external-sources)
9. [Intelligent Dataset Handling](#intelligent-dataset-handling)

## Introduction

Fine-tuning allows you to customize a pre-trained language model for your specific needs. This process adapts the model to:

- Better understand your domain-specific terminology
- Follow your preferred writing style
- Improve responses for your specific use cases
- Reduce hallucinations on topics you care about

Ollama Shell makes fine-tuning accessible to everyone by automating the complex technical aspects while giving you control over the important parameters. The system works directly with your Ollama models, so there's no need to download models from external sources.

## Prerequisites

Before starting, make sure you have:

1. **Ollama Shell installed** - If you haven't installed it yet, follow the instructions in the main README.md file.

2. **Ollama running** - Make sure Ollama is installed and running on your system.

3. **Check your hardware** - Run the following command to see if your hardware supports fine-tuning:

   ```
   /finetune status
   ```

   This will show:
   - Detected hardware (NVIDIA GPU, Apple Silicon, or CPU)
   - Recommended framework (Unsloth or MLX)
   - Required dependencies and their installation status

4. **Install dependencies** - If any dependencies are missing, install them with:

   ```
   /finetune install
   ```

   This might take a few minutes depending on your internet connection.

## Preparing Your Dataset

Fine-tuning requires a dataset of examples showing how you want the model to respond. Let's create a simple dataset:

### Option 1: Use the Sample Dataset

Ollama Shell comes with a sample dataset you can use to test the fine-tuning process:

```
/finetune dataset ./examples/sample_dataset.json
```

This dataset contains 10 example conversations covering various topics. You can use it as a starting point or as a template for creating your own dataset.

### Option 2: Create Your Own JSON Dataset

1. Create a new file named `my_dataset.json` with the following structure:

   ```json
   [
     {
       "instruction": "Explain quantum computing in simple terms.",
       "response": "Quantum computing uses quantum bits or qubits that can be both 0 and 1 at the same time, unlike regular computers that use bits that are either 0 or 1. This allows quantum computers to process certain types of problems much faster than regular computers."
     },
     {
       "instruction": "Write a short poem about artificial intelligence.",
       "response": "Silicon dreams in digital streams,\nLearning patterns, crafting schemes.\nMind of math, soul of code,\nAI walks the human road."
     }
   ]
   ```

   Add 10-20 examples for best results. Each example should include:
   - An instruction or question
   - Your preferred response

2. Save this file somewhere accessible.

### Option 3: Convert Your Chat History

If you've been using Ollama Shell for a while, you can convert your chat history to a training dataset:

1. Export your chat history using the `/export` command
2. Use the `/finetune dataset` command with the exported file

### Importing Your Dataset

Import your dataset with:

```
/finetune dataset /path/to/my_dataset.json
```

You can also drag and drop the file into the terminal after typing `/finetune dataset`.

## Fine-Tuning Process

The fine-tuning process consists of four main steps:

1. **Prepare your dataset**
2. **Create a fine-tuning job**
3. **Start the fine-tuning process**
4. **Export the fine-tuned model**

### Step 1: Prepare Your Dataset

First, you need to prepare your dataset. You can use the `/finetune dataset` command to load your dataset:

```
/finetune dataset /path/to/your/dataset.json
```

You can also drag and drop a file directly into the terminal after typing `/finetune dataset`.

The system will automatically process your dataset and make it available for fine-tuning. The dataset will be assigned an ID (usually based on the filename) that you'll use in the next step.

### Step 2: Create a Fine-Tuning Job

Next, create a fine-tuning job by specifying a name for your job and the base model you want to fine-tune:

```
/finetune create my_job_name llama3.2:latest
```

This will create a new job with default parameters. You can view the job with:

```
/finetune list
```

### Step 3: Start the Fine-Tuning Process

Now you can start the fine-tuning process:

```
/finetune start my_job_name
```

The system will automatically:
1. Detect your hardware and select the appropriate framework (Unsloth for NVIDIA GPUs, MLX for Apple Silicon)
2. Set up the environment with the required dependencies
3. Prepare the model and dataset
4. Start the fine-tuning process

You can monitor the progress with:

```
/finetune list
```

This will show the current status, progress percentage, and estimated time remaining.

#### Framework-Specific Details

##### MLX (Apple Silicon)

For Apple Silicon (M1/M2/M3) Macs, Ollama Shell uses MLX-LM, a specialized framework optimized for Apple's Neural Engine. Key features include:

- Direct integration with Ollama models via the API
- Optimized performance on Apple Silicon
- Lower memory usage compared to traditional fine-tuning
- Automatic installation of required dependencies

The MLX framework is automatically installed from source to ensure compatibility with the latest versions of macOS and Ollama.

MLX-LM is a variant of the MLX framework specifically designed for language models. It provides improved performance and efficiency for fine-tuning language models on Apple Silicon hardware.

##### Unsloth (NVIDIA GPUs)

For systems with NVIDIA GPUs, Ollama Shell uses Unsloth, which provides:

- 2-3x faster fine-tuning compared to traditional methods
- QLoRA for memory-efficient training
- Support for a wide range of Hugging Face models
- Automatic CUDA optimization

### Step 4: Export the Fine-Tuned Model

Once the fine-tuning process is complete, you can export the model to Ollama:

```
/finetune export my_job_name
```

This will:
1. Create a Modelfile with appropriate parameters
2. Register the model with Ollama
3. Make the model available for use in Ollama Shell

You can then use your fine-tuned model just like any other Ollama model:

```
/model my_job_name
```

## Using Your Fine-Tuned Model

To use your fine-tuned model:

1. In Ollama Shell, select your model with:

   ```
   /model llama2-my_first_tuning
   ```

2. Start chatting! Your model should now respond according to the patterns in your training dataset.

3. To compare with the original model, you can switch back with:

   ```
   /model llama2
   ```

## Troubleshooting

### Common Issues and Solutions

1. **"Error installing dependencies"**
   - Make sure you have an internet connection
   - For macOS: Install Homebrew and run `brew install cmake`
   - For NVIDIA GPUs: Ensure CUDA drivers are installed

2. **"Dataset file not found"**
   - Check that the path is correct
   - Try using absolute paths
   - Try drag-and-drop instead of typing the path

3. **"Out of memory error"**
   - Reduce batch_size (e.g., `batch_size=4`)
   - Use a smaller base model

4. **"Training seems slow"**
   - Reduce the number of epochs
   - Use a GPU if available
   - Use a smaller dataset for testing

5. **"Ollama model not found"**
   - Make sure Ollama is running
   - Check that the model name is correct (case-sensitive)
   - Try pulling the model first: `ollama pull modelname`

6. **MLX-specific issues**
   - **"MLX-LM not found"**: The installation may have failed. Try running `/finetune install` again
   - **"Error loading model with MLX"**: Ensure you're using a compatible model (not all models work with MLX)
   - **"AttributeError during training"**: This may indicate a version mismatch. Try reinstalling MLX-LM with `/finetune install`
   - **"Memory allocation failed"**: Reduce the batch size or context length in the parameters

7. **Unsloth-specific issues**
   - **"CUDA out of memory"**: Reduce batch size or use a smaller model
   - **"CUDA not available"**: Make sure your NVIDIA drivers are properly installed
   - **"ImportError: cannot import name 'unsloth'"**: Try reinstalling with `/finetune install`

### Advanced Troubleshooting

If you encounter persistent issues:

1. Check the logs in the job directory:
   ```
   cat ~/ollama_shell_data/finetune/jobs/my_job_name/logs.txt
   ```

2. Try resetting the job status:
   ```
   /finetune reset my_job_name
   ```

3. For MLX-specific issues on Apple Silicon, you can try reinstalling MLX from source:
   ```
   pip uninstall -y mlx mlx-lm
   pip install -U mlx
   git clone https://github.com/ml-explore/mlx-examples.git
   cd mlx-examples/llms/mlx-lm
   pip install -e .
   ```

## Advanced Options

### Framework Selection

Ollama Shell automatically selects the best framework for your hardware:

- **MLX** for Apple Silicon (M1/M2/M3 Macs)
  - Optimized for Apple's Neural Engine
  - Direct integration with Ollama models
  - Uses either mlx-lm or direct MLX implementation

- **Unsloth** for NVIDIA GPUs
  - Optimized for CUDA
  - Significantly faster than standard fine-tuning
  - Low memory usage

You can check which framework will be used with:

```
/finetune status
```

### Custom Training Parameters

Fine-tune your training process with these parameters:

```
/finetune create my_job llama2 epochs=5 learning_rate=0.0001 batch_size=4
```

Available parameters:

| Parameter | Description | Default | Recommended Range |
|-----------|-------------|---------|------------------|
| epochs | Number of training cycles | 3 | 1-10 |
| learning_rate | How quickly the model adapts | 0.0002 | 0.00001-0.001 |
| batch_size | Examples processed at once | 8 | 1-32 |
| cutoff_len | Maximum sequence length | 512 | 128-2048 |

### Dataset Formats

Ollama Shell supports multiple dataset formats:

1. **JSON format** (recommended):
   ```json
   [
     {
       "instruction": "Question or instruction here",
       "response": "Desired response here"
     }
   ]
   ```

2. **CSV format**:
   ```
   instruction,response
   "Question or instruction here","Desired response here"
   ```

3. **TXT format**:
   ```
   Question or instruction here|Desired response here
   ```

4. **Parquet format**:
   Ollama Shell supports Parquet files with columns named:
   - `instruction` (or alternative: question, input, prompt, query)
   - `response` (or alternative: answer, output, completion, result)
   
   This is particularly useful for large datasets as Parquet files are compressed and efficient.
   
   Example usage:
   ```
   /finetune dataset my_dataset.parquet
   ```
   
   Note: Using Parquet files requires the `pandas` and `pyarrow` packages, which will be installed automatically if missing.

### Tips for Better Results

1. **Quality over quantity**: 20 high-quality examples are better than 100 poor ones
2. **Diverse examples**: Include a variety of question types and response styles
3. **Consistent style**: Keep the response style consistent for similar questions
4. **Multiple epochs**: For small datasets, use more epochs (5-10)
5. **Test incrementally**: Start with a small dataset and short training time to test

## Using Datasets from External Sources

Ollama Shell supports various dataset formats for fine-tuning, including JSON, CSV, TXT, and Parquet. However, many datasets available online may require some preprocessing before they can be used with our fine-tuning system. To help with this, we've included a dataset converter script.

### Using the Dataset Converter

The `dataset_converter.py` script in the `examples` directory can help you convert datasets from various sources:

```bash
# Basic usage
python examples/dataset_converter.py --input /path/to/dataset --output /path/to/output.json

# For Git LFS repositories (like HuggingFace datasets)
python examples/dataset_converter.py --input /path/to/dataset --output /path/to/output.json --git-lfs

# For HuggingFace datasets (requires datasets library)
python examples/dataset_converter.py --input dataset_name --output /path/to/output.json --hf
```

### Working with Git LFS Datasets

Many datasets (like those from HuggingFace) use Git LFS (Large File Storage) to store the actual data files. To use these datasets:

1. Install Git LFS:
   ```bash
   brew install git-lfs
   git lfs install
   ```

2. Clone the dataset repository:
   ```bash
   git clone https://huggingface.co/datasets/dataset-name
   ```

3. Pull the LFS files:
   ```bash
   cd dataset-name
   git lfs pull
   ```

4. Use our converter to prepare the dataset:
   ```bash
   python /path/to/examples/dataset_converter.py --input . --output /path/to/output.json --git-lfs
   ```

5. Use the converted dataset with Ollama Shell:
   ```bash
   /finetune dataset /path/to/output.json
   ```

### Supported Dataset Formats

The following formats are supported:

- **JSON**: A list of objects with "instruction" and "response" fields
- **CSV**: A file with "instruction" and "response" columns
- **TXT**: A text file with alternating instructions and responses
- **Parquet**: A columnar storage file with "instruction" and "response" columns

The converter will attempt to map common column names (like "question"/"answer" or "input"/"output") to our expected format.

## Intelligent Dataset Handling

Ollama Shell now includes intelligent dataset handling that can automatically detect and process various dataset formats, including directories containing multiple files. This makes it much easier to use datasets from external sources without manual preprocessing.

### Supported Dataset Formats and Structures

The system can now automatically handle:

1. **Single Files**:
   - JSON files with instruction/response pairs
   - CSV files with instruction/response columns
   - TXT files with alternating paragraphs
   - Parquet files with instruction/response columns

2. **Directories**:
   - Directories containing multiple JSON, CSV, TXT, or Parquet files
   - HuggingFace dataset directories (with dataset_info.json)
   - Directories with mixed file types

3. **Special Dataset Formats**:
   - News article datasets (with headline/article pairs)
   - Question/answer datasets
   - Input/output datasets

### Using Directory-Based Datasets

To use a directory-based dataset, simply provide the directory path to the dataset command:

```bash
/finetune dataset /path/to/dataset/directory
```

The system will:
1. Scan the directory for supported file types
2. Process each file according to its format
3. Extract instruction/response pairs from each file
4. Combine all pairs into a single dataset
5. Save the processed dataset for fine-tuning

### Column Name Mapping

The system automatically maps various column names to the standard "instruction" and "response" format:

- For "instruction": also accepts "input", "question", "prompt", "query"
- For "response": also accepts "output", "answer", "completion", "result"

### Example: Using the AmericanStories Dataset

After downloading the AmericanStories dataset with Git LFS:

```bash
# Navigate to the dataset directory
cd /Users/christopher.bradford/Datasets/AmericanStories

# Pull the actual data files
git lfs pull

# Use the dataset with Ollama Shell
/finetune dataset /Users/christopher.bradford/Datasets/AmericanStories
```

The system will:
1. Find all JSON files in the directory
2. Extract articles from each file
3. Convert headlines and article content into instruction/response pairs
4. Create a fine-tuning dataset

### Example: Using the Open-Platypus Dataset

```bash
# Navigate to the dataset directory
cd /Users/christopher.bradford/Datasets/Open-Platypus

# Pull the actual data files
git lfs pull

# Use the dataset with Ollama Shell
/finetune dataset /Users/christopher.bradford/Datasets/Open-Platypus
```

The system will automatically find and process the Parquet files in the data directory.

---

Happy fine-tuning! With Ollama Shell, you now have the power to create custom AI models tailored to your specific needs.
