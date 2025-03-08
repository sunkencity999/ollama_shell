#!/usr/bin/env python3
"""
Cleanup script to remove original user data files that have been migrated to the "Created Files" directory.
This script identifies and removes:
1. Original fine-tuning jobs
2. Original datasets
3. Original models
4. Original user-created files
"""

import os
import shutil
import glob
import json
import sys

def get_created_files_dir():
    """Get the path to the Created Files directory."""
    project_root = os.path.dirname(os.path.abspath(__file__))
    created_files_dir = os.path.join(project_root, "Created Files")
    return created_files_dir

def cleanup_fine_tuning_jobs(project_root):
    """Remove original fine-tuning job directories."""
    # Look for job directories in the project root
    job_dirs = []
    
    # Check for job directories in the project root
    for item in os.listdir(project_root):
        item_path = os.path.join(project_root, item)
        if os.path.isdir(item_path) and "job" in item.lower() and item != "Created Files":
            job_dirs.append(item_path)
    
    # Check for job directories in the finetune directory if it exists
    finetune_dir = os.path.join(project_root, "finetune")
    if os.path.exists(finetune_dir) and os.path.isdir(finetune_dir):
        for item in os.listdir(finetune_dir):
            item_path = os.path.join(finetune_dir, item)
            if os.path.isdir(item_path) and "job" in item.lower():
                job_dirs.append(item_path)
    
    # Check for job directories in the finetune_modules directory if it exists
    finetune_modules_dir = os.path.join(project_root, "finetune_modules")
    if os.path.exists(finetune_modules_dir) and os.path.isdir(finetune_modules_dir):
        for item in os.listdir(finetune_modules_dir):
            item_path = os.path.join(finetune_modules_dir, item)
            if os.path.isdir(item_path) and "job" in item.lower():
                job_dirs.append(item_path)
    
    # Remove job directories
    removed_jobs = 0
    for job_dir in job_dirs:
        job_name = os.path.basename(job_dir)
        try:
            if os.path.exists(job_dir) and os.path.isdir(job_dir):
                shutil.rmtree(job_dir)
                print(f"Removed job directory: {job_dir}")
                removed_jobs += 1
        except Exception as e:
            print(f"Error removing job directory {job_dir}: {e}")
    
    return removed_jobs

def cleanup_datasets(project_root):
    """Remove original dataset directories and files."""
    # Look for dataset directories and files
    dataset_paths = []
    
    # Check for dataset directories in the project root
    for item in os.listdir(project_root):
        item_path = os.path.join(project_root, item)
        if item != "Created Files" and (
            (os.path.isdir(item_path) and "dataset" in item.lower()) or 
            (os.path.isfile(item_path) and item.lower().endswith((".jsonl", ".json")) and "dataset" in item.lower())
        ):
            dataset_paths.append(item_path)
    
    # Check for datasets in the finetune directory if it exists
    finetune_dir = os.path.join(project_root, "finetune")
    if os.path.exists(finetune_dir) and os.path.isdir(finetune_dir):
        for item in os.listdir(finetune_dir):
            item_path = os.path.join(finetune_dir, item)
            if (os.path.isdir(item_path) and "dataset" in item.lower()) or \
               (os.path.isfile(item_path) and item.lower().endswith((".jsonl", ".json")) and "dataset" in item.lower()):
                dataset_paths.append(item_path)
    
    # Remove datasets
    removed_datasets = 0
    for dataset_path in dataset_paths:
        try:
            if os.path.isdir(dataset_path):
                shutil.rmtree(dataset_path)
            else:
                os.remove(dataset_path)
            print(f"Removed dataset: {dataset_path}")
            removed_datasets += 1
        except Exception as e:
            print(f"Error removing dataset {dataset_path}: {e}")
    
    return removed_datasets

