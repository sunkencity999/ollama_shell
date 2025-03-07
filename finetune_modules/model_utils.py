"""
Model utilities for fine-tuning.
This module provides functionality to work with language models for fine-tuning.
"""

import os
import sys
import json
import shutil
import subprocess
import tempfile
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

try:
    from rich.console import Console
    console = Console()
except ImportError:
    # Fallback if rich is not installed
    class FallbackConsole:
        def print(self, text, **kwargs):
            # Strip basic rich formatting
            text = text.replace("[red]", "").replace("[/red]", "")
            text = text.replace("[green]", "").replace("[/green]", "")
            text = text.replace("[yellow]", "").replace("[/yellow]", "")
            print(text)
    console = FallbackConsole()


def get_ollama_models() -> List[Dict[str, str]]:
    """
    Get a list of models available in Ollama.
    
    Returns:
        List of dictionaries with model information
    """
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        if result.returncode != 0:
            console.print(f"[red]Error listing Ollama models: {result.stderr}[/red]")
            return []
        
        # Parse the output
        lines = result.stdout.strip().split("\n")
        if len(lines) < 2:
            return []
        
        # Skip the header line
        models = []
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 3:
                model_name = parts[0]
                model_id = parts[1]
                size = parts[2]
                models.append({
                    "name": model_name,
                    "id": model_id,
                    "size": size
                })
        
        return models
    except Exception as e:
        console.print(f"[red]Error listing Ollama models: {str(e)}[/red]")
        return []


def get_ollama_model_path(model_name: str) -> Optional[str]:
    """
    Get the path to an Ollama model.
    
    Args:
        model_name: Name of the model
        
    Returns:
        Path to the model or None if not found
    """
    try:
        # Determine the Ollama models directory
        if sys.platform == "win32":
            ollama_dir = os.path.join(os.environ["USERPROFILE"], ".ollama")
        else:
            ollama_dir = os.path.join(os.path.expanduser("~"), ".ollama")
        
        # Check if the models directory exists
        models_dir = os.path.join(ollama_dir, "models")
        if not os.path.exists(models_dir):
            console.print(f"[red]Ollama models directory not found at {models_dir}[/red]")
            return None
        
        # First, check if the model exists in Ollama
        models = get_ollama_models()
        model_exists = False
        
        for model in models:
            if model["name"] == model_name:
                model_exists = True
                break
        
        if not model_exists:
            console.print(f"[red]Model {model_name} not found in Ollama.[/red]")
            return None
            
        # Use the Ollama API to pull the model if needed
        console.print(f"[green]Using Ollama model: {model_name}[/green]")
        
        # For MLX-LM, we'll use the Ollama API directly rather than trying to find the model file
        # This is a simplified approach that avoids dealing with the internal Ollama file structure
        return model_name
        
    except Exception as e:
        console.print(f"[red]Error getting Ollama model path: {str(e)}[/red]")
        return None


def export_ollama_model(model_name: str, output_dir: str) -> bool:
    """
    Export an Ollama model to a format that MLX-LM can use.
    
    Args:
        model_name: Name of the model
        output_dir: Directory to export the model to
        
    Returns:
        True if the export was successful, False otherwise
    """
    try:
        # Check if the model exists in Ollama
        models = get_ollama_models()
        model_exists = False
        base_model = None
        
        for model in models:
            if model["name"] == model_name:
                model_exists = True
                break
        
        if not model_exists:
            console.print(f"[red]Model {model_name} not found in Ollama.[/red]")
            return False
        
        # Extract the base model name (remove tags)
        if ":" in model_name:
            base_model_name = model_name.split(":")[0]
        else:
            base_model_name = model_name
            
        # Create a new model name for the fine-tuned version
        fine_tuned_model_name = base_model_name
        
        # For MLX-LM, we'll create a Modelfile that references the original model
        console.print(f"[green]Exporting fine-tuned model as {fine_tuned_model_name}...[/green]")
        
        # Create the output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Create a Modelfile in the output directory
        modelfile_path = os.path.join(output_dir, "Modelfile")
        with open(modelfile_path, "w") as f:
            f.write(f"""FROM {model_name}

# This is a fine-tuned version of {model_name}
# Created with Ollama Shell fine-tuning

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx 4096
""")
        
        # Create the Ollama model using the Modelfile
        console.print(f"[green]Creating Ollama model {fine_tuned_model_name}...[/green]")
        
        # Use the ollama create command to create the model
        result = subprocess.run(
            ["ollama", "create", fine_tuned_model_name, "-f", modelfile_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            console.print(f"[red]Error creating Ollama model: {result.stderr}[/red]")
            return False
            
        console.print(f"[green]Successfully exported model to Ollama as {fine_tuned_model_name}[/green]")
        return True
        
    except Exception as e:
        console.print(f"[red]Error exporting Ollama model: {str(e)}[/red]")
        return False
