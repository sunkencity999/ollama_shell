"""
Environment variable patch for Agentic Mode to bypass API key validation.
This sets environment variables that Agentic Mode might be checking for API keys.
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_patch() -> bool:
    """
    Apply environment variable patches to bypass API key validation.
    
    Returns:
        bool: True if the patch was applied successfully
    """
    try:
        # Set environment variables for various API keys
        os.environ["OPENAI_API_KEY"] = "sk-dummy-key-for-ollama-integration"
        os.environ["ANTHROPIC_API_KEY"] = "sk-dummy-key-for-ollama-integration"
        os.environ["OLLAMA_API_KEY"] = "sk-dummy-key-for-ollama-integration"
        os.environ["OPENAI_VISION_API_KEY"] = "sk-dummy-key-for-ollama-vision"
        os.environ["LLM_DEFAULT_API_KEY"] = "sk-dummy-key-for-ollama-integration"
        os.environ["LLM_VISION_API_KEY"] = "sk-dummy-key-for-ollama-vision"
        
        # Set environment variables to bypass validation
        os.environ["AGENTIC_BYPASS_API_KEY_VALIDATION"] = "true"
        os.environ["AGENTIC_OFFLINE_MODE"] = "true"
        
        logger.info("Set environment variables for API keys")
        return True
    except Exception as e:
        logger.error(f"Failed to set environment variables: {str(e)}")
        return False

if __name__ == "__main__":
    # Apply the patch when this module is run directly
    apply_patch()