def cleanup_models(project_root):
    """Remove original model directories and files."""
    # Look for model directories and files
    model_paths = []
    
    # Check for model directories in the project root
    for item in os.listdir(project_root):
        item_path = os.path.join(project_root, item)
        if item != "Created Files" and (
            (os.path.isdir(item_path) and "model" in item.lower()) or 
            (os.path.isfile(item_path) and item.lower().endswith((".bin", ".pt", ".gguf")) and "model" in item.lower())
        ):
            model_paths.append(item_path)
    
    # Check for models in the finetune directory if it exists
    finetune_dir = os.path.join(project_root, "finetune")
    if os.path.exists(finetune_dir) and os.path.isdir(finetune_dir):
        for item in os.listdir(finetune_dir):
            item_path = os.path.join(finetune_dir, item)
            if (os.path.isdir(item_path) and "model" in item.lower()) or \
               (os.path.isfile(item_path) and item.lower().endswith((".bin", ".pt", ".gguf")) and "model" in item.lower()):
                model_paths.append(item_path)
    
    # Remove models
    removed_models = 0
    for model_path in model_paths:
        try:
            if os.path.isdir(model_path):
                shutil.rmtree(model_path)
            else:
                os.remove(model_path)
            print(f"Removed model: {model_path}")
            removed_models += 1
        except Exception as e:
            print(f"Error removing model {model_path}: {e}")
    
    return removed_models

def cleanup_created_files(project_root):
    """Remove original user-created files."""
    # Extensions that are likely user-created files
    user_extensions = [".txt", ".csv", ".docx", ".xlsx", ".pdf", ".md", ".json", ".jsonl"]
    
    # Files to exclude (common project files)
    exclude_files = ["requirements.txt", "README.md", "LICENSE", "setup.py", "config.json", 
                     "create_directories.py", "migrate_user_data.py", "cleanup_original_data.py"]
    
    # Look for user-created files in the project root
    user_files = []
    for ext in user_extensions:
        for file_path in glob.glob(os.path.join(project_root, f"*{ext}")):
            file_name = os.path.basename(file_path)
            if file_name not in exclude_files and os.path.isfile(file_path):
                # Check if this is a user-created file (not a project file)
                if file_name.lower() in ["finetune_config.json", "fine_tuning_guide.md"] or \
                   (not file_name.startswith(".") and file_name not in exclude_files):
                    user_files.append(file_path)
    
    # Remove user-created files
    removed_files = 0
    for file_path in user_files:
        try:
            os.remove(file_path)
            print(f"Removed file: {file_path}")
            removed_files += 1
        except Exception as e:
            print(f"Error removing file {file_path}: {e}")
    
    return removed_files

def main():
    print("🧹 Starting cleanup of original user data files...")
    
    # Get project root
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Confirm that Created Files directory exists
    created_files_dir = get_created_files_dir()
    if not os.path.exists(created_files_dir):
        print("❌ Error: Created Files directory does not exist. Migration may not have been completed.")
        print("Please run migrate_user_data.py first to migrate your data.")
        sys.exit(1)
    
    # Confirm with user
    print(f"⚠️  WARNING: This will permanently delete original user data files that have been migrated to {created_files_dir}")
    confirm = input("Are you sure you want to continue? (y/n): ")
    if confirm.lower() != 'y':
        print("Cleanup cancelled.")
        sys.exit(0)
    
    # Cleanup fine-tuning jobs
    print("\n🗑️  Removing original fine-tuning jobs...")
    removed_jobs = cleanup_fine_tuning_jobs(project_root)
    
    # Cleanup datasets
    print("\n🗑️  Removing original datasets...")
    removed_datasets = cleanup_datasets(project_root)
    
    # Cleanup models
    print("\n🗑️  Removing original models...")
    removed_models = cleanup_models(project_root)
    
    # Cleanup user-created files
    print("\n🗑️  Removing original user-created files...")
    removed_files = cleanup_created_files(project_root)
    
    # Print summary
    print("\n✅ Cleanup complete!")
    print(f"Removed {removed_jobs} fine-tuning job directories")
    print(f"Removed {removed_datasets} datasets")
    print(f"Removed {removed_models} models")
    print(f"Removed {removed_files} user-created files")
    print(f"\nAll user data is now stored exclusively in: {created_files_dir}")

if __name__ == "__main__":
    main()
