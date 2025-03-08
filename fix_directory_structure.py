#!/usr/bin/env python3
"""
Fix the directory structure in the "Created Files" directory to remove extra nesting
and update the configuration file to point to the correct locations.
"""

import os
import shutil
import json
import sys

def get_created_files_dir():
    """Get the path to the Created Files directory."""
    project_root = os.path.dirname(os.path.abspath(__file__))
    created_files_dir = os.path.join(project_root, "Created Files")
    return created_files_dir

def fix_directory_structure():
    """Fix the directory structure by removing extra nesting."""
    created_files_dir = get_created_files_dir()
    
    # Fix jobs directory
    jobs_dir = os.path.join(created_files_dir, "jobs")
    nested_jobs_dir = os.path.join(jobs_dir, "jobs")
    
    if os.path.exists(nested_jobs_dir):
        print(f"Fixing jobs directory structure...")
        # Move all job directories from nested_jobs_dir to jobs_dir
        for item in os.listdir(nested_jobs_dir):
            src_path = os.path.join(nested_jobs_dir, item)
            dst_path = os.path.join(jobs_dir, item)
            
            if os.path.isdir(src_path) and not os.path.exists(dst_path):
                shutil.move(src_path, dst_path)
                print(f"  Moved job: {item}")
        
        # Remove the empty nested directory
        if not os.listdir(nested_jobs_dir):
            os.rmdir(nested_jobs_dir)
            print(f"  Removed empty directory: {nested_jobs_dir}")
    
    # Fix datasets directory
    datasets_dir = os.path.join(created_files_dir, "datasets")
    nested_datasets_dir = os.path.join(datasets_dir, "datasets")
    
    if os.path.exists(nested_datasets_dir):
        print(f"Fixing datasets directory structure...")
        # Move all dataset directories from nested_datasets_dir to datasets_dir
        for item in os.listdir(nested_datasets_dir):
            src_path = os.path.join(nested_datasets_dir, item)
            dst_path = os.path.join(datasets_dir, item)
            
            if os.path.exists(src_path) and not os.path.exists(dst_path):
                if os.path.isdir(src_path):
                    shutil.move(src_path, dst_path)
                else:
                    shutil.copy2(src_path, dst_path)
                print(f"  Moved dataset: {item}")
        
        # Remove the empty nested directory
        if not os.listdir(nested_datasets_dir):
            os.rmdir(nested_datasets_dir)
            print(f"  Removed empty directory: {nested_datasets_dir}")
    
    # Fix models directory
    models_dir = os.path.join(created_files_dir, "models")
    nested_models_dir = os.path.join(models_dir, "models")
    
    if os.path.exists(nested_models_dir):
        print(f"Fixing models directory structure...")
        # Move all model directories from nested_models_dir to models_dir
        for item in os.listdir(nested_models_dir):
            src_path = os.path.join(nested_models_dir, item)
            dst_path = os.path.join(models_dir, item)
            
            if os.path.exists(src_path) and not os.path.exists(dst_path):
                if os.path.isdir(src_path):
                    shutil.move(src_path, dst_path)
                else:
                    shutil.copy2(src_path, dst_path)
                print(f"  Moved model: {item}")
        
        # Remove the empty nested directory
        if not os.listdir(nested_models_dir):
            os.rmdir(nested_models_dir)
            print(f"  Removed empty directory: {nested_models_dir}")

def update_config_file():
    """Update the configuration file to point to the correct locations."""
    created_files_dir = get_created_files_dir()
    config_path = os.path.join(created_files_dir, "finetune_config.json")
    
    if not os.path.exists(config_path):
        # If the config file doesn't exist in Created Files, check if it exists in exports
        exports_config_path = os.path.join(created_files_dir, "exports", "finetune_config.json")
        if os.path.exists(exports_config_path):
            # Copy the config file from exports to Created Files
            shutil.copy2(exports_config_path, config_path)
            print(f"Copied config file from exports to Created Files directory")
    
    if os.path.exists(config_path):
        print(f"Updating configuration file: {config_path}")
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
            
            # Update job directories
            if "jobs" in config:
                for job_name, job_data in list(config["jobs"].items()):
                    if "directory" in job_data:
                        old_dir = job_data["directory"]
                        # Replace any path with the correct path in Created Files/jobs
                        new_dir = os.path.join(created_files_dir, "jobs", job_name)
                        job_data["directory"] = new_dir
                        print(f"  Updated job directory for {job_name}: {new_dir}")
            
            # Update dataset directories
            if "datasets" in config:
                for dataset_name, dataset_data in list(config["datasets"].items()):
                    if "directory" in dataset_data:
                        old_dir = dataset_data["directory"]
                        # Replace any path with the correct path in Created Files/datasets
                        new_dir = os.path.join(created_files_dir, "datasets", dataset_name)
                        dataset_data["directory"] = new_dir
                        print(f"  Updated dataset directory for {dataset_name}: {new_dir}")
            
            # Save the updated config
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
            
            print(f"Configuration file updated successfully")
        except Exception as e:
            print(f"Error updating configuration file: {e}")
    else:
        print(f"Configuration file not found: {config_path}")
        # Create a new config file with empty jobs and datasets
        config = {"jobs": {}, "datasets": {}}
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        print(f"Created new configuration file: {config_path}")

def main():
    print("🔧 Fixing directory structure in Created Files directory...")
    
    # Fix directory structure
    fix_directory_structure()
    
    # Update configuration file
    update_config_file()
    
    print("✅ Directory structure fixed and configuration file updated")
    print("You can now use the /finetune commands to manage your fine-tuning jobs and datasets")

if __name__ == "__main__":
    main()
