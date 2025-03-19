#!/usr/bin/env python3
"""
Logger module for the Enhanced Agentic Assistant.
"""

import logging

def setup_logger(name, level=logging.INFO):
    """
    Set up a logger with the specified name and level.
    
    Args:
        name: Name of the logger
        level: Logging level (default: INFO)
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Create console handler
    handler = logging.StreamHandler()
    handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    return logger
