"""
Patch file for Agentic Mode to bypass API key validation for Ollama models.
"""
import os
import sys
import logging

logger = logging.getLogger(__name__)

def apply_patches():
    """Apply patches to Agentic Mode to make it work with Ollama without API keys."""
    try:
        # Find the config.py file in the Agentic Mode installation
        agentic_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agentic_mode")
        
        # Try different potential locations for the config.py file
        config_paths = [
            os.path.join(agentic_dir, "agentic_mode", "config.py"),
            os.path.join(agentic_dir, "app", "config.py"),
            os.path.join(agentic_dir, "config.py")
        ]
        
        patched = False
        for config_path in config_paths:
            if os.path.exists(config_path):
                logger.info(f"Found config.py at {config_path}, applying patch...")
                
                # Read the current content
                with open(config_path, 'r') as f:
                    content = f.read()
                
                # Check if we need to patch
                if "# OLLAMA_SHELL_PATCHED" not in content:
                    # Add our patch to bypass API key validation for Ollama
                    patched_content = content.replace(
                        "class AppConfig(BaseModel):",
                        """class AppConfig(BaseModel):
    # OLLAMA_SHELL_PATCHED
    
    @model_validator(mode='after')
    def set_default_api_keys(self):
        \"\"\"Set default API keys for Ollama if they are missing.\"\"\"
        # For the default LLM provider
        if hasattr(self, 'llm') and hasattr(self.llm, 'default'):
            if not hasattr(self.llm, self.llm.default + '_api_key') or getattr(self.llm, self.llm.default + '_api_key') is None:
                setattr(self.llm, self.llm.default + '_api_key', "sk-dummy-key-for-validation-purposes-only")
        
        # For vision model
        if hasattr(self, 'llm') and hasattr(self.llm, 'vision') and hasattr(self.llm.vision, 'api_key') and self.llm.vision.api_key is None:
            self.llm.vision.api_key = "sk-dummy-key-for-validation-purposes-only"
        
        return self"""
                    )
                    
                    # Write back the patched content
                    with open(config_path, 'w') as f:
                        f.write(patched_content)
                    
                    logger.info(f"Successfully patched {config_path} to bypass API key validation for Ollama")
                    patched = True
                    break
                else:
                    logger.info(f"Config file {config_path} already patched")
                    patched = True
                    break
        
        if not patched:
            logger.warning("Could not find config.py to patch. API key validation may still fail.")
            
        return patched
    
    except Exception as e:
        logger.error(f"Error applying patches to Agentic Mode: {str(e)}")
        return False

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Apply patches
    apply_patches()
