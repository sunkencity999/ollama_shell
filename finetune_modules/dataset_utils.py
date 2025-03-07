"""
Dataset utilities for fine-tuning.
This module provides functionality to prepare and process datasets for fine-tuning.
"""

import os
import sys
import json
import shutil
import csv
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

from .venv_utils import get_venv_python_cmd, run_in_venv

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


def prepare_dataset(dataset_path: str, output_dir: str, framework: str) -> Optional[str]:
    """
    Prepare a dataset for fine-tuning.
    
    Args:
        dataset_path: Path to the dataset file or directory
        output_dir: Directory to store the prepared dataset
        framework: Framework to prepare the dataset for ('mlx' or 'unsloth')
        
    Returns:
        Path to the prepared dataset or None if preparation failed
    """
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if the dataset exists
    if not os.path.exists(dataset_path):
        console.print(f"[red]Dataset not found at {dataset_path}[/red]")
        return None
    
    # Determine the dataset format
    if os.path.isdir(dataset_path):
        # Check if this is already a prepared dataset
        if framework == "mlx" and os.path.exists(os.path.join(dataset_path, "train.jsonl")):
            console.print("[green]Using existing MLX-LM formatted dataset.[/green]")
            return dataset_path
        elif framework == "unsloth" and os.path.exists(os.path.join(dataset_path, "train.json")):
            console.print("[green]Using existing Unsloth formatted dataset.[/green]")
            return dataset_path
        else:
            console.print("[red]Directory dataset not in the expected format.[/red]")
            return None
    
    # Process file-based datasets
    if dataset_path.endswith(".jsonl"):
        return _process_jsonl_dataset(dataset_path, output_dir, framework)
    elif dataset_path.endswith(".json"):
        return _process_json_dataset(dataset_path, output_dir, framework)
    elif dataset_path.endswith(".csv") or dataset_path.endswith(".tsv"):
        return _process_csv_dataset(dataset_path, output_dir, framework)
    elif dataset_path.endswith(".txt"):
        return _process_text_dataset(dataset_path, output_dir, framework)
    else:
        console.print(f"[red]Unsupported dataset format: {os.path.splitext(dataset_path)[1]}[/red]")
        console.print("[yellow]Supported formats: .jsonl, .json, .csv, .tsv, .txt[/yellow]")
        return None


def _process_jsonl_dataset(dataset_path: str, output_dir: str, framework: str) -> Optional[str]:
    """Process a JSONL dataset file."""
    try:
        # Read the JSONL file
        with open(dataset_path, "r") as f:
            lines = f.readlines()
        
        if framework == "mlx":
            # For MLX-LM, just copy the file to train.jsonl
            output_path = os.path.join(output_dir, "train.jsonl")
            shutil.copy(dataset_path, output_path)
            console.print(f"[green]Copied dataset to {output_path}[/green]")
            return output_dir
        else:  # Unsloth
            # For Unsloth, convert to the expected format
            output_path = os.path.join(output_dir, "train.json")
            data = []
            
            for line in lines:
                try:
                    item = json.loads(line.strip())
                    if "text" in item:
                        data.append({"text": item["text"]})
                    elif "prompt" in item and "completion" in item:
                        data.append({
                            "text": f"<s>[INST] {item['prompt']} [/INST] {item['completion']}</s>"
                        })
                    elif "messages" in item:
                        # Handle ChatML format
                        conversation = ""
                        for msg in item["messages"]:
                            role = msg.get("role", "")
                            content = msg.get("content", "")
                            if role == "system":
                                conversation += f"<s>[INST] {content} [/INST]"
                            elif role == "user":
                                conversation += f"<s>[INST] {content} [/INST]"
                            elif role == "assistant":
                                conversation += f" {content}</s>"
                        data.append({"text": conversation})
                except json.JSONDecodeError:
                    console.print(f"[yellow]Skipping invalid JSON line: {line.strip()}[/yellow]")
            
            # Write the output file
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2)
            
            console.print(f"[green]Converted dataset to {output_path}[/green]")
            return output_dir
    except Exception as e:
        console.print(f"[red]Error processing JSONL dataset: {str(e)}[/red]")
        return None


