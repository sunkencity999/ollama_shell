"""
Direct patch for Agentic Mode to bypass API key validation for Ollama models.
This version directly modifies the AppConfig class to accept dummy API keys.
Compatible with both Pydantic v1 and v2 validation formats.
"""
import os
import sys
import logging
import importlib
import inspect
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_patch() -> bool:
    """
    Apply a direct patch to Agentic Mode to bypass API key validation.
    
    Returns:
        bool: True if the patch was applied successfully, False otherwise
    """
    try:
        # Try multiple import paths for AppConfig
        app_config_class = None
        import_paths = [
            'agentic_mode.app.config',
            'app.config',
            'config'
        ]
        
        for path in import_paths:
            try:
                module = importlib.import_module(path)
                if hasattr(module, 'AppConfig'):
                    app_config_class = module.AppConfig
                    logger.info(f"Found AppConfig in {path}")
                    break
            except ImportError:
                continue
        
        if app_config_class is None:
            logger.error("Could not import AppConfig from any known path")
            return False
        
        # Determine if we're using Pydantic v1 or v2
        pydantic_version = 1
        try:
            import pydantic
            if hasattr(pydantic, '__version__'):
                version_str = pydantic.__version__
                major_version = int(version_str.split('.')[0])
                pydantic_version = major_version
                logger.info(f"Detected Pydantic version {major_version}")
        except (ImportError, ValueError, AttributeError):
            logger.warning("Could not determine Pydantic version, assuming v1")
        
        # Create a configuration file with the correct format
        config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agentic_mode", "config")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "config.toml")
        
        # Write a configuration file with all possible API key formats
        with open(config_path, 'w') as f:
            f.write("""# Agentic Mode Configuration for Ollama

[llm]
default = "ollama"
default_api_key = "sk-dummy-key-for-ollama-integration"
vision_api_key = "sk-dummy-key-for-ollama-vision"
api_key = "sk-dummy-key-for-ollama-integration"
openai_api_key = "sk-dummy-key-for-ollama-integration"
anthropic_api_key = "sk-dummy-key-for-ollama-integration"

[llm.default]
api_key = "sk-dummy-key-for-ollama-integration"

[llm.vision]
api_key = "sk-dummy-key-for-ollama-vision"

[llm.ollama]
model = "llama3"
base_url = "http://localhost:11434/v1"
api_key = "sk-dummy-key-for-ollama-integration"
max_tokens = 4096
temperature = 0.7
api_type = "Openai"
api_version = "2023-05-15"

[llm.providers.ollama]
model = "llama3"
base_url = "http://localhost:11434/v1"
api_key = "sk-dummy-key-for-ollama-integration"
max_tokens = 4096
temperature = 0.7
api_type = "Openai"
api_version = "2023-05-15"
""")
        
        logger.info(f"Created comprehensive configuration file at {config_path}")
        
        # Method 1: Monkey patch the __init__ method
        original_init = app_config_class.__init__
        
        def patched_init(self, *args, **kwargs):
            # Call the original __init__
            original_init(self, *args, **kwargs)
            
            # Set API keys directly after initialization using different approaches
            try:
                # Direct attribute setting for nested objects
                if hasattr(self, 'llm'):
                    # For Pydantic v1 style
                    if hasattr(self.llm, 'default'):
                        if hasattr(self.llm.default, 'api_key'):
                            self.llm.default.api_key = "sk-dummy-key-for-ollama-integration"
                    
                    if hasattr(self.llm, 'vision'):
                        if hasattr(self.llm.vision, 'api_key'):
                            self.llm.vision.api_key = "sk-dummy-key-for-ollama-vision"
                    
                    # For top-level keys
                    if hasattr(self.llm, 'default_api_key'):
                        self.llm.default_api_key = "sk-dummy-key-for-ollama-integration"
                    
                    if hasattr(self.llm, 'vision_api_key'):
                        self.llm.vision_api_key = "sk-dummy-key-for-ollama-vision"
                    
                    # For provider-specific keys
                    if hasattr(self.llm, 'providers') and hasattr(self.llm.providers, 'ollama'):
                        if hasattr(self.llm.providers.ollama, 'api_key'):
                            self.llm.providers.ollama.api_key = "sk-dummy-key-for-ollama-integration"
                    
                    if hasattr(self.llm, 'ollama'):
                        if hasattr(self.llm.ollama, 'api_key'):
                            self.llm.ollama.api_key = "sk-dummy-key-for-ollama-integration"
                
                logger.info("Applied API key patch to AppConfig instance")
            except Exception as e:
                logger.error(f"Failed to set API keys via direct attribute access: {str(e)}")
                
            # Method 2: Try using dict-style access for Pydantic v2
            try:
                if pydantic_version >= 2:
                    # Get the model_dump method if available (Pydantic v2)
                    if hasattr(self, 'model_dump'):
                        config_dict = self.model_dump()
                        
                        # Update the dictionary with API keys
                        if 'llm' in config_dict:
                            if 'default' in config_dict['llm'] and isinstance(config_dict['llm']['default'], dict):
                                config_dict['llm']['default']['api_key'] = "sk-dummy-key-for-ollama-integration"
                            
                            if 'vision' in config_dict['llm'] and isinstance(config_dict['llm']['vision'], dict):
                                config_dict['llm']['vision']['api_key'] = "sk-dummy-key-for-ollama-vision"
                            
                            # Try to update the model with the modified dict
                            if hasattr(self, 'model_validate'):
                                updated_config = type(self).model_validate(config_dict)
                                # Copy attributes from updated config to self
                                for attr, value in updated_config.__dict__.items():
                                    setattr(self, attr, value)
                                logger.info("Applied API key patch using Pydantic v2 model_validate")
            except Exception as e:
                logger.error(f"Failed to set API keys via Pydantic v2 methods: {str(e)}")
        
        # Replace the __init__ method
        app_config_class.__init__ = patched_init
        
        # Method 3: Monkey patch the validation method if it exists
        if hasattr(app_config_class, 'validate'):
            original_validate = app_config_class.validate
            
            def patched_validate(cls, *args, **kwargs):
                # Call the original validate method
                result = original_validate(cls, *args, **kwargs)
                
                # Ensure API keys are set
                if hasattr(result, 'llm'):
                    if hasattr(result.llm, 'default'):
                        if hasattr(result.llm.default, 'api_key'):
                            result.llm.default.api_key = "sk-dummy-key-for-ollama-integration"
                    
                    if hasattr(result.llm, 'vision'):
                        if hasattr(result.llm.vision, 'api_key'):
                            result.llm.vision.api_key = "sk-dummy-key-for-ollama-vision"
                
                logger.info("Applied API key patch in validate method")
                return result
            
            app_config_class.validate = classmethod(patched_validate)
        
        logger.info("Successfully applied comprehensive patches to AppConfig")
        return True
    except Exception as e:
        logger.error(f"Failed to apply direct patch: {str(e)}")
        return False

if __name__ == "__main__":
    # Apply the patch when this module is run directly
    apply_patch()
