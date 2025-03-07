# Fine-Tuning Modules for Ollama Shell

This package provides a modular approach to fine-tuning language models in Ollama Shell. It supports multiple frameworks and platforms, including:

- MLX-LM for Apple Silicon (M1/M2/M3 Macs)
- Unsloth for NVIDIA GPUs (Linux/Windows)

## Architecture

The package is organized into several modules:

- `manager.py`: The main fine-tuning manager that integrates all functionalities
- `hardware_detection.py`: Detects the hardware configuration for fine-tuning
- `venv_utils.py`: Handles virtual environment creation and management
- `dataset_utils.py`: Prepares and processes datasets for fine-tuning
- `model_utils.py`: Provides utilities for working with models, including exporting
- `mlx_runner.py`: Handles fine-tuning jobs using MLX-LM on Apple Silicon
- `unsloth_runner.py`: Manages fine-tuning jobs using Unsloth on NVIDIA GPUs

## Usage

### Basic Usage

```python
from finetune_modules import FineTuningManager

# Create a fine-tuning manager
manager = FineTuningManager()

# Check the status of the fine-tuning system
manager.display_status()

# Install required dependencies
manager.install_dependencies()

# Prepare a dataset
dataset_id = manager.prepare_dataset("path/to/dataset.jsonl")

# Create a fine-tuning job
manager.create_job("my_job", "llama3:8b", dataset_id)

# Start the job
manager.start_job("my_job")

# Check the progress
manager.display_job_progress("my_job")

# Export the fine-tuned model to Ollama
manager.export_job("my_job", "my_fine_tuned_model")
```

### Command-Line Interface

The package includes an example script `finetune_example.py` that demonstrates how to use the fine-tuning modules from the command line:

```bash
# Show fine-tuning status
./finetune_example.py status

# Install required dependencies
./finetune_example.py install

# Prepare a dataset
./finetune_example.py dataset path/to/dataset.jsonl --name my_dataset

# Create a fine-tuning job
./finetune_example.py create my_job llama3:8b --dataset my_dataset

# Start the job
./finetune_example.py start my_job

# Show job progress
./finetune_example.py progress my_job

# Export the fine-tuned model to Ollama
./finetune_example.py export my_job --target my_fine_tuned_model
```

## Integration with Ollama Shell

This package is designed to be integrated with Ollama Shell. The main integration point is the `FineTuningManager` class, which provides a high-level interface for managing fine-tuning jobs.

To integrate with Ollama Shell, import the `FineTuningManager` class and use it to handle fine-tuning commands:

```python
from finetune_modules import FineTuningManager

# Create a fine-tuning manager
manager = FineTuningManager()

# Use the manager to handle fine-tuning commands
if command == "status":
    manager.display_status()
elif command == "install":
    manager.install_dependencies()
# ...and so on
```

## Dependencies

The package uses virtual environments to manage dependencies, ensuring isolation from the system Python installation. The required dependencies are installed on-demand based on the detected hardware configuration.

For MLX-LM (Apple Silicon):
- mlx
- mlx-lm
- transformers
- datasets
- rich

For Unsloth (NVIDIA GPUs):
- torch
- transformers
- datasets
- unsloth
- rich

## License

This package is part of Ollama Shell and is distributed under the same license.
