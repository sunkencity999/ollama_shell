#!/usr/bin/env python3
"""
Example script demonstrating how to use the modular fine-tuning system.
"""

import os
import sys
import argparse
from rich.console import Console

from finetune_modules import FineTuningManager

console = Console()

def main():
    """Main entry point for the example script."""
    parser = argparse.ArgumentParser(description="Fine-tuning example for Ollama models")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Status command
    subparsers.add_parser("status", help="Show fine-tuning status")
    
    # Install command
    subparsers.add_parser("install", help="Install required dependencies")
    
    # Dataset command
    dataset_parser = subparsers.add_parser("dataset", help="Prepare a dataset for fine-tuning")
    dataset_parser.add_argument("path", help="Path to the dataset file or directory")
    dataset_parser.add_argument("--name", help="Name for the dataset")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a fine-tuning job")
    create_parser.add_argument("name", help="Name for the job")
    create_parser.add_argument("base_model", help="Base model to fine-tune")
    create_parser.add_argument("--dataset", help="Dataset ID to use")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start a fine-tuning job")
    start_parser.add_argument("name", help="Name of the job to start")
    
    # List command
    subparsers.add_parser("list", help="List all fine-tuning jobs")
    
    # Models command
    subparsers.add_parser("models", help="List available Ollama models")
    
    # Progress command
    progress_parser = subparsers.add_parser("progress", help="Show progress of a fine-tuning job")
    progress_parser.add_argument("name", help="Name of the job to show progress for")
    
    # Pause command
    pause_parser = subparsers.add_parser("pause", help="Pause a running fine-tuning job")
    pause_parser.add_argument("name", help="Name of the job to pause")
    
    # Resume command
    resume_parser = subparsers.add_parser("resume", help="Resume a paused fine-tuning job")
    resume_parser.add_argument("name", help="Name of the job to resume")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a fine-tuning job")
    delete_parser.add_argument("name", help="Name of the job to delete")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export a fine-tuned model to Ollama")
    export_parser.add_argument("name", help="Name of the job to export")
    export_parser.add_argument("--target", help="Name to use for the exported model")
    
    args = parser.parse_args()
    
    # Create the fine-tuning manager
    manager = FineTuningManager()
    
    if args.command == "status" or args.command is None:
        manager.display_status()
    
    elif args.command == "install":
        if manager.install_dependencies():
            console.print("[green]Successfully installed dependencies.[/green]")
        else:
            console.print("[red]Failed to install dependencies.[/red]")
            return 1
    
    elif args.command == "dataset":
        dataset_id = manager.prepare_dataset(args.path, args.name)
        if not dataset_id:
            return 1
    
    elif args.command == "create":
        if not manager.create_job(args.name, args.base_model, args.dataset):
            return 1
    
    elif args.command == "start":
        if not manager.start_job(args.name):
            return 1
    
    elif args.command == "list":
        jobs = manager.get_jobs()
        if not jobs:
            console.print("[yellow]No jobs available.[/yellow]")
        else:
            console.print(f"[bold blue]Available Jobs ({len(jobs)}):[/bold blue]")
            for job_name, job in jobs.items():
                status = job.get("status", "unknown")
                console.print(f"[bold]{job_name}[/bold] - Status: {status}")
    
    elif args.command == "models":
        models = manager.get_ollama_models()
        if not models:
            console.print("[yellow]No models available in Ollama.[/yellow]")
        else:
            console.print(f"[bold blue]Available Models ({len(models)}):[/bold blue]")
            for model in models:
                console.print(f"[bold]{model.get('name')}[/bold] - Size: {model.get('size')}")
    
    elif args.command == "progress":
        manager.display_job_progress(args.name)
    
    elif args.command == "pause":
        if not manager.pause_job(args.name):
            return 1
    
    elif args.command == "resume":
        if not manager.resume_job(args.name):
            return 1
    
    elif args.command == "delete":
        if not manager.delete_job(args.name):
            return 1
    
    elif args.command == "export":
        if not manager.export_job(args.name, args.target):
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
