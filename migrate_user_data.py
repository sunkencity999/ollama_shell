#!/usr/bin/env python3
"""
Migration script to copy existing user data to the "Created Files" directory structure.
This script identifies and migrates:
1. Fine-tuning jobs
2. Datasets
3. Models
4. User-created files
"""

import os
import shutil
import glob
from pathlib import Path
import json
import sys

def get_created_files_dir():
    """Get the path to the Created Files directory."""
    project_root = os.path.dirname(os.path.abspath(__file__))
    created_files_dir = os.path.join(project_root, "Created Files")
    os.makedirs(created_files_dir, exist_ok=True)
    return created_files_dir

def ensure_subdirs(created_files_dir):
    """Ensure all subdirectories exist."""
    subdirs = ["jobs", "datasets", "models", "exports"]
    for subdir in subdirs:
        os.makedirs(os.path.join(created_files_dir, subdir), exist_ok=True)
    return {subdir: os.path.join(created_files_dir, subdir) for subdir in subdirs}

def migrate_fine_tuning_jobs(project_root, target_dirs):
    """Migrate existing fine-tuning jobs to the Created Files directory."""
    # Look for job directories in the project root
    job_dirs = []
    
    # Check for job directories in the project root
    for item in os.listdir(project_root):
        item_path = os.path.join(project_root, item)
        if os.path.isdir(item_path) and "job" in item.lower():
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
    
    # Look for job configuration files
    config_file = os.path.join(project_root, "finetune_config.json")
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                if "jobs" in config:
                    for job_name, job_data in config["jobs"].items():
                        if "directory" in job_data:
                            job_dir = job_data["directory"]
                            if os.path.exists(job_dir) and os.path.isdir(job_dir):
                                job_dirs.append(job_dir)
        except Exception as e:
            print(f"Error reading config file: {e}")
    
    # Migrate job directories
    migrated_jobs = 0
    for job_dir in job_dirs:
        job_name = os.path.basename(job_dir)
        target_job_dir = os.path.join(target_dirs["jobs"], job_name)
        
        if os.path.exists(target_job_dir):
            print(f"Job already migrated: {job_name}")
            continue
        
        try:
            shutil.copytree(job_dir, target_job_dir)
            print(f"Migrated job: {job_name}")
            migrated_jobs += 1
        except Exception as e:
            print(f"Error migrating job {job_name}: {e}")
    
    return migrated_jobs

def migrate_datasets(project_root, target_dirs):
    """Migrate existing datasets to the Created Files directory."""
    # Look for dataset directories and files
    dataset_paths = []
    
    # Check for dataset directories in the project root
    for item in os.listdir(project_root):
        item_path = os.path.join(project_root, item)
        if (os.path.isdir(item_path) and "dataset" in item.lower()) or \
           (os.path.isfile(item_path) and item.lower().endswith((".jsonl", ".json")) and "dataset" in item.lower()):
            dataset_paths.append(item_path)
    
    # Check for datasets in the finetune directory if it exists
    finetune_dir = os.path.join(project_root, "finetune")
    if os.path.exists(finetune_dir) and os.path.isdir(finetune_dir):
        for item in os.listdir(finetune_dir):
            item_path = os.path.join(finetune_dir, item)
            if (os.path.isdir(item_path) and "dataset" in item.lower()) or \
               (os.path.isfile(item_path) and item.lower().endswith((".jsonl", ".json")) and "dataset" in item.lower()):
                dataset_paths.append(item_path)
    
    # Migrate datasets
    migrated_datasets = 0
    for dataset_path in dataset_paths:
        dataset_name = os.path.basename(dataset_path)
        target_dataset_path = os.path.join(target_dirs["datasets"], dataset_name)
        
        if os.path.exists(target_dataset_path):
            print(f"Dataset already migrated: {dataset_name}")
            continue
        
        try:
            if os.path.isdir(dataset_path):
                shutil.copytree(dataset_path, target_dataset_path)
            else:
                shutil.copy2(dataset_path, target_dataset_path)
            print(f"Migrated dataset: {dataset_name}")
            migrated_datasets += 1
        except Exception as e:
            print(f"Error migrating dataset {dataset_name}: {e}")
    
    return migrated_datasets

