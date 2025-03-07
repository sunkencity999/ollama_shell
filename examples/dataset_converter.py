#!/usr/bin/env python3
"""
Dataset Converter for Ollama Shell Fine-Tuning

This script helps convert various dataset formats to the format expected by Ollama Shell's fine-tuning system.
It supports:
1. Hugging Face datasets
2. Git LFS datasets
3. Compressed archives (tar.gz, zip)

Usage:
    python dataset_converter.py --input /path/to/dataset --output /path/to/output.json --format json
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
import tempfile
import shutil

def check_git_lfs():
    """Check if Git LFS is installed."""
    try:
        subprocess.run(["git", "lfs", "version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def download_git_lfs(input_path):
    """Download Git LFS files in the given directory."""
    if not check_git_lfs():
        print("Git LFS is not installed. Please install it with 'brew install git-lfs' and run 'git lfs install'.")
        return False
    
    try:
        # Change to the input directory
        original_dir = os.getcwd()
        os.chdir(input_path)
        
        # Pull LFS files
        subprocess.run(["git", "lfs", "pull"], check=True)
        
        # Return to original directory
        os.chdir(original_dir)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error downloading Git LFS files: {e}")
        return False

def extract_archive(archive_path, output_dir):
    """Extract a compressed archive."""
    try:
        if archive_path.endswith('.tar.gz') or archive_path.endswith('.tgz'):
            subprocess.run(["tar", "-xzf", archive_path, "-C", output_dir], check=True)
        elif archive_path.endswith('.zip'):
            subprocess.run(["unzip", archive_path, "-d", output_dir], check=True)
        else:
            print(f"Unsupported archive format: {archive_path}")
            return False
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error extracting archive: {e}")
        return False

def convert_huggingface_dataset(input_path, output_path, format='json'):
    """Convert a Hugging Face dataset to the desired format."""
    try:
        import datasets
    except ImportError:
        print("The 'datasets' library is not installed. Please install it with 'pip install datasets'.")
        return False
    
    try:
        # Load the dataset
        dataset = datasets.load_dataset(input_path)
        
        # Convert to the desired format
        if 'train' in dataset:
            data = dataset['train']
        else:
            data = dataset[list(dataset.keys())[0]]
        
        # Map column names if needed
        mapped_data = []
        for item in data:
            mapped_item = {}
            
            # Try to map common column names to our expected format
            if 'instruction' in item:
                mapped_item['instruction'] = item['instruction']
            elif 'input' in item:
                mapped_item['instruction'] = item['input']
            elif 'question' in item:
                mapped_item['instruction'] = item['question']
            elif 'prompt' in item:
                mapped_item['instruction'] = item['prompt']
            else:
                # No suitable column found
                print("Could not find a suitable 'instruction' column in the dataset.")
                return False
            
            if 'response' in item:
                mapped_item['response'] = item['response']
            elif 'output' in item:
                mapped_item['response'] = item['output']
            elif 'answer' in item:
                mapped_item['response'] = item['answer']
            elif 'completion' in item:
                mapped_item['response'] = item['completion']
            else:
                # No suitable column found
                print("Could not find a suitable 'response' column in the dataset.")
                return False
            
            mapped_data.append(mapped_item)
        
        # Write to the output file
        with open(output_path, 'w') as f:
            json.dump(mapped_data, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error converting Hugging Face dataset: {e}")
        return False

def convert_parquet_to_json(input_path, output_path):
    """Convert a Parquet file to JSON."""
    try:
        import pandas as pd
    except ImportError:
        print("pandas is required but not installed.")
        print("To install it, run: pip install pandas pyarrow")
        return False
    
    try:
        # Read the Parquet file
        df = pd.read_parquet(input_path)
        
        # Check if the dataframe has the required columns
        required_columns = ["instruction", "response"]
        if not all(col in df.columns for col in required_columns):
            # Try alternative column names
            alt_columns = {
                "instruction": ["question", "input", "prompt", "query"],
                "response": ["answer", "output", "completion", "result"]
            }
            
            mapped_columns = {}
            for req_col, alt_cols in alt_columns.items():
                if req_col in df.columns:
                    mapped_columns[req_col] = req_col
                else:
                    for alt_col in alt_cols:
                        if alt_col in df.columns:
                            mapped_columns[req_col] = alt_col
                            break
            
            if len(mapped_columns) < len(required_columns):
                missing = [col for col in required_columns if col not in mapped_columns]
                print(f"Parquet file missing required columns: {missing}. "
                      f"Please ensure your file has 'instruction' and 'response' columns or equivalent.")
                return False
            
            # Rename columns to standard format
            df = df.rename(columns={mapped_columns[col]: col for col in required_columns})
        
        # Convert to list of dictionaries
        data = df[required_columns].to_dict(orient='records')
        
        # Write as JSON
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error converting Parquet file: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Convert datasets for Ollama Shell fine-tuning")
    parser.add_argument("--input", required=True, help="Path to the input dataset")
    parser.add_argument("--output", required=True, help="Path to the output file")
    parser.add_argument("--format", choices=["json", "csv", "parquet"], default="json", 
                        help="Output format (default: json)")
    parser.add_argument("--hf", action="store_true", help="Treat input as a Hugging Face dataset")
    parser.add_argument("--git-lfs", action="store_true", help="Download Git LFS files before processing")
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    
    # Check if input is a Git LFS repository
    if args.git_lfs:
        print("Downloading Git LFS files...")
        if not download_git_lfs(args.input):
            return 1
    
    # Process based on input type
    if args.hf:
        print(f"Converting Hugging Face dataset {args.input} to {args.format}...")
        if not convert_huggingface_dataset(args.input, args.output, args.format):
            return 1
    elif os.path.isfile(args.input):
        # Check if it's an archive
        if args.input.endswith(('.tar.gz', '.tgz', '.zip')):
            print(f"Extracting archive {args.input}...")
            temp_dir = tempfile.mkdtemp()
            if not extract_archive(args.input, temp_dir):
                shutil.rmtree(temp_dir)
                return 1
            
            # TODO: Process extracted files
            print(f"Archive extracted to {temp_dir}")
            print("Please manually process the extracted files.")
            return 0
        
        # Check if it's a Parquet file
        elif args.input.endswith('.parquet'):
            print(f"Converting Parquet file {args.input} to JSON...")
            if not convert_parquet_to_json(args.input, args.output):
                return 1
        else:
            print(f"Unsupported file format: {args.input}")
            return 1
    else:
        print(f"Input path {args.input} does not exist or is not a file.")
        return 1
    
    print(f"Conversion complete! Output saved to {args.output}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
