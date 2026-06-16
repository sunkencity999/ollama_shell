#!/usr/bin/env python3
"""
Script to reset, fix status, or restart a fine-tuning job.
"""

import os
import sys
import json
import signal
import argparse
from finetune_modules.manager import FineTuningManager

def fix_job_status(job_name):
    """Fix the status of a job that completed successfully but is marked as error."""
    ft_manager = FineTuningManager()
    
    # Get the job details
    job = ft_manager.get_job(job_name)
    if not job:
        print(f"Job {job_name} not found")
        return False
    
    # Check if the job has output files
    job_dir = job.get("job_dir")
    if not job_dir or not os.path.exists(job_dir):
        # Try to find the job directory in the new location
        created_files_dir = ft_manager.get_created_files_dir()
        jobs_dir = os.path.join(created_files_dir, "jobs")
        potential_job_dir = os.path.join(jobs_dir, job_name)
        
        if os.path.exists(potential_job_dir):
            job_dir = potential_job_dir
            print(f"Found job directory at new location: {job_dir}")
        else:
            print(f"Job directory not found for {job_name}")
            return False
        
    output_dir = os.path.join(job_dir, "output")
    log_file = os.path.join(job_dir, "finetune.log")
    
    # Check for successful completion indicators
    success = False
    
    # Check if output directory has files
    if os.path.exists(output_dir) and os.listdir(output_dir):
        success = True
        print(f"Found model files in output directory")
    
    # Check log file for completion message
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            log_content = f.read()
            if "Training complete!" in log_content:
                success = True
                print(f"Found 'Training complete!' in log file")
    
    if success:
        # Update job status in the manager's config
        ft_manager.config["jobs"][job_name]["status"] = "completed"
        ft_manager.config["jobs"][job_name]["progress"] = 100.0
        ft_manager._save_config()
        print(f"Successfully updated job {job_name} status to 'completed'")
        return True
    else:
        print(f"No evidence found that job {job_name} completed successfully")
        return False

def main():
    parser = argparse.ArgumentParser(description="Reset, fix status, or restart a fine-tuning job")
    parser.add_argument("job_name", help="Name of the job to manage")
    parser.add_argument("--fix-status", action="store_true", help="Fix the status of a completed job")
    parser.add_argument("--reset-only", action="store_true", help="Reset the job without starting it")
    args = parser.parse_args()
    
    job_name = args.job_name
    
    # Initialize the fine-tuning manager
    ft_manager = FineTuningManager()
    
    if args.fix_status:
        # Just fix the status
        fix_job_status(job_name)
        return
    
    # Reset the job
    print(f"Resetting job: {job_name}")
    if ft_manager.reset_job(job_name):
        print(f"Successfully reset job {job_name} to 'created' state")
        
        if not args.reset_only:
            # Start the job
            print(f"Starting job: {job_name}")
            if ft_manager.start_job(job_name):
                print(f"Successfully started job {job_name}")
                print(f"You can check the progress with: /finetune progress {job_name}")
            else:
                print(f"Failed to start job {job_name}")
    else:
        print(f"Failed to reset job {job_name}")

if __name__ == "__main__":
    main()
