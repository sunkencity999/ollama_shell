#!/usr/bin/env python
"""
MLX Bridge Script

This script serves as a bridge between the MLX runner and the finetune.py file
in the application's root directory. It ensures that the fine-tuning process
can find and use the finetune.py file correctly.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

def main():
    """
    Main function to bridge MLX runner and finetune.py.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="MLX Bridge Script")
    parser.add_argument("--model", required=True, help="Model name to fine-tune")
    parser.add_argument("--train-file", required=True, help="Path to training data file")
    parser.add_argument("--ollama", action="store_true", help="Use Ollama API to get the model")
    parser.add_argument("--batch-size", type=int, default=1, help="Batch size for training")
    parser.add_argument("--learning-rate", type=float, default=5e-5, help="Learning rate for training")
    parser.add_argument("--max-steps", type=int, default=100, help="Maximum number of training steps")
    parser.add_argument("--save-every", type=int, default=10, help="Save model every N steps")
    parser.add_argument("--output-dir", required=True, help="Output directory for the fine-tuned model")
    
    args = parser.parse_args()
    
    # Find the finetune.py file in the application's root directory
    app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    finetune_script = os.path.join(app_root, "finetune.py")
    
    if not os.path.exists(finetune_script):
        print(f"Error: finetune.py not found at {finetune_script}")
        sys.exit(1)
    
    print(f"Found finetune.py at {finetune_script}")
    
    # Prepare the command to run finetune.py
    cmd = [
        sys.executable,
        finetune_script,
        "--model", args.model,
        "--train-file", args.train_file,
        "--batch-size", str(args.batch_size),
        "--learning-rate", str(args.learning_rate),
        "--max-steps", str(args.max_steps),
        "--save-every", str(args.save_every),
        "--output-dir", args.output_dir
    ]
    
    # Add the --ollama flag if specified
    if args.ollama:
        cmd.append("--ollama")
    
    print(f"Running command: {' '.join(cmd)}")
    
    # Execute the command
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        # Process output in real-time
        for line in process.stdout:
            print(line, end='')
            sys.stdout.flush()
        
        # Wait for process to complete
        return_code = process.wait()
        
        if return_code == 0:
            print("\nFine-tuning completed successfully!")
        else:
            print(f"\nFine-tuning failed with return code {return_code}")
            sys.exit(return_code)
    
    except Exception as e:
        print(f"Error during fine-tuning: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
