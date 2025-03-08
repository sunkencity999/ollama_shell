# Fine-Tuning Guide for Ollama Shell

This guide explains how to use the fine-tuning capabilities in Ollama Shell to create custom models tailored to your specific needs.

## Overview

Ollama Shell provides an integrated fine-tuning system that automatically detects your hardware and selects the appropriate framework:

- **MLX**: For Apple Silicon (M1/M2/M3 Macs)
- **Unsloth**: For NVIDIA GPUs (Linux/Windows)
- **CPU Fallback**: For other platforms

## Getting Started

### 1. Check Your Hardware

First, check what hardware you have and if all dependencies are installed:

```
/finetune status
```

This will show your detected hardware, the framework that will be used, and the status of required dependencies.

### 2. Install Dependencies

If dependencies are missing, install them with:

```
/finetune install
```

This will install the appropriate framework and dependencies based on your hardware.

### 3. Prepare a Dataset

Fine-tuning requires a dataset. Ollama Shell supports various dataset formats and sources:

#### Local JSONL Files

The simplest approach is using a local JSONL file:

```
/finetune dataset path/to/your/dataset.jsonl
```

The dataset should be in JSONL format with "input" and "output" fields, for example:

```json
{"input": "What is the capital of France?", "output": "The capital of France is Paris."}
{"input": "Who wrote Romeo and Juliet?", "output": "William Shakespeare wrote Romeo and Juliet."}
```

#### Supported Dataset Formats

Ollama Shell supports various dataset formats:

- **JSONL**: The preferred format with "input" and "output" fields
- **JSON**: Standard JSON files with appropriate fields
- **CSV/TSV**: Tabular data with column headers
- **TXT**: Plain text files for simple datasets

```
/finetune dataset path/to/dataset.json
```

```
/finetune dataset path/to/dataset.csv
```

When using CSV files, you'll be prompted to specify which columns contain the input and output text.

#### Dataset Parameters

You can customize dataset processing with parameters:

```
/finetune dataset path/to/dataset.jsonl --name custom_name
```

This assigns a custom name to the dataset for easier reference.

#### Using Datasets with Jobs

When creating a fine-tuning job, you can specify which dataset to use:

```
/finetune create job_name base_model --dataset dataset_name
```

You can also update the dataset for an existing job:

```
/finetune dataset-set job_name dataset_name
```

To see all available datasets:

```
/finetune datasets
```

### 4. Create a Fine-Tuning Job

Create a new fine-tuning job with:

```
/finetune create job_name base_model
```

For example:

```
/finetune create my_assistant llama3
```

This will create a new job using the specified base model.

### 5. Start the Fine-Tuning Process

Start the fine-tuning process with:

```
/finetune start job_name
```

This will begin the fine-tuning process. The time required depends on your hardware, dataset size, and model size.

### 6. Monitor Progress

Check the status of your fine-tuning job:

```
/finetune status job_name
```

### 7. Export the Model to Ollama

Once fine-tuning is complete, export the model to Ollama:

```
/finetune export job_name
```

This will create a new model in Ollama that you can use with the `/model` command.

## Advanced Options

### Dataset Management

Ollama Shell provides commands for managing your datasets:

#### Listing Datasets

View all available datasets:

```
/finetune datasets
```

This shows all datasets that have been prepared for fine-tuning.

#### Removing Datasets

Remove a dataset when it's no longer needed:

```
/finetune dataset-remove dataset_name
```

If the dataset is in use by a job, you'll need to use the `--force` flag:

```
/finetune dataset-remove dataset_name --force
```

#### Updating Datasets for Jobs

Change which dataset a job uses:

```
/finetune dataset-set job_name dataset_name
```

This allows you to experiment with different datasets for the same job.

#### Dataset Inspection

You can inspect the contents of a dataset using the `/create` command:

```
/create preview of dataset dataset_name
```

This will show a sample of the dataset contents to verify it's formatted correctly.

### Customizing Fine-Tuning Parameters

You can customize the fine-tuning parameters when creating a job:

```
/finetune create job_name base_model --learning_rate 2e-5 --batch_size 4 --max_steps 200
```

### Using a Specific Dataset

If you have multiple datasets, you can specify which one to use:

```
/finetune create job_name base_model --dataset dataset_name
```

### Listing Jobs and Datasets

List all fine-tuning jobs:

```
/finetune list
```

List all datasets:

```
/finetune datasets
```

## Troubleshooting

### Reset a Failed Job

If a job fails, you can reset it and try again:

```
/finetune reset job_name
```

### Delete a Job

To delete a job:

```
/finetune delete job_name
```

### Common Issues

1. **Out of Memory**: Try reducing the batch size or using a smaller model
2. **Slow Training**: This is normal for larger models, especially on CPU
3. **Installation Failures**: Make sure you have the required system dependencies for your platform

## Example Datasets

Here are some example datasets you can use for fine-tuning:

### Sample Datasets

You can create sample datasets for testing the fine-tuning process:

```
# Create a simple Q&A dataset
/create sample dataset with 10 questions and save as sample_qa.jsonl
```

### Creating Custom Datasets

You can create custom datasets from your own data using the `/create` command:

```
/create dataset from my_documents/ and save as my_custom_dataset.jsonl
```

This will process the documents in the specified directory and create a dataset in the correct format for fine-tuning.

### Recommended Dataset Sources

While Ollama Shell doesn't directly support importing from external repositories, you can download datasets from these popular sources and then use them with the `/finetune dataset` command:

1. **HuggingFace Datasets**: Download datasets from [HuggingFace](https://huggingface.co/datasets) and convert them to JSONL format

2. **Alpaca Dataset**: The Stanford Alpaca dataset is a good starting point for instruction tuning

3. **Open Assistant**: High-quality conversation datasets from [Open Assistant](https://huggingface.co/datasets/OpenAssistant/oasst1)

4. **Dolly**: Databricks' Dolly dataset for instruction tuning

After downloading these datasets, you can use them with:

```
/finetune dataset path/to/downloaded/dataset.jsonl
```

## Best Practices

1. **Start Small**: Begin with a small dataset and a small model to test the process
2. **Quality Over Quantity**: A smaller, high-quality dataset often works better than a large, noisy one
3. **Test Incrementally**: Test your model after each fine-tuning session to see if it's improving
4. **Save Checkpoints**: The system automatically saves checkpoints during training
5. **Use Diverse Data**: Include a variety of examples that cover the range of tasks you want the model to perform

## Data Privacy

All fine-tuning data is stored locally in the "Created Files" directory and is excluded from Git. Your data never leaves your machine unless you explicitly share it.

---

For more information, refer to the documentation for [MLX](https://github.com/ml-explore/mlx) or [Unsloth](https://github.com/unslothai/unsloth) depending on your platform.
