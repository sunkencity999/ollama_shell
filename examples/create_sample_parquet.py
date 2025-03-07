#!/usr/bin/env python3
"""
This script creates a sample Parquet file for fine-tuning.
It requires pandas and pyarrow to be installed.
"""

import os
import json
import sys

try:
    import pandas as pd
except ImportError:
    print("pandas is required but not installed.")
    print("To install it, run: pip install pandas pyarrow")
    print("If you're using a virtual environment, activate it first.")
    sys.exit(1)

try:
    # This will raise an ImportError if pyarrow is not installed
    pd.DataFrame().to_parquet
except (ImportError, AttributeError):
    print("pyarrow is required but not installed.")
    print("To install it, run: pip install pyarrow")
    print("If you're using a virtual environment, activate it first.")
    sys.exit(1)

# Create examples directory if it doesn't exist
os.makedirs("examples", exist_ok=True)

# Load the sample JSON dataset
with open("examples/sample_dataset.json", "r") as f:
    data = json.load(f)

# Convert to DataFrame
df = pd.DataFrame(data)

# Save as Parquet
df.to_parquet("examples/sample_dataset.parquet", index=False)

print("Created sample Parquet file at examples/sample_dataset.parquet")
print("You can use it with: /finetune dataset ./examples/sample_dataset.parquet")