def migrate_models(project_root, target_dirs):
    """Migrate existing models to the Created Files directory."""
    # Look for model directories and files
    model_paths = []
    
    # Check for model directories in the project root
    for item in os.listdir(project_root):
        item_path = os.path.join(project_root, item)
        if (os.path.isdir(item_path) and "model" in item.lower()) or \
           (os.path.isfile(item_path) and item.lower().endswith((".bin", ".pt", ".gguf")) and "model" in item.lower()):
            model_paths.append(item_path)
    
    # Check for models in the finetune directory if it exists
    finetune_dir = os.path.join(project_root, "finetune")
    if os.path.exists(finetune_dir) and os.path.isdir(finetune_dir):
        for item in os.listdir(finetune_dir):
            item_path = os.path.join(finetune_dir, item)
            if (os.path.isdir(item_path) and "model" in item.lower()) or \
               (os.path.isfile(item_path) and item.lower().endswith((".bin", ".pt", ".gguf")) and "model" in item.lower()):
                model_paths.append(item_path)
    
    # Migrate models
    migrated_models = 0
    for model_path in model_paths:
        model_name = os.path.basename(model_path)
        target_model_path = os.path.join(target_dirs["models"], model_name)
        
        if os.path.exists(target_model_path):
            print(f"Model already migrated: {model_name}")
            continue
        
        try:
            if os.path.isdir(model_path):
                shutil.copytree(model_path, target_model_path)
            else:
                shutil.copy2(model_path, target_model_path)
            print(f"Migrated model: {model_name}")
            migrated_models += 1
        except Exception as e:
            print(f"Error migrating model {model_name}: {e}")
    
    return migrated_models

def migrate_created_files(project_root, target_dirs):
    """Migrate user-created files to the Created Files directory."""
    # Extensions that are likely user-created files
    user_extensions = [".txt", ".csv", ".docx", ".xlsx", ".pdf", ".md", ".json", ".jsonl"]
    
    # Files to exclude (common project files)
    exclude_files = ["requirements.txt", "README.md", "LICENSE", "setup.py", "config.json"]
    
    # Look for user-created files in the project root
    user_files = []
    for ext in user_extensions:
        for file_path in glob.glob(os.path.join(project_root, f"*{ext}")):
            file_name = os.path.basename(file_path)
            if file_name not in exclude_files and os.path.isfile(file_path):
                user_files.append(file_path)
    
    # Migrate user-created files
    migrated_files = 0
    for file_path in user_files:
        file_name = os.path.basename(file_path)
        target_file_path = os.path.join(target_dirs["exports"], file_name)
        
        if os.path.exists(target_file_path):
            print(f"File already migrated: {file_name}")
            continue
        
        try:
            shutil.copy2(file_path, target_file_path)
            print(f"Migrated file: {file_name}")
            migrated_files += 1
        except Exception as e:
            print(f"Error migrating file {file_name}: {e}")
    
    return migrated_files

def main():
    print("🚀 Starting migration of user data to Created Files directory...")
    
    # Get project root and Created Files directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    created_files_dir = get_created_files_dir()
    
    # Ensure subdirectories exist
    target_dirs = ensure_subdirs(created_files_dir)
    
    # Migrate fine-tuning jobs
    print("\n📁 Migrating fine-tuning jobs...")
    migrated_jobs = migrate_fine_tuning_jobs(project_root, target_dirs)
    
    # Migrate datasets
    print("\n📁 Migrating datasets...")
    migrated_datasets = migrate_datasets(project_root, target_dirs)
    
    # Migrate models
    print("\n📁 Migrating models...")
    migrated_models = migrate_models(project_root, target_dirs)
    
    # Migrate user-created files
    print("\n📁 Migrating user-created files...")
    migrated_files = migrate_created_files(project_root, target_dirs)
    
    # Print summary
    print("\n✅ Migration complete!")
    print(f"Migrated {migrated_jobs} fine-tuning jobs")
    print(f"Migrated {migrated_datasets} datasets")
    print(f"Migrated {migrated_models} models")
    print(f"Migrated {migrated_files} user-created files")
    print(f"\nAll user data has been copied to: {created_files_dir}")
    print("Original files have not been deleted. You can delete them manually if desired.")

if __name__ == "__main__":
    main()
