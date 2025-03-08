#!/usr/bin/env python3
"""
Scan the Created Files directory for fine-tuning jobs and datasets and update the configuration file.
This ensures that migrated jobs and datasets are properly recognized by the FineTuningManager.
"""

import os
import json
import datetime
import sys
from pathlib import Path

def get_created_files_dir():
    """Get the path to the Created Files directory."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    created_files_dir = os.path.join(project_root, "Created Files")
    return created_files_dir

def scan_jobs_directory(config):
    """
    Scan the jobs directory for fine-tuning jobs and update the configuration.
    
    Args:
        config: The current configuration dictionary
    
    Returns:
        Updated configuration dictionary
    """
    created_files_dir = get_created_files_dir()
    jobs_dir = os.path.join(created_files_dir, "jobs")
    
    if not os.path.exists(jobs_dir) or not os.path.isdir(jobs_dir):
        print(f"Jobs directory not found: {jobs_dir}")
        return config
    
    # Initialize jobs in config if not present
    if "jobs" not in config:
        config["jobs"] = {}
    
    # Scan for job directories
    job_count = 0
    for job_name in os.listdir(jobs_dir):
        job_dir = os.path.join(jobs_dir, job_name)
        
        # Skip if not a directory or already in config
        if not os.path.isdir(job_dir) or job_name in config["jobs"]:
            continue
        
        # Check if this looks like a fine-tuning job
        model_dir = os.path.join(job_dir, "model")
        model_name_file = os.path.join(model_dir, "model_name.txt")
        
        if os.path.exists(model_dir) and os.path.isdir(model_dir):
            # Determine base model if possible
            base_model = "unknown"
            if os.path.exists(model_name_file):
                try:
                    with open(model_name_file, "r") as f:
                        base_model = f.read().strip()
                except:
                    pass
            
            # Determine job status
            status = "unknown"
            if os.path.exists(os.path.join(job_dir, "completed")):
                status = "completed"
            elif os.path.exists(os.path.join(job_dir, "process.pid")):
                # Check if process is still running
                try:
                    with open(os.path.join(job_dir, "process.pid"), "r") as f:
                        pid = int(f.read().strip())
                    
                    # Try to check if process exists
                    try:
                        os.kill(pid, 0)  # Signal 0 doesn't kill the process, just checks if it exists
                        status = "running"
                    except ProcessLookupError:
                        status = "failed"
                except:
                    status = "failed"
            
            # Add job to config
            config["jobs"][job_name] = {
                "name": job_name,
                "base_model": base_model,
                "directory": job_dir,
                "job_dir": job_dir,
                "status": status,
                "created_at": datetime.datetime.now().isoformat()
            }
            
            print(f"Found job: {job_name} (status: {status}, base model: {base_model})")
            job_count += 1
    
    print(f"Found {job_count} new jobs")
    return config

def scan_datasets_directory(config):
    """
    Scan the datasets directory for datasets and update the configuration.
    
    Args:
        config: The current configuration dictionary
    
    Returns:
        Updated configuration dictionary
    """
    created_files_dir = get_created_files_dir()
    datasets_dir = os.path.join(created_files_dir, "datasets")
    
    if not os.path.exists(datasets_dir) or not os.path.isdir(datasets_dir):
        print(f"Datasets directory not found: {datasets_dir}")
        return config
    
    # Initialize datasets in config if not present
    if "datasets" not in config:
        config["datasets"] = {}
    
    # Scan for dataset directories
    dataset_count = 0
    for dataset_name in os.listdir(datasets_dir):
        dataset_dir = os.path.join(datasets_dir, dataset_name)
        
        # Skip if already in config
        if dataset_name in config["datasets"]:
            continue
        
        # Check if this is a directory or a file
        if os.path.isdir(dataset_dir):
            # Look for jsonl files in the directory
            jsonl_files = [f for f in os.listdir(dataset_dir) if f.endswith('.jsonl')]
            
            if jsonl_files:
                # Add dataset to config
                config["datasets"][dataset_name] = {
                    "name": dataset_name,
                    "directory": dataset_dir,
                    "path": os.path.join(dataset_dir, jsonl_files[0]),
                    "created_at": datetime.datetime.now().isoformat()
                }
                
                print(f"Found dataset directory: {dataset_name} (files: {', '.join(jsonl_files)})")
                dataset_count += 1
        elif dataset_name.endswith('.jsonl') or dataset_name.endswith('.json'):
            # This is a dataset file
            dataset_id = os.path.splitext(dataset_name)[0]
            
            # Add dataset to config
            config["datasets"][dataset_id] = {
                "name": dataset_id,
                "path": dataset_dir,
                "created_at": datetime.datetime.now().isoformat()
            }
            
            print(f"Found dataset file: {dataset_name}")
            dataset_count += 1
    
    print(f"Found {dataset_count} new datasets")
    return config

def main():
    """Main function to scan the Created Files directory and update the configuration."""
    created_files_dir = get_created_files_dir()
    config_path = os.path.join(created_files_dir, "finetune_config.json")
    
    print(f"Scanning Created Files directory: {created_files_dir}")
    
    # Load existing config if it exists
    config = {"jobs": {}, "datasets": {}}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except json.JSONDecodeError:
            print(f"Error parsing config file {config_path}, starting with empty config")
    
    # Scan for jobs and datasets
    config = scan_jobs_directory(config)
    config = scan_datasets_directory(config)
    
    # Save the updated config
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"Updated configuration saved to {config_path}")
    print(f"Total jobs: {len(config.get('jobs', {}))}")
    print(f"Total datasets: {len(config.get('datasets', {}))}")

if __name__ == "__main__":
    main()
