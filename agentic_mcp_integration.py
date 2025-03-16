#!/usr/bin/env python3
"""
OpenManus MCP Integration for Ollama Shell

This module integrates the OpenManus agent framework with Ollama Shell,
allowing users to perform complex tasks through natural language commands
using local LLMs via Ollama.
"""

import os
import sys
import json
import logging
import subprocess
import threading
import time
import asyncio
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("openmanus_mcp_integration")

# Import Ollama API client
import requests

class AgenticMCPIntegration:
    """
    Integration between Ollama Shell and the OpenManus agent framework.
    Allows users to perform complex tasks through natural language commands.
    """
    
    def __init__(self, openmanus_path: Optional[str] = None):
        """
        Initialize the OpenManus MCP integration.
        
        Args:
            openmanus_path: Path to the OpenManus installation directory (optional)
        """
        self.openmanus_path = openmanus_path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "openmanus")
        self.config_path = os.path.join(self.agentic_path, "config", "config.toml")
        self.available = False
        
        # Check if Agentic Mode is installed
        self._check_installation()
    
    def _check_installation(self) -> bool:
        """
        Check if OpenManus is installed and properly configured.
        If not, provide guidance on installation.
        
        Returns:
            bool: True if installed and configured, False otherwise
        """
        # Check if OpenManus directory exists
        if not os.path.exists(self.openmanus_path):
            logger.warning(f"OpenManus not found at {self.openmanus_path}")
            self.available = False
            return False
        
        # Check if config file exists
        if not os.path.exists(self.config_path):
            logger.warning(f"OpenManus config not found at {self.config_path}")
            self.available = False
            return False
        
        # Check if main.py exists
        main_py_path = os.path.join(self.openmanus_path, "main.py")
        if not os.path.exists(main_py_path):
            logger.warning(f"OpenManus main.py not found at {main_py_path}")
            self.available = False
            return False
        
        # All checks passed
        self.available = True
        return True
    
    def is_configured(self) -> bool:
        """
        Check if OpenManus is properly configured to use Ollama models.
        
        Returns:
            bool: True if configured, False otherwise
        """
        if not self.available:
            return False
        
        try:
            # Read the config file
            with open(self.config_path, 'r') as f:
                config_content = f.read()
            
            # Check if Ollama is configured
            if "ollama" in config_content.lower():
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking Agentic Mode configuration: {str(e)}")
            return False
    
    def configure_for_ollama(self, model: str = "llama3") -> bool:
        """
        Configure OpenManus to use Ollama models.
        
        Args:
            model: The Ollama model to use
            
        Returns:
            bool: True if configured successfully, False otherwise
        """
        if not self.available:
            logger.error("OpenManus is not available. Please install it first.")
            return False
        
        try:
            # Determine if the model has vision capabilities
            vision_model = model
            if not model.endswith("-vision") and not "vision" in model:
                # Check if a vision variant exists
                vision_candidates = [f"{model}-vision", f"{model}.vision"]
                vision_model = vision_candidates[0]  # Default to first option if can't verify
            
            # Use our custom config file if it exists
            custom_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "openmanus_config.toml")
            
            if os.path.exists(custom_config_path):
                logger.info(f"Using custom config file from {custom_config_path}")
                with open(custom_config_path, 'r') as f:
                    config_content = f.read()
            else:
                # Create a config.toml file for Ollama
                config_content = f"""
# Global LLM configuration for Ollama
[llm]
default = "ollama"
ollama_api_key = "sk-dummy-key-for-validation-purposes-only"
openai_api_key = "sk-dummy-key-for-validation-purposes-only"
anthropic_api_key = "sk-dummy-key-for-validation-purposes-only"
max_tokens = 4096
temperature = 0.0

# Define the Ollama provider
[llm.providers.ollama]
model = "{model}"
base_url = "http://localhost:11434/api"
api_type = "ollama"
api_key = "sk-dummy-key-for-validation-purposes-only"  # Dummy API key that passes validation

# Vision model configuration
[llm.vision]
model = "{vision_model}"
base_url = "http://localhost:11434/api"
api_type = "ollama"
api_key = "sk-dummy-key-for-validation-purposes-only"  # Dummy API key that passes validation

# Agent configuration
[agent]
verbose = true
max_iterations = 15

# Tool configuration
[tools]
allow_code_execution = true
allow_file_operations = true
"""
            
            # Ensure config directory exists
            config_dir = os.path.dirname(self.config_path)
            os.makedirs(config_dir, exist_ok=True)
            
            # Create other necessary directories
            os.makedirs(os.path.join(self.openmanus_path, "logs"), exist_ok=True)
            os.makedirs(os.path.join(self.openmanus_path, "workspace"), exist_ok=True)
            
            # Write the config file to all possible locations
            # 1. Main config path
            with open(self.config_path, 'w') as f:
                f.write(config_content)
            
            # 2. Root directory config
            root_config_path = os.path.join(self.openmanus_path, "config.toml")
            with open(root_config_path, 'w') as f:
                f.write(config_content)
                
            # 3. Home directory config
            home_config_dir = os.path.join(os.path.expanduser("~"), ".openmanus")
            os.makedirs(home_config_dir, exist_ok=True)
            home_config_path = os.path.join(home_config_dir, "config.toml")
            with open(home_config_path, 'w') as f:
                f.write(config_content)
            
            logger.info(f"OpenManus configured to use Ollama model: {model} (vision: {vision_model})")
            return True
        except Exception as e:
            logger.error(f"Error configuring OpenManus for Ollama: {str(e)}")
            return False
    
    async def execute_task(self, task: str, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a task using OpenManus with Ollama models.
        
        Args:
            task: The task description to execute
            model: The Ollama model to use (optional)
            
        Returns:
            Dict containing the execution results
        """
        if not self.available:
            return {
                "success": False,
                "error": "OpenManus is not available. Please install it first.",
                "task": task
            }
        
        # Always check and update configuration to ensure API keys are set
        # This handles both cases: new configuration or updating existing one
        config_file = os.path.join(self.config_path, "config.toml")
        
        if os.path.exists(config_file):
            try:
                # Read existing config and check if it has API keys
                import toml
                with open(config_file, 'r') as f:
                    config = toml.load(f)
                
                needs_update = False
                
                # Check if API keys are missing or empty in the config
                needs_update = False
                
                # Check if we have the providers section with Ollama
                if 'llm' not in config or 'providers' not in config['llm'] or 'ollama' not in config['llm']['providers']:
                    needs_update = True
                elif 'api_key' not in config['llm']['providers']['ollama'] or not config['llm']['providers']['ollama']['api_key'].startswith('sk-'):
                    needs_update = True
                
                # Check vision configuration
                if 'llm' not in config or 'vision' not in config['llm'] or 'api_key' not in config['llm']['vision'] or not config['llm']['vision']['api_key'].startswith('sk-'):
                    needs_update = True
                
                if needs_update:
                    logger.info("Updating existing configuration with API key placeholders for Ollama")
                    self.configure_for_ollama(model=model or "llama3")
            except Exception as e:
                logger.warning(f"Error checking existing configuration: {str(e)}. Reconfiguring...")
                self.configure_for_ollama(model=model or "llama3")
        elif not self.is_configured():
            # No configuration exists, create a new one
            if not self.configure_for_ollama(model=model or "llama3"):
                return {
                    "success": False,
                    "error": "Failed to configure OpenManus for Ollama. Please check the configuration.",
                    "task": task
                }
        
        try:
            # Check for required dependencies and install them if missing
            try:
                # Try to import openai to see if it's installed
                import openai
                logger.info("OpenAI package is already installed")
            except ImportError:
                # Install openai and other required dependencies
                logger.info("Installing missing dependencies (openai, langchain, toml, requests)...")
                try:
                    # Try using uv first (faster)
                    import subprocess
                    subprocess.run("uv pip install openai langchain toml requests", shell=True, check=True)
                except (subprocess.CalledProcessError, ImportError):
                    # Fall back to regular pip
                    subprocess.run("pip install openai langchain toml requests", shell=True, check=True)
                logger.info("Successfully installed missing dependencies")
            
            # Apply patches to Agentic Mode to bypass API key validation
            try:
                # First try the environment variable patch (simplest approach)
                try:
                    import openmanus_env_patch
                    env_patch_result = openmanus_env_patch.apply_patch()
                    logger.info(f"Applied Agentic Mode environment variable patch: {env_patch_result}")
                except ImportError:
                    logger.warning("Agentic Mode environment variable patch module not found")
                
                # Then try the direct patch (most reliable for class modification)
                try:
                    import openmanus_direct_patch
                    patch_result = openmanus_direct_patch.apply_patch()
                    logger.info(f"Applied Agentic Mode direct patch: {patch_result}")
                except ImportError:
                    logger.warning("Agentic Mode direct patch module not found, trying v3")
                    
                    # Try the v3 patch if available
                    try:
                        import openmanus_patch_v3
                        patch_result = openmanus_patch_v3.apply_patch()
                        logger.info(f"Applied Agentic Mode patches v3: {patch_result}")
                    except ImportError:
                        logger.warning("Agentic Mode patch v3 module not found, trying v2")
                        
                        # Try the v2 patch if available
                        try:
                            import openmanus_patch_v2
                            patch_result = openmanus_patch_v2.apply_patch()
                            logger.info(f"Applied Agentic Mode patches v2: {patch_result}")
                        except ImportError:
                            logger.warning("Agentic Mode patch v2 module not found, trying original patch")
                            
                            # Try the original patch as last resort
                            try:
                                import openmanus_patch
                                patch_result = openmanus_patch.apply_patches()
                                logger.info(f"Applied Agentic Mode patches: {patch_result}")
                            except ImportError:
                                logger.warning("No Agentic Mode patch modules found, skipping patches")
            except Exception as e:
                logger.warning(f"Failed to apply Agentic Mode patches: {str(e)}")
            
            # Add all potential module paths to sys.path to ensure imports work
            potential_paths = [
                self.openmanus_path,                                # Root directory
                os.path.dirname(self.openmanus_path),               # Parent directory
                os.path.join(self.openmanus_path, "app"),           # app directory
                os.path.join(self.openmanus_path, "app", "agent"),  # app/agent directory
                os.path.join(self.openmanus_path, "openmanus"),     # openmanus directory (our created structure)
                os.path.join(self.openmanus_path, "openmanus", "agent")  # openmanus/agent directory
            ]
            
            for path in potential_paths:
                if path not in sys.path and os.path.exists(path):
                    sys.path.insert(0, path)
                    logger.info(f"Added {path} to sys.path")
            
            # Try importing the Manus class using multiple strategies
            import_errors = []
            Manus = None  # Will store the Manus class if successfully imported
            
            # First try our mock implementation (most reliable)
            try:
                from openmanus_mock import Manus as MockManus
                Manus = MockManus
                logger.info("Successfully imported mock Manus implementation")
            except ImportError as e_mock:
                import_errors.append(f"Failed to import mock Manus: {str(e_mock)}")
                logger.warning(f"Failed to import mock Manus: {str(e_mock)}")
                
                # Strategy 1: Import from app.agent.manus (original repository structure)
                try:
                    from app.agent.manus import Manus as ManusCls1
                    Manus = ManusCls1
                    logger.info("Successfully imported Manus from app.agent.manus")
                except ImportError as e1:
                    import_errors.append(f"Failed to import from app.agent.manus: {str(e1)}")
                    logger.warning(f"Failed to import from app.agent.manus: {str(e1)}")
                
                # Strategy 2: Import from agent.manus (if app is in sys.path)
                if Manus is None:
                    try:
                        from agent.manus import Manus as ManusCls2
                        Manus = ManusCls2
                        logger.info("Successfully imported Manus from agent.manus")
                    except ImportError as e2:
                        import_errors.append(f"Failed to import from agent.manus: {str(e2)}")
                        logger.warning(f"Failed to import from agent.manus: {str(e2)}")
                
                # Strategy 3: Import from openmanus.agent.manus (our created structure)
                if Manus is None:
                    try:
                        from openmanus.agent.manus import Manus as ManusCls3
                        Manus = ManusCls3
                        logger.info("Successfully imported Manus from openmanus.agent.manus")
                    except ImportError as e3:
                        import_errors.append(f"Failed to import from openmanus.agent.manus: {str(e3)}")
                        logger.warning(f"Failed to import from openmanus.agent.manus: {str(e3)}")
            
            # Strategy 4: Try to find manus.py and create symlinks if needed
            if Manus is None:
                manus_path = os.path.join(self.openmanus_path, "app", "agent", "manus.py")
                if os.path.exists(manus_path):
                    logger.info(f"Found manus.py at {manus_path}, setting up symlinks")
                    try:
                        # Create the openmanus directory structure with proper __init__.py files
                        openmanus_dir = os.path.join(self.openmanus_path, "openmanus")
                        agent_dir = os.path.join(openmanus_dir, "agent")
                        os.makedirs(agent_dir, exist_ok=True)
                        
                        # Create __init__.py at root level
                        root_init = os.path.join(self.openmanus_path, "__init__.py")
                        if not os.path.exists(root_init):
                            with open(root_init, 'w') as f:
                                f.write("# Agentic Mode root package\n")
                        
                        # Create __init__.py files in app directory if it exists
                        app_dir = os.path.join(self.openmanus_path, "app")
                        if os.path.exists(app_dir):
                            app_init = os.path.join(app_dir, "__init__.py")
                            if not os.path.exists(app_init):
                                with open(app_init, 'w') as f:
                                    f.write("# OpenManus app package\n")
                            
                            # Create __init__.py in app/agent if it exists
                            app_agent_dir = os.path.join(app_dir, "agent")
                            if os.path.exists(app_agent_dir):
                                app_agent_init = os.path.join(app_agent_dir, "__init__.py")
                                if not os.path.exists(app_agent_init):
                                    with open(app_agent_init, 'w') as f:
                                        f.write("# OpenManus app.agent package\n\nfrom .manus import Manus\n")
                        
                        # Create __init__.py files in openmanus structure
                        init_files = [
                            (openmanus_dir, "# OpenManus package\n"),
                            (agent_dir, "# OpenManus agent module\n\nfrom .manus import Manus\n")
                        ]
                        
                        for dir_path, content in init_files:
                            init_file = os.path.join(dir_path, "__init__.py")
                            if not os.path.exists(init_file):
                                with open(init_file, 'w') as f:
                                    f.write(content)
                        
                        # Create symlink to manus.py if it doesn't exist
                        manus_symlink = os.path.join(agent_dir, "manus.py")
                        if os.path.exists(manus_symlink):
                            if os.path.islink(manus_symlink):
                                os.unlink(manus_symlink)
                            else:
                                os.remove(manus_symlink)
                        
                        try:
                            os.symlink(manus_path, manus_symlink)
                            logger.info(f"Created symlink from {manus_path} to {manus_symlink}")
                        except Exception as e_sym:
                            # If symlink fails, copy the file instead
                            logger.warning(f"Failed to create symlink, copying file instead: {str(e_sym)}")
                            import shutil
                            shutil.copy2(manus_path, manus_symlink)
                        
                        # Copy any other Python files from app/agent to openmanus/agent
                        app_agent_dir = os.path.join(self.openmanus_path, "app", "agent")
                        if os.path.exists(app_agent_dir):
                            for file in os.listdir(app_agent_dir):
                                if file.endswith(".py") and file != "manus.py" and file != "__init__.py":
                                    source_file = os.path.join(app_agent_dir, file)
                                    target_file = os.path.join(agent_dir, file)
                                    try:
                                        shutil.copy2(source_file, target_file)
                                        logger.info(f"Copied {source_file} to {target_file}")
                                    except Exception as e_copy:
                                        logger.warning(f"Failed to copy {file}: {str(e_copy)}")
                        
                        # Add the new directory to sys.path and try importing again
                        if openmanus_dir not in sys.path:
                            sys.path.insert(0, openmanus_dir)
                        
                        # Clear module cache to ensure fresh import
                        if "openmanus" in sys.modules:
                            del sys.modules["openmanus"]
                        if "openmanus.agent" in sys.modules:
                            del sys.modules["openmanus.agent"]
                        if "openmanus.agent.manus" in sys.modules:
                            del sys.modules["openmanus.agent.manus"]
                        
                        # Try importing again
                        from openmanus.agent.manus import Manus as ManusCls4
                        Manus = ManusCls4
                        logger.info("Successfully imported Manus after creating symlinks")
                    except Exception as e4:
                        import_errors.append(f"Failed to create symlinks and import: {str(e4)}")
                        logger.error(f"Failed to create symlinks and import: {str(e4)}")
            
            # Strategy 5: Dynamic import using importlib as a last resort
            if Manus is None:
                # Try to find manus.py in various locations
                potential_manus_paths = [
                    os.path.join(self.openmanus_path, "app", "agent", "manus.py"),
                    os.path.join(self.openmanus_path, "agent", "manus.py"),
                    os.path.join(self.openmanus_path, "openmanus", "agent", "manus.py"),
                    os.path.join(self.openmanus_path, "manus.py")
                ]
                
                for manus_path in potential_manus_paths:
                    if os.path.exists(manus_path):
                        try:
                            logger.info(f"Attempting dynamic import of {manus_path}")
                            import importlib.util
                            # Generate a unique module name to avoid conflicts
                            module_name = f"manus_module_{hash(manus_path) & 0xFFFFFFFF}"
                            spec = importlib.util.spec_from_file_location(module_name, manus_path)
                            manus_module = importlib.util.module_from_spec(spec)
                            # Add the module to sys.modules to handle potential circular imports
                            sys.modules[module_name] = manus_module
                            spec.loader.exec_module(manus_module)
                            
                            # Check if the module has a Manus class
                            if hasattr(manus_module, "Manus"):
                                Manus = manus_module.Manus
                                logger.info(f"Successfully imported Manus using dynamic import from {manus_path}")
                                break
                            else:
                                logger.warning(f"Module {manus_path} does not contain a Manus class")
                        except Exception as e5:
                            import_errors.append(f"Failed to dynamically import from {manus_path}: {str(e5)}")
                            logger.error(f"Failed to dynamically import from {manus_path}: {str(e5)}")
                
                # If still not found, try to search for manus.py recursively
                if Manus is None:
                    try:
                        logger.info("Searching for manus.py recursively in the OpenManus directory")
                        for root, dirs, files in os.walk(self.openmanus_path):
                            if "manus.py" in files:
                                manus_path = os.path.join(root, "manus.py")
                                logger.info(f"Found manus.py at {manus_path}, attempting dynamic import")
                                
                                try:
                                    import importlib.util
                                    module_name = f"manus_module_found_{hash(manus_path) & 0xFFFFFFFF}"
                                    spec = importlib.util.spec_from_file_location(module_name, manus_path)
                                    manus_module = importlib.util.module_from_spec(spec)
                                    sys.modules[module_name] = manus_module
                                    spec.loader.exec_module(manus_module)
                                    
                                    if hasattr(manus_module, "Manus"):
                                        Manus = manus_module.Manus
                                        logger.info(f"Successfully imported Manus from discovered path: {manus_path}")
                                        break
                                except Exception as e6:
                                    import_errors.append(f"Failed to import from discovered path {manus_path}: {str(e6)}")
                                    logger.error(f"Failed to import from discovered path {manus_path}: {str(e6)}")
                    except Exception as e_search:
                        import_errors.append(f"Error during recursive search: {str(e_search)}")
                        logger.error(f"Error during recursive search: {str(e_search)}")
            
            # If all import strategies failed
            if Manus is None:
                error_msg = "\n".join(import_errors)
                logger.error(f"All import strategies failed:\n{error_msg}")
                
                # Check for specific common issues
                missing_deps = []
                if any("No module named 'openai'" in err for err in import_errors):
                    missing_deps.append("openai")
                if any("No module named 'langchain'" in err for err in import_errors):
                    missing_deps.append("langchain")
                if any("No module named 'toml'" in err for err in import_errors):
                    missing_deps.append("toml")
                if any("No module named 'requests'" in err for err in import_errors):
                    missing_deps.append("requests")
                
                # Provide a more helpful error message based on the diagnosis
                if missing_deps:
                    deps_str = ", ".join(missing_deps)
                    return {
                        "success": False,
                        "error": f"Failed to import OpenManus modules due to missing dependencies: {deps_str}. \n\nPlease run: pip install {' '.join(missing_deps)}\n\nFull error details:\n{error_msg}",
                        "task": task,
                        "missing_dependencies": missing_deps
                    }
                elif any("ModuleNotFoundError" in err for err in import_errors):
                    return {
                        "success": False,
                        "error": f"Failed to import OpenManus modules due to missing Python modules. This may indicate an incomplete installation.\n\nTry reinstalling OpenManus with: python -m pip install -e {self.openmanus_path}\n\nFull error details:\n{error_msg}",
                        "task": task
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to import OpenManus modules after multiple attempts. Please check the installation.\n\nDiagnostic information:\n1. OpenManus path: {self.openmanus_path}\n2. Python path: {sys.path}\n3. Errors encountered:\n{error_msg}",
                        "task": task
                    }
            
            # Create and run the Manus agent
            logger.info(f"Creating Manus agent with config path: {self.config_path}")
            
            # Check if model parameter is required for the Manus constructor
            try:
                import inspect
                sig = inspect.signature(Manus.__init__)
                agent_kwargs = {}
                
                # Add config_path if it's a parameter
                if 'config_path' in sig.parameters:
                    agent_kwargs['config_path'] = self.config_path
                
                # Add model if it's a parameter
                if 'model' in sig.parameters:
                    agent_kwargs['model'] = model or self.get_configured_model()
                
                agent = Manus(**agent_kwargs)
                logger.info(f"Created Manus agent with kwargs: {agent_kwargs}")
            except Exception as e_init:
                logger.warning(f"Error inspecting Manus constructor, falling back to default: {str(e_init)}")
                # Fallback to default initialization
                agent = Manus(config_path=self.config_path)
            
            # Execute the task
            logger.info(f"Executing task: {task}")
            result = await agent.run(task)
            logger.info(f"Task execution completed with result type: {type(result)}")
            
            return {
                "success": True,
                "task": task,
                "result": result,
                "steps": agent.steps if hasattr(agent, "steps") else []
            }
        except Exception as e:
            logger.error(f"Error executing task with OpenManus: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "task": task
            }
    
    def install_openmanus(self, method: str = "uv") -> bool:
        """
        Install OpenManus in the specified directory.
        If OpenManus is already installed, updates it instead.
        
        Args:
            method: Installation method ('conda' or 'uv')
            
        Returns:
            bool: True if installed successfully, False otherwise
        """
        try:
            # Check if OpenManus directory already exists and is a git repository
            is_existing_repo = False
            if os.path.exists(self.openmanus_path):
                try:
                    # Check if it's a git repository
                    git_check_cmd = f"cd {self.openmanus_path} && git rev-parse --is-inside-work-tree"
                    result = subprocess.run(git_check_cmd, shell=True, capture_output=True, text=True, check=False)
                    is_existing_repo = result.stdout.strip() == "true"
                except Exception:
                    is_existing_repo = False
            
            if is_existing_repo:
                # It's an existing repository, update it instead of cloning
                logger.info(f"OpenManus repository already exists at {self.openmanus_path}, updating it...")
                try:
                    update_cmd = f"cd {self.openmanus_path} && git pull"
                    subprocess.run(update_cmd, shell=True, check=True)
                    logger.info("OpenManus repository updated successfully")
                except subprocess.CalledProcessError as e:
                    logger.error(f"Failed to update OpenManus repository: {str(e)}")
                    return False
            else:
                # Directory doesn't exist or isn't a git repo, create it and clone
                if os.path.exists(self.openmanus_path) and os.listdir(self.openmanus_path):
                    logger.error(f"Directory {self.openmanus_path} exists and is not empty. Please remove it first.")
                    return False
                
                # Create directory if it doesn't exist
                os.makedirs(self.openmanus_path, exist_ok=True)
                
                # Clone the repository
                logger.info(f"Cloning OpenManus repository to {self.openmanus_path}...")
                clone_cmd = f"git clone https://github.com/mannaandpoem/OpenManus.git {self.openmanus_path}"
                subprocess.run(clone_cmd, shell=True, check=True)
                logger.info("OpenManus repository cloned successfully")
            
            # Create necessary directories
            os.makedirs(os.path.join(self.openmanus_path, "logs"), exist_ok=True)
            os.makedirs(os.path.join(self.openmanus_path, "workspace"), exist_ok=True)
            os.makedirs(os.path.join(self.openmanus_path, "config"), exist_ok=True)
            
            # Install dependencies based on method
            logger.info(f"Installing dependencies using {method}...")
            if method == "conda":
                # Create conda environment
                conda_cmd = f"conda create -n open_manus python=3.12 -y && conda activate open_manus && pip install -r {os.path.join(self.openmanus_path, 'requirements.txt')}"
                subprocess.run(conda_cmd, shell=True, check=True)
                
                # Install additional required dependencies that might be missing
                extra_deps_cmd = f"conda activate open_manus && pip install openai langchain toml requests"
                subprocess.run(extra_deps_cmd, shell=True, check=True)
                
                # Install OpenManus as a package in development mode
                install_cmd = f"cd {self.openmanus_path} && conda activate open_manus && pip install -e ."
                subprocess.run(install_cmd, shell=True, check=True)
            else:  # uv method
                # Install uv if not already installed
                try:
                    subprocess.run("uv --version", shell=True, check=True)
                except subprocess.CalledProcessError:
                    subprocess.run("curl -LsSf https://astral.sh/uv/install.sh | sh", shell=True, check=True)
                
                # Install dependencies from requirements.txt
                venv_cmd = f"cd {self.openmanus_path} && uv pip install -r requirements.txt"
                try:
                    subprocess.run(venv_cmd, shell=True, check=True)
                except subprocess.CalledProcessError as e:
                    logger.warning(f"Error installing from requirements.txt: {str(e)}. Will install core dependencies directly.")
                
                # Install additional required dependencies that might be missing
                logger.info("Installing core dependencies directly...")
                extra_deps_cmd = f"cd {self.openmanus_path} && uv pip install openai langchain toml requests"
                subprocess.run(extra_deps_cmd, shell=True, check=True)
                
                # Install OpenManus as a package in development mode
                install_cmd = f"cd {self.openmanus_path} && uv pip install -e ."
                subprocess.run(install_cmd, shell=True, check=True)
            
            logger.info("Dependencies installed successfully")
            
            # Create a setup.py file if it doesn't exist (needed for pip install -e .)
            setup_py_path = os.path.join(self.openmanus_path, "setup.py")
            if not os.path.exists(setup_py_path):
                logger.info("Creating setup.py file for development installation...")
                setup_py_content = """
from setuptools import setup, find_packages

setup(
    name="openmanus",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "langchain",
        "openai",
        "toml",
        "requests",
    ],
)
"""
                with open(setup_py_path, 'w') as f:
                    f.write(setup_py_content)
            
            # Create config file if it doesn't exist
            if not os.path.exists(self.config_path):
                config_dir = os.path.dirname(self.config_path)
                example_config = os.path.join(config_dir, "config.example.toml")
                if os.path.exists(example_config):
                    logger.info("Creating config file from example...")
                    copy_cmd = f"cp {example_config} {self.config_path}"
                    subprocess.run(copy_cmd, shell=True, check=True)
                else:
                    # Create a default config file
                    logger.info("Creating default config file...")
                    from ollama_shell import load_config
                    config = load_config()
                    model = config.get("default_model", "llama3.2:latest")
                    self.configure_for_ollama(model)
            else:
                # Configure for Ollama with existing config
                from ollama_shell import load_config
                config = load_config()
                model = config.get("default_model", "llama3.2:latest")
                self.configure_for_ollama(model)
            
            # Set up proper module structure for importing
            # The OpenManus repository has the agent module in app/agent/manus.py
            # We need to create a proper Python package structure for importing
            try:
                # Create the openmanus directory and __init__.py
                openmanus_dir = os.path.join(self.openmanus_path, "openmanus")
                os.makedirs(openmanus_dir, exist_ok=True)
                with open(os.path.join(openmanus_dir, "__init__.py"), 'w') as f:
                    f.write("# OpenManus package\n")
                
                # Create the agent directory and __init__.py
                agent_dir = os.path.join(openmanus_dir, "agent")
                os.makedirs(agent_dir, exist_ok=True)
                
                # Create symlinks to the actual agent files
                source_agent_dir = os.path.join(self.openmanus_path, "app", "agent")
                if os.path.exists(source_agent_dir):
                    # Create __init__.py in agent directory
                    with open(os.path.join(agent_dir, "__init__.py"), 'w') as f:
                        f.write("# OpenManus agent module\n\nfrom .manus import Manus\n")
                    
                    # Create symlinks for all Python files in the agent directory
                    for file in os.listdir(source_agent_dir):
                        if file.endswith(".py"):
                            source_file = os.path.join(source_agent_dir, file)
                            target_file = os.path.join(agent_dir, file)
                            if not os.path.exists(target_file):
                                try:
                                    os.symlink(source_file, target_file)
                                    logger.info(f"Created symlink from {source_file} to {target_file}")
                                except Exception as e:
                                    # If symlink fails, copy the file instead
                                    logger.warning(f"Failed to create symlink, copying file instead: {str(e)}")
                                    import shutil
                                    shutil.copy2(source_file, target_file)
                else:
                    logger.warning(f"Source agent directory {source_agent_dir} not found")
                
                # Create an __init__.py in the app directory to make it a package
                app_dir = os.path.join(self.openmanus_path, "app")
                if os.path.exists(app_dir):
                    app_init_path = os.path.join(app_dir, "__init__.py")
                    if not os.path.exists(app_init_path):
                        with open(app_init_path, 'w') as f:
                            f.write("# OpenManus app package\n")
                    
                    # Create an __init__.py in the app/agent directory if it doesn't exist
                    app_agent_init_path = os.path.join(app_dir, "agent", "__init__.py")
                    if os.path.exists(os.path.dirname(app_agent_init_path)) and not os.path.exists(app_agent_init_path):
                        with open(app_agent_init_path, 'w') as f:
                            f.write("# OpenManus app.agent module\n\nfrom .manus import Manus\n")
                
                logger.info("Set up proper module structure for importing OpenManus modules")
            except Exception as e:
                logger.error(f"Error setting up module structure: {str(e)}")
            
            # Update availability status
            self.available = self._check_installation()
            
            return self.available
        except Exception as e:
            logger.error(f"Error installing OpenManus: {str(e)}")
            return False

# Singleton instance for use throughout the application
_openmanus_integration_instance = None

def get_openmanus_mcp_integration(openmanus_path: Optional[str] = None) -> OpenManusMCPIntegration:
    """
    Get the singleton instance of the OpenManusMCPIntegration.
    
    Args:
        openmanus_path: Path to the OpenManus installation directory (optional)
        
    Returns:
        OpenManusMCPIntegration instance
    """
    global _openmanus_integration_instance
    
    if _openmanus_integration_instance is None:
        _openmanus_integration_instance = OpenManusMCPIntegration(openmanus_path)
    
    return _openmanus_integration_instance

async def handle_openmanus_task(task: str, model: Optional[str] = None) -> Dict[str, Any]:
    """
    Handle a task execution request for OpenManus.
    
    Args:
        task: The task description to execute
        model: The Ollama model to use (optional)
        
    Returns:
        Dict containing the execution results
    """
    openmanus_integration = get_openmanus_mcp_integration()
    
    if not openmanus_integration.available:
        return {
            "success": False,
            "error": "OpenManus is not available. Please install it using the /agentic install command.",
            "task": task
        }
    
    return await openmanus_integration.execute_task(task, model)