def _process_json_dataset(dataset_path: str, output_dir: str, framework: str) -> Optional[str]:
    """Process a JSON dataset file."""
    try:
        # Read the JSON file
        with open(dataset_path, "r") as f:
            data = json.load(f)
        
        if framework == "mlx":
            # For MLX-LM, convert to JSONL format
            output_path = os.path.join(output_dir, "train.jsonl")
            
            with open(output_path, "w") as f:
                if isinstance(data, list):
                    for item in data:
                        f.write(json.dumps(item) + "\n")
                else:
                    # Handle the case where the JSON is a single object
                    f.write(json.dumps(data) + "\n")
            
            console.print(f"[green]Converted JSON dataset to JSONL format at {output_path}[/green]")
            return output_dir
        else:  # Unsloth
            # For Unsloth, convert to the expected format
            output_path = os.path.join(output_dir, "train.json")
            
            if isinstance(data, list):
                # Process list of items
                processed_data = []
                for item in data:
                    if "text" in item:
                        processed_data.append({"text": item["text"]})
                    elif "prompt" in item and "completion" in item:
                        processed_data.append({
                            "text": f"<s>[INST] {item['prompt']} [/INST] {item['completion']}</s>"
                        })
                    elif "messages" in item:
                        # Handle ChatML format
                        conversation = ""
                        for msg in item["messages"]:
                            role = msg.get("role", "")
                            content = msg.get("content", "")
                            if role == "system":
                                conversation += f"<s>[INST] {content} [/INST]"
                            elif role == "user":
                                conversation += f"<s>[INST] {content} [/INST]"
                            elif role == "assistant":
                                conversation += f" {content}</s>"
                        processed_data.append({"text": conversation})
                
                # Write the output file
                with open(output_path, "w") as f:
                    json.dump(processed_data, f, indent=2)
            else:
                # Handle the case where the JSON is a single object
                with open(output_path, "w") as f:
                    if "text" in data:
                        json.dump([{"text": data["text"]}], f, indent=2)
                    elif "prompt" in data and "completion" in data:
                        json.dump([{
                            "text": f"<s>[INST] {data['prompt']} [/INST] {data['completion']}</s>"
                        }], f, indent=2)
                    else:
                        console.print("[red]JSON dataset is not in the expected format.[/red]")
                        return None
            
            console.print(f"[green]Converted dataset to {output_path}[/green]")
            return output_dir
    except Exception as e:
        console.print(f"[red]Error processing JSON dataset: {str(e)}[/red]")
        return None


def _process_csv_dataset(dataset_path: str, output_dir: str, framework: str) -> Optional[str]:
    """Process a CSV/TSV dataset file."""
    try:
        # Determine the delimiter
        delimiter = "," if dataset_path.endswith(".csv") else "\t"
        
        # Read the CSV/TSV file
        with open(dataset_path, "r", newline="") as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            data = list(reader)
        
        if framework == "mlx":
            # For MLX-LM, convert to JSONL format
            output_path = os.path.join(output_dir, "train.jsonl")
            
            with open(output_path, "w") as f:
                for item in data:
                    if "prompt" in item and "completion" in item:
                        f.write(json.dumps({
                            "prompt": item["prompt"],
                            "completion": item["completion"]
                        }) + "\n")
                    elif "text" in item:
                        f.write(json.dumps({"text": item["text"]}) + "\n")
                    else:
                        # Use the first column as text
                        f.write(json.dumps({"text": next(iter(item.values()))}) + "\n")
            
            console.print(f"[green]Converted CSV/TSV dataset to JSONL format at {output_path}[/green]")
            return output_dir
        else:  # Unsloth
            # For Unsloth, convert to the expected format
            output_path = os.path.join(output_dir, "train.json")
            
            processed_data = []
            for item in data:
                if "prompt" in item and "completion" in item:
                    processed_data.append({
                        "text": f"<s>[INST] {item['prompt']} [/INST] {item['completion']}</s>"
                    })
                elif "text" in item:
                    processed_data.append({"text": item["text"]})
                else:
                    # Use the first column as text
                    processed_data.append({"text": next(iter(item.values()))})
            
            # Write the output file
            with open(output_path, "w") as f:
                json.dump(processed_data, f, indent=2)
            
            console.print(f"[green]Converted dataset to {output_path}[/green]")
            return output_dir
    except Exception as e:
        console.print(f"[red]Error processing CSV/TSV dataset: {str(e)}[/red]")
        return None


def _process_text_dataset(dataset_path: str, output_dir: str, framework: str) -> Optional[str]:
    """Process a plain text dataset file."""
    try:
        # Read the text file
        with open(dataset_path, "r") as f:
            text = f.read()
        
        # Split into paragraphs (assuming paragraphs are separated by blank lines)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        
        if framework == "mlx":
            # For MLX-LM, convert to JSONL format
            output_path = os.path.join(output_dir, "train.jsonl")
            
            with open(output_path, "w") as f:
                for paragraph in paragraphs:
                    f.write(json.dumps({"text": paragraph}) + "\n")
            
            console.print(f"[green]Converted text dataset to JSONL format at {output_path}[/green]")
            return output_dir
        else:  # Unsloth
            # For Unsloth, convert to the expected format
            output_path = os.path.join(output_dir, "train.json")
            
            processed_data = [{"text": paragraph} for paragraph in paragraphs]
            
            # Write the output file
            with open(output_path, "w") as f:
                json.dump(processed_data, f, indent=2)
            
            console.print(f"[green]Converted dataset to {output_path}[/green]")
            return output_dir
    except Exception as e:
        console.print(f"[red]Error processing text dataset: {str(e)}[/red]")
        return None
