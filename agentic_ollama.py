"""
Agentic Ollama - An integrated agentic implementation for Ollama Shell.
Provides advanced capabilities including image search, file operations, content generation,
image analysis, and document handling directly within Ollama Shell.
"""
import os
import sys
import json
import logging
import requests
import base64
import shutil
import re
import time
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgenticOllama:
    """
    Agentic implementation for Ollama Shell.
    Provides advanced capabilities including image search, file operations,
    content generation, and image analysis directly integrated with Ollama's API.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the Agentic Ollama instance.
        
        Args:
            config_path: Optional path to configuration file
        """
        self.ollama_base_url = "http://localhost:11434/api"
        
        # Check available models and use an appropriate one
        self.model = self._get_available_model()
        self.vision_model = self._get_available_vision_model()
        self.max_tokens = 4096
        self.temperature = 0.7
        
        # Log initialization
        logger.info(f"Initialized Agentic Ollama with model: {self.model}")
    
    def _get_available_model(self) -> str:
        """
        Get an available model from Ollama.
        
        Returns:
            The name of an available model
        """
        try:
            # Try to get the list of models
            response = requests.get(f"{self.ollama_base_url}/tags")
            response.raise_for_status()
            models = response.json().get("models", [])
            
            # Look for preferred models first
            preferred_models = ["llama3", "llama2", "mistral", "gemma", "phi"]
            for preferred in preferred_models:
                for model in models:
                    model_name = model.get("name", "")
                    if preferred in model_name.lower():
                        return model_name
            
            # If no preferred model is found, return the first one
            if models:
                return models[0].get("name", "llama3")
            
            # Default fallback
            return "llama3"
        except Exception as e:
            logger.warning(f"Error getting available models: {str(e)}. Using default.")
            return "llama3"
    
    def _get_available_vision_model(self) -> str:
        """
        Get an available vision model from Ollama.
        
        Returns:
            The name of an available vision model
        """
        try:
            # Try to get the list of models
            response = requests.get(f"{self.ollama_base_url}/tags")
            response.raise_for_status()
            models = response.json().get("models", [])
            
            # Look for vision models
            vision_keywords = ["vision", "vqa", "visual", "multimodal"]
            for model in models:
                model_name = model.get("name", "")
                if any(keyword in model_name.lower() for keyword in vision_keywords):
                    return model_name
            
            # If no vision model is found, return a regular model
            return self._get_available_model()
        except Exception as e:
            logger.warning(f"Error getting available vision models: {str(e)}. Using default.")
            return self._get_available_model()
    
    async def run(self, task: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a task using Agentic Ollama capabilities.
        
        Args:
            task: The task description containing the user's request
            image_path: Optional path to an image file for image analysis tasks
            
        Returns:
            Dict containing the execution results and any relevant data
        """
        logger.info(f"Executing task with Agentic Ollama: {task}")
        
        try:
            # Check for specific task types
            task_lower = task.lower()
            
            # Check if an image path was provided for analysis
            if image_path:
                logger.info(f"Image path provided: {image_path}")
                # Extract custom prompt from task if present
                custom_prompt = None
                if task and len(task.strip()) > 0:
                    custom_prompt = task
                # Analyze the image using vision capabilities
                return await self.analyze_image(image_path, custom_prompt)
            
            # Check if the task involves analyzing a URL or article
            if "analyze" in task_lower and "article" in task_lower and "http" in task:
                # Article analysis capability
                return await self._analyze_article(task)
            
            # Check if the task involves analyzing images
            elif "analyze" in task_lower and ("image" in task_lower or "picture" in task_lower or "photo" in task_lower):
                # Check if we have a path to an image in the task
                image_path = self._extract_path(task)
                if image_path and os.path.exists(image_path):
                    # Extract custom prompt if any
                    custom_prompt = re.sub(r'analyze\s+(?:this\s+)?(?:image|picture|photo)\s+(?:at|in|from)\s+[^\s]+\s+(.+)', r'\1', task, flags=re.IGNORECASE)
                    if custom_prompt == task:  # No match, use default prompt
                        custom_prompt = None
                    return await self.analyze_image(image_path, custom_prompt)
                else:
                    return {
                        "success": False,
                        "message": "To analyze an image, please drag and drop it into the chat or provide a valid path to the image.",
                        "error": "No image provided"
                    }
            
            # Check if the task involves finding or searching for images
            elif ("find" in task_lower or "search" in task_lower) and "image" in task_lower:
                # Image search capability
                return await self._handle_image_search_task(task)
            
            # Check if it's a /create command for file creation
            elif task_lower.startswith("/create"):
                # Extract the arguments (everything after /create)
                create_args = task[7:].strip()
                return await self._handle_create_command(create_args)
            
            # Check if the task involves file operations
            elif any(keyword in task_lower for keyword in ["save", "create folder", "make directory", "download", "file"]):
                # File operation capability
                return await self._handle_file_operation_task(task)
            
            # Default to a simple completion using the Ollama model
            return await self._generate_completion(task)
        except Exception as e:
            logger.error(f"Error in Agentic Ollama: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "task": task
            }
    
    async def _generate_completion(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a completion using Ollama API.
        
        Args:
            prompt: The prompt to complete
            
        Returns:
            Dict containing the completion results
        """
        try:
            # First check if the model exists
            try:
                model_check_url = f"{self.ollama_base_url}/tags"
                model_response = requests.get(model_check_url)
                model_response.raise_for_status()
                models_data = model_response.json()
                
                # Get list of available models
                available_models = [model.get("name", "") for model in models_data.get("models", [])]
                logger.info(f"Available models: {available_models}")
                
                # If our model isn't available, use the first available one
                if self.model not in available_models and available_models:
                    self.model = available_models[0]
                    logger.info(f"Using alternative model: {self.model}")
            except Exception as model_error:
                logger.warning(f"Error checking available models: {str(model_error)}")
            
            # Prepare the request to Ollama
            # Use the Ollama endpoint directly
            url = f"{self.ollama_base_url}/generate"
            
            # Create a full prompt with system prompt if provided
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            payload = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens
                }
            }
            
            # Make the API request
            response = requests.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            
            # Extract the completion
            completion = result.get("response", "")
            
            logger.info("Successfully generated completion from Ollama")
            
            return {
                "success": True,
                "result": completion,
                "task": prompt
            }
        except Exception as e:
            logger.error(f"Error generating completion: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "task": prompt
            }
    
    async def _analyze_article(self, task: str) -> Dict[str, Any]:
        """
        Analyze an article for bias using Ollama.
        
        Args:
            task: The task description containing the URL
            
        Returns:
            Dict containing the analysis results
        """
        try:
            # Extract the URL from the task
            import re
            url_match = re.search(r'https?://[^\s]+', task)
            if not url_match:
                return {
                    "success": False,
                    "error": "No URL found in task",
                    "task": task
                }
            
            url = url_match.group(0)
            
            # Fetch the article content
            try:
                article_response = requests.get(url, timeout=10)
                article_response.raise_for_status()
                article_content = article_response.text
                
                # Truncate the article if it's too long
                if len(article_content) > 10000:
                    article_content = article_content[:10000] + "... [truncated]"
            except Exception as e:
                logger.warning(f"Error fetching article: {str(e)}. Using URL only.")
                article_content = f"[Could not fetch content from {url}]"
            
            # Create a prompt for bias analysis
            analysis_prompt = f"""
            Analyze the following article for political bias:
            
            URL: {url}
            
            Content: {article_content}
            
            Please provide:
            1. A summary of the article
            2. An assessment of any political bias (left, right, or neutral)
            3. Specific examples of biased language or framing, if any
            4. An overall bias rating on a scale from -5 (far left) to +5 (far right)
            """
            
            # Generate the analysis with a bias analysis system prompt
            system_prompt = "You are a helpful assistant that analyzes articles for political bias."
            analysis_result = await self._generate_completion(analysis_prompt, system_prompt)
            
            if analysis_result["success"]:
                return {
                    "success": True,
                    "result": analysis_result["result"],
                    "task": task,
                    "url": url
                }
            else:
                return analysis_result
        except Exception as e:
            logger.error(f"Error analyzing article: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "task": task
            }
    
    async def _handle_image_search_task(self, task: str) -> Dict[str, Any]:
        """
        Handle tasks related to searching for images with advanced capabilities.
        Provides intelligent image search with customizable parameters and folder organization.
        
        Args:
            task: The task description containing the image search request
            
        Returns:
            Dict containing the search results, actions taken, and any downloaded images
        """
        try:
            # Extract the search query and parameters from the task
            search_terms, search_params = self._extract_search_terms(task)
            logger.info(f"Searching for images with terms: {search_terms}")
            logger.info(f"Search parameters: {search_params}")
            
            # Check if the task involves saving results to a file
            save_to_file = False
            file_path = None
            if "save" in task.lower() and ("file" in task.lower() or ".txt" in task.lower()):
                save_to_file = True
                # Try to extract the filename from the task
                file_match = re.search(r'(?:to|into|in)\s+(?:a\s+)?(?:file\s+)?(?:named\s+)?["\'](.+?\.txt)["\']', task, re.IGNORECASE)
                if not file_match:
                    file_match = re.search(r'(?:to|into|in)\s+(?:a\s+)?(?:file\s+)?(?:named\s+)?(\w+\.txt)', task, re.IGNORECASE)
                
                if file_match:
                    file_path = file_match.group(1)
                    # If it's just a filename without a path, add a default path
                    if os.path.sep not in file_path:
                        file_path = os.path.expanduser(f"~/Documents/{file_path}")
            
            # Check if the task involves saving images to a folder
            save_to_folder = False
            folder_path = None
            if "save" in task.lower() and ("folder" in task.lower() or "directory" in task.lower()):
                save_to_folder = True
                # Try to extract the folder name from the task
                folder_match = re.search(r'(?:to|into|in)\s+(?:a\s+)?(?:folder|directory)\s+(?:named|called)\s+["\'](.*?)["\'](\s|$)', task, re.IGNORECASE)
                if not folder_match:
                    folder_match = re.search(r'(?:to|into|in)\s+(?:a\s+)?(?:folder|directory)\s+(?:named|called)\s+([\w-]+)(\s|$)', task, re.IGNORECASE)
                
                if folder_match:
                    folder_name = folder_match.group(1)
                    # Create the folder path
                    folder_path = os.path.expanduser(f"~/Documents/{folder_name}")
                    
                    # Create the folder if it doesn't exist
                    try:
                        if not os.path.exists(folder_path):
                            os.makedirs(folder_path)
                            logger.info(f"Created folder: {folder_path}")
                    except Exception as folder_error:
                        logger.error(f"Error creating folder: {str(folder_error)}")
            
            # Use Ollama to generate a search strategy
            search_strategy_prompt = f"I need to find images of {search_terms}. What would be the best search terms to use, and what websites should I check? Format your response as JSON with 'search_terms' and 'websites' keys."
            system_prompt = "You are a helpful assistant that specializes in image search strategies. Provide concise, relevant search terms and website suggestions in JSON format."
            strategy_response = await self._generate_completion(search_strategy_prompt, system_prompt)
            
            # Extract search strategy if possible
            try:
                import json
                strategy_text = strategy_response.get("result", "")
                # Try to extract JSON from the text
                json_match = re.search(r'\{[^\}]+\}', strategy_text)
                if json_match:
                    strategy_json = json.loads(json_match.group(0))
                    refined_terms = strategy_json.get("search_terms", search_terms)
                    if refined_terms and isinstance(refined_terms, str):
                        search_terms = refined_terms
                        logger.info(f"Refined search terms to: {search_terms}")
            except Exception as json_error:
                logger.warning(f"Could not parse search strategy: {str(json_error)}")
            
            # Perform the actual image search with parameters
            search_results = self._perform_image_search(search_terms, search_params=search_params)
            
            # Generate a response about the search results
            response = f"I've searched for images of '{search_terms}' using Agentic Ollama and found {len(search_results)} results.\n"
            
            # Add information about search parameters if any were specified
            param_info = []
            if search_params['format']:
                param_info.append(f"format: {search_params['format']}")
            if search_params['size']:
                param_info.append(f"size: {search_params['size']}")
            if search_params['color']:
                param_info.append(f"color: {search_params['color']}")
            if search_params['type']:
                param_info.append(f"type: {search_params['type']}")
            if search_params['count'] is not None:
                param_info.append(f"count: {search_params['count']}")
                
            if param_info:
                response += f"Search parameters used: {', '.join(param_info)}\n"
                
            response += "\n"
            
            if search_results:
                response += "Here are the top results:\n"
                for i, result in enumerate(search_results[:5], 1):
                    response += f"{i}. {result['title']} - {result['url']}\n"
                
                # Download images
                if len(search_results) > 0:
                    try:
                        # Determine how many images to download
                        num_images_to_download = 1  # Default to just the first image
                        
                        # Use count from search parameters if specified
                        if search_params['count'] is not None:
                            num_images_to_download = min(search_params['count'], len(search_results))
                        # If saving to a folder and no count specified, download multiple images
                        elif save_to_folder and folder_path:
                            num_images_to_download = min(10, len(search_results))  # Download up to 10 images by default
                            
                            # Download multiple images to the folder
                            downloaded_images = []
                            for i, image_result in enumerate(search_results[:num_images_to_download]):
                                try:
                                    image_url = image_result['url']
                                    image_path = self._download_image(image_url, f"{search_terms}_{i+1}", folder_path, search_params)
                                    if image_path:
                                        downloaded_images.append(image_path)
                                except Exception as img_error:
                                    logger.warning(f"Error downloading image {i+1}: {str(img_error)}")
                            
                            if downloaded_images:
                                # Create a summary file with information about the downloaded images
                                try:
                                    summary_content = f"Agentic Ollama - Image Search Results for '{search_terms}'\n\n"
                                    summary_content += f"Search performed on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                                    summary_content += f"Downloaded {len(downloaded_images)} images to folder: {folder_path}\n\n"
                                    summary_content += f"Search parameters: {', '.join(param_info) if param_info else 'None'}\n\n"
                                    summary_content += "Image Details:\n"
                                    
                                    for i, (image_path, image_result) in enumerate(zip(downloaded_images, search_results[:len(downloaded_images)])):
                                        filename = os.path.basename(image_path)
                                        summary_content += f"{i+1}. {filename}\n"
                                        summary_content += f"   Title: {image_result.get('title', 'Unknown')}\n"
                                        summary_content += f"   Source URL: {image_result.get('url', 'Unknown')}\n"
                                        summary_content += f"   Source: {image_result.get('source', 'Unknown')}\n\n"
                                    
                                    # Save the summary file
                                    summary_path = os.path.join(folder_path, f"{search_terms}_summary.txt")
                                    with open(summary_path, 'w', encoding='utf-8') as f:
                                        f.write(summary_content)
                                    
                                    response += f"\nI've downloaded {len(downloaded_images)} images to folder: {folder_path}\n"
                                    response += f"A summary file with details about the images has also been saved to {summary_path}\n"
                                    response += f"You can analyze these images by dragging and dropping them into the chat.\n"
                                except Exception as summary_error:
                                    logger.error(f"Error creating summary file: {str(summary_error)}")
                                    response += f"\nI've downloaded {len(downloaded_images)} images to folder: {folder_path}\n"
                                    response += f"You can view these images in the folder or drag and drop them into the chat for analysis.\n"
                        else:
                            # Just download the first image to the default location
                            first_image = search_results[0]
                            image_url = first_image['url']
                            image_path = self._download_image(image_url, search_terms, None, search_params)
                            
                            if image_path:
                                response += f"\nI've downloaded the top image to: {image_path}\n"
                                response += f"You can view this image, save it to a different location, or drag and drop it into the chat for detailed analysis using vision models."
                    except Exception as download_error:
                        logger.error(f"Error downloading image: {str(download_error)}")
                        response += f"\nI found images but couldn't download them due to: {str(download_error)}"
                
                # Save search results to a text file if requested
                if save_to_file and file_path:
                    try:
                        # Create content for the file
                        file_content = f"Agentic Ollama - Image Search Results for '{search_terms}'\n\n"
                        file_content += f"Search performed on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        file_content += f"Search parameters: {', '.join(param_info) if param_info else 'None'}\n\n"
                        file_content += "Results:\n"
                        
                        for i, result in enumerate(search_results, 1):
                            file_content += f"{i}. {result['title']}\n   URL: {result['url']}\n   Source: {result.get('source', 'Unknown')}\n\n"
                        
                        # Save the content to the file
                        save_result = self._save_text_file(file_path, file_content)
                        response += f"\n\n{save_result}"
                    except Exception as save_error:
                        logger.error(f"Error saving search results to file: {str(save_error)}")
                        response += f"\n\nI tried to save the search results to {file_path}, but encountered an error: {str(save_error)}"
            else:
                response += "I couldn't find any images matching your search terms. Please try a different query or adjust the search parameters (format, size, color, type)."
            
            result_dict = {
                "success": True,
                "result": response,
                "task": task,
                "search_terms": search_terms,
                "search_params": search_params,
                "search_results": search_results
            }
            
            # Add file information if applicable
            if save_to_file and file_path:
                result_dict["file_path"] = file_path
                result_dict["saved_to_file"] = True
                
            # Add folder information if applicable
            if save_to_folder and folder_path:
                result_dict["folder_path"] = folder_path
                result_dict["saved_to_folder"] = True
            
            return result_dict
        except Exception as e:
            logger.error(f"Error handling image search task: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "task": task
            }
    
    async def delete_files(self, task: str) -> Dict[str, Any]:
        """
        Delete files based on natural language request.
        
        Args:
            task: Natural language description of files to delete
            
        Returns:
            Dict containing the deletion results
        """
        try:
            # Extract file types and directories from the task description
            file_types = []
            directory = None
            
            # Look for common file extensions
            for ext in ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.txt', '.doc', '.docx', '.xls', '.xlsx', '.csv']:
                if ext in task.lower():
                    file_types.append(ext)
            
            # Look for directory names
            dir_match = re.search(r'(?:in|from|within)\s+(?:the\s+)?["\']?([\w\s\-\/]+)["\']?\s+(?:folder|directory)', task, re.IGNORECASE)
            if dir_match:
                directory = dir_match.group(1).strip()
            
            # If no directory found, try other patterns
            if not directory:
                dir_match = re.search(r'(?:delete|remove)\s+(?:all\s+)?(?:files|images|documents)\s+(?:in|from|within)\s+(?:the\s+)?["\']?([\w\s\-\/]+)["\']?', task, re.IGNORECASE)
                if dir_match:
                    directory = dir_match.group(1).strip()
            
            # If still no directory, look for folder name at the end
            if not directory:
                dir_match = re.search(r'["\']?([\w\s\-\/]+)["\']?\s+(?:folder|directory)', task, re.IGNORECASE)
                if dir_match:
                    directory = dir_match.group(1).strip()
            
            # Determine the full directory path
            if directory:
                # Check if it's a relative or absolute path
                if directory.startswith('/'):
                    full_directory = directory
                else:
                    # Try to find the directory in common locations
                    possible_locations = [
                        os.path.expanduser(f'~/{directory}'),
                        os.path.expanduser(f'~/Documents/{directory}'),
                        os.path.expanduser(f'~/Downloads/{directory}')
                    ]
                    
                    for location in possible_locations:
                        if os.path.exists(location) and os.path.isdir(location):
                            full_directory = location
                            break
                    else:
                        # If not found, default to the first option
                        full_directory = possible_locations[0]
            else:
                # Default to Downloads folder if no directory specified
                full_directory = os.path.expanduser('~/Downloads')
            
            # Ensure the directory exists
            if not os.path.exists(full_directory):
                return {
                    "success": False,
                    "error": f"Directory not found: {full_directory}",
                    "task": task
                }
            
            # Find files to delete
            files_to_delete = []
            
            # If specific file types were mentioned, only delete those types
            if file_types:
                for file_type in file_types:
                    for file in os.listdir(full_directory):
                        if file.lower().endswith(file_type):
                            files_to_delete.append(os.path.join(full_directory, file))
            else:
                # If no specific types mentioned, look for all common image formats
                # This is a safety measure to avoid deleting all files unintentionally
                if 'image' in task.lower() or 'picture' in task.lower() or 'photo' in task.lower():
                    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
                    for file in os.listdir(full_directory):
                        if any(file.lower().endswith(ext) for ext in image_extensions):
                            files_to_delete.append(os.path.join(full_directory, file))
                # If specifically mentioned 'all files', delete everything in the directory
                elif 'all files' in task.lower() or 'everything' in task.lower():
                    for file in os.listdir(full_directory):
                        file_path = os.path.join(full_directory, file)
                        if os.path.isfile(file_path):
                            files_to_delete.append(file_path)
            
            # Delete the files
            deleted_files = []
            for file_path in files_to_delete:
                try:
                    os.remove(file_path)
                    deleted_files.append(os.path.basename(file_path))
                except Exception as e:
                    logger.warning(f"Error deleting file {file_path}: {str(e)}")
            
            # Generate a summary of the deletion
            summary = f"Deleted {len(deleted_files)} files from {full_directory}."
            
            # Add details about deleted files
            if deleted_files:
                if len(deleted_files) <= 10:
                    files_str = '\n'.join([f"- {file}" for file in deleted_files])
                    summary += f"\n\nDeleted files:\n{files_str}"
                else:
                    files_sample = '\n'.join([f"- {file}" for file in deleted_files[:10]])
                    summary += f"\n\nSample of deleted files (showing 10 of {len(deleted_files)}):\n{files_sample}"
            
            return {
                "success": True,
                "summary": summary,
                "directory": full_directory,
                "files_deleted": len(deleted_files),
                "deleted_files": deleted_files,
                "task": task
            }
            
        except Exception as e:
            logger.error(f"Error deleting files: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "task": task
            }
    
    async def organize_files(self, task: str) -> Dict[str, Any]:
        """
        Find and organize files based on their content and type.
        
        Args:
            task: The task description containing the file organization request
            
        Returns:
            Dict containing the result of the file organization operation
        """
        try:
            # Extract file type and directory from the task
            file_type_match = re.search(r'(?:find|organize)\s+(?:all\s+)?([\w\d]+)\s+files', task, re.IGNORECASE)
            directory_match = re.search(r'(?:in|from)\s+(?:my\s+)?([\w\d\s]+)\s+(?:folder|directory)', task, re.IGNORECASE)
            
            # Default values
            file_type = file_type_match.group(1).lower() if file_type_match else None
            directory = directory_match.group(1).strip() if directory_match else "Downloads"
            
            # Map common directory names to actual paths
            directory_map = {
                "downloads": os.path.expanduser("~/Downloads"),
                "documents": os.path.expanduser("~/Documents"),
                "desktop": os.path.expanduser("~/Desktop"),
                "pictures": os.path.expanduser("~/Pictures"),
                "music": os.path.expanduser("~/Music"),
                "videos": os.path.expanduser("~/Videos")
            }
            
            # Get the actual directory path
            directory_path = directory_map.get(directory.lower(), os.path.expanduser(f"~/{directory}"))
            
            # Check if the directory exists
            if not os.path.exists(directory_path):
                return {
                    "success": False,
                    "error": f"Directory '{directory_path}' does not exist"
                }
            
            # Find files of the specified type
            files = []
            if file_type:
                # Handle common file types
                extension_map = {
                    "pdf": ".pdf",
                    "document": ".docx",
                    "spreadsheet": ".xlsx",
                    "presentation": ".pptx",
                    "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
                    "video": [".mp4", ".avi", ".mov", ".mkv"],
                    "audio": [".mp3", ".wav", ".ogg", ".flac"],
                    "text": ".txt"
                }
                
                extensions = extension_map.get(file_type.lower(), f".{file_type.lower()}")
                
                # Find all files with the specified extension(s)
                for root, _, filenames in os.walk(directory_path):
                    for filename in filenames:
                        if isinstance(extensions, list):
                            if any(filename.lower().endswith(ext) for ext in extensions):
                                files.append(os.path.join(root, filename))
                        else:
                            if filename.lower().endswith(extensions):
                                files.append(os.path.join(root, filename))
            
            # If no files found, return an error
            if not files:
                return {
                    "success": False,
                    "error": f"No {file_type} files found in '{directory_path}'"
                }
            
            # Generate a system prompt for analyzing file topics
            system_prompt = f"""You are an expert at analyzing file content and categorizing files by topic.
            For each file name, determine the most likely topic category based on the file name and any keywords present.
            Respond with a JSON object where keys are file paths and values are topic categories.
            Choose from these topic categories: Work, Education, Finance, Personal, Entertainment, Health, Travel, Technology, Other.
            If you can't determine a category, use 'Other'."""
            
            # Generate a prompt for the model to categorize files
            file_list = "\n".join([f"- {os.path.basename(file)}" for file in files])
            categorization_prompt = f"Categorize these files by topic based on their names:\n{file_list}"
            
            # Get categorization from the model
            categorization_result = await self._generate_completion(categorization_prompt, system_prompt)
            
            # Extract JSON from the response
            json_match = re.search(r'\{[^\}]+\}', categorization_result.get("result", ""))
            categories = {}
            
            if json_match:
                try:
                    # Parse the JSON response
                    categories_raw = json.loads(json_match.group(0))
                    
                    # Map the categories to file paths
                    for i, file in enumerate(files):
                        file_basename = os.path.basename(file)
                        for key, value in categories_raw.items():
                            if key.lower() in file_basename.lower() or file_basename.lower() in key.lower():
                                categories[file] = value
                                break
                        if file not in categories:
                            categories[file] = "Other"
                except json.JSONDecodeError:
                    # If JSON parsing fails, assign default categories
                    for file in files:
                        categories[file] = "Other"
            else:
                # If no JSON found, assign default categories
                for file in files:
                    categories[file] = "Other"
            
            # Create folders for each category
            category_folders = {}
            for category in set(categories.values()):
                category_folder = os.path.join(directory_path, category)
                if not os.path.exists(category_folder):
                    os.makedirs(category_folder)
                category_folders[category] = category_folder
            
            # Move files to their respective category folders
            moved_files = {}
            for file, category in categories.items():
                try:
                    destination = os.path.join(category_folders[category], os.path.basename(file))
                    # If the file already exists in the destination, add a suffix
                    if os.path.exists(destination):
                        base, ext = os.path.splitext(destination)
                        counter = 1
                        while os.path.exists(f"{base}_{counter}{ext}"):
                            counter += 1
                        destination = f"{base}_{counter}{ext}"
                    
                    # Move the file
                    shutil.move(file, destination)
                    moved_files[file] = destination
                except Exception as e:
                    logger.error(f"Error moving file {file}: {str(e)}")
            
            # Generate a summary of the organization
            summary = f"Found {len(files)} {file_type} files in '{directory_path}'\n"
            summary += f"Organized into {len(category_folders)} categories:\n"
            
            for category, folder in category_folders.items():
                count = sum(1 for _, cat in categories.items() if cat == category)
                summary += f"- {category}: {count} files\n"
            
            return {
                "success": True,
                "file_type": file_type,
                "directory": directory_path,
                "files_found": len(files),
                "categories": list(category_folders.keys()),
                "summary": summary
            }
        except Exception as e:
            logger.error(f"Error organizing files: {str(e)}")
            return {
                "success": False,
                "error": f"Error organizing files: {str(e)}"
            }
    
    async def _handle_file_operation_task(self, task: str) -> Dict[str, Any]:
        """
        Handle tasks related to file operations like saving images or creating directories.
        This is a real implementation that performs actual file operations.
        
        Args:
            task: The task description containing the file operation request
            
        Returns:
            Dict containing the results of the file operations
        """
        try:
            # Extract operation type and parameters
            task_lower = task.lower()
            
            # Handle file creation with the /create command syntax
            if task_lower.startswith("/create") or ("create" in task_lower and ("file" in task_lower or "document" in task_lower or "." in task)):
                # Check if it's using the command syntax: /create [filename] [content]
                if task_lower.startswith("/create"):
                    # Remove the /create command
                    create_request = task[8:].strip()
                    
                    # Check for the natural language syntax: /create [request] and save to [filename]
                    save_to_match = re.search(r'(.+?)\s+(?:and\s+)?(?:save|write)\s+(?:to|as|in)\s+([^\s]+)', create_request, re.IGNORECASE)
                    
                    if save_to_match:
                        # Natural language format
                        content_request = save_to_match.group(1).strip()
                        filename = save_to_match.group(2).strip()
                        return await self.create_file(content_request, filename)
                    else:
                        # Standard format - try to extract filename and content
                        parts = create_request.split(None, 1)
                        if len(parts) >= 2:
                            filename = parts[0].strip()
                            content = parts[1].strip()
                            return await self.create_file(content, filename)
                        else:
                            return {
                                "success": False,
                                "message": "Invalid /create command format. Use '/create [filename] [content]' or '/create [request] and save to [filename]'.",
                                "error": "Invalid command format"
                            }
                else:
                    # Natural language file creation request
                    # Extract potential filename from the request
                    filename = None
                    
                    # Look for "create a [filetype] file" pattern
                    file_type_match = re.search(r'create\s+(?:a|an)\s+([a-z]+)\s+(?:file|document)', task_lower)
                    if file_type_match:
                        file_type = file_type_match.group(1)
                        # Map common file type names to extensions
                        file_type_map = {
                            "text": ".txt",
                            "word": ".docx",
                            "excel": ".xlsx",
                            "spreadsheet": ".xlsx",
                            "csv": ".csv",
                            "pdf": ".pdf",
                            "markdown": ".md",
                            "python": ".py",
                            "javascript": ".js",
                            "html": ".html",
                            "css": ".css",
                            "json": ".json"
                        }
                        
                        # Look for "save to [filename]" pattern
                        save_to_match = re.search(r'(?:save|write)\s+(?:to|as|in)\s+([^\s]+)', task, re.IGNORECASE)
                        if save_to_match:
                            filename = save_to_match.group(1)
                        else:
                            # Generate a filename based on the task
                            filename_prompt = f"Based on this request: '{task}', suggest an appropriate filename with {file_type_map.get(file_type, '.txt')} extension. Only respond with the filename, nothing else."
                            filename_response = await self._generate_completion(filename_prompt)
                            filename = filename_response.get("result", "").strip()
                            
                            # Ensure it has the right extension
                            if not filename.endswith(file_type_map.get(file_type, '.txt')):
                                filename += file_type_map.get(file_type, '.txt')
                    
                    # Use the create_file method to handle the request
                    return await self.create_file(task, filename)
            
            # Handle directory creation
            if "create folder" in task_lower or "make directory" in task_lower:
                # Extract directory path
                directory_path = self._extract_path(task)
                if not directory_path:
                    # Use Ollama to suggest a good path based on the task
                    path_prompt = f"Based on this request: '{task}', suggest an appropriate directory path. Only respond with the path, nothing else."
                    path_response = await self._generate_completion(path_prompt)
                    suggested_path = path_response.get("result", "").strip()
                    
                    if os.path.sep in suggested_path or "~" in suggested_path:
                        directory_path = suggested_path
                    else:
                        directory_path = os.path.expanduser(f"~/Documents/{suggested_path}")
                
                # Create the directory
                result = self._create_directory(directory_path)
                return {
                    "success": True,
                    "result": result,
                    "task": task,
                    "operation": "create_directory",
                    "path": directory_path
                }
            
            # Handle file saving/downloading
            elif "save" in task_lower or "download" in task_lower:
                # Check if it's about saving an image from a URL
                if "image" in task_lower and ("http" in task or "www" in task):
                    # Extract URL and destination path
                    url = self._extract_url(task)
                    destination = self._extract_path(task)
                    
                    if not url:
                        return {
                            "success": False,
                            "error": "No URL found in the task",
                            "task": task
                        }
                    
                    if not destination:
                        # Use Ollama to suggest a good filename
                        filename_prompt = f"Based on this URL: '{url}' and task: '{task}', suggest an appropriate filename with extension. Only respond with the filename, nothing else."
                        filename_response = await self._generate_completion(filename_prompt)
                        suggested_filename = filename_response.get("result", "").strip()
                        
                        if "." in suggested_filename and len(suggested_filename) > 3:
                            destination = os.path.expanduser(f"~/Downloads/{suggested_filename}")
                        else:
                            # Extract a filename from the URL
                            file_name = url.split("/")[-1]
                            if not file_name or len(file_name) < 3 or "." not in file_name:
                                file_name = f"image_{int(time.time())}.jpg"
                            destination = os.path.expanduser(f"~/Downloads/{file_name}")
                    
                    # Download and save the file
                    result = self._download_file(url, destination)
                    return {
                        "success": True,
                        "result": result,
                        "task": task,
                        "operation": "save_file",
                        "url": url,
                        "path": destination
                    }
                # Handle saving text to a file
                elif "text" in task_lower or "content" in task_lower or ".txt" in task_lower or any(ext in task_lower for ext in [".md", ".py", ".js", ".html", ".css", ".json", ".csv"]):
                    # Check if this is a request to create a file with content
                    if re.search(r'(create|write|generate)\s+(?:a|an)?\s+(?:text|file|document)', task_lower):
                        # This is likely a file creation request, use the create_file method
                        return await self.create_file(task)
                    else:
                        # Extract content and path
                        content = self._extract_content(task)
                        path = self._extract_path(task)
                        
                        if not path:
                            # Use Ollama to suggest a good filename
                            filename_prompt = f"Based on this task: '{task}', suggest an appropriate filename with extension. Only respond with the filename, nothing else."
                            filename_response = await self._generate_completion(filename_prompt)
                            suggested_filename = filename_response.get("result", "").strip()
                            
                            if "." in suggested_filename and len(suggested_filename) > 5:
                                path = os.path.expanduser(f"~/Documents/{suggested_filename}")
                            else:
                                path = os.path.expanduser(f"~/Documents/ollama_shell_{int(time.time())}.txt")
                        
                        # Save the content to the file
                        result = self._save_text_file(path, content)
                        return {
                            "success": True,
                            "result": result,
                            "task": task,
                            "operation": "save_text",
                            "path": path
                        }
            
            # For other file operations, generate a plan using Ollama and execute it
            plan_prompt = f"I need to {task}. Provide a step-by-step plan to accomplish this using Python. Format your response as JSON with 'steps' as a list of operations."
            plan_response = await self._generate_completion(plan_prompt)
            
            # Try to extract and execute the plan
            try:
                import json
                plan_text = plan_response.get("result", "")
                # Try to extract JSON from the text
                json_match = re.search(r'\{[^\}]+\}', plan_text)
                if json_match:
                    plan_json = json.loads(json_match.group(0))
                    steps = plan_json.get("steps", [])
                    
                    if steps and isinstance(steps, list):
                        # Execute the first step as a demonstration
                        first_step = steps[0]
                        step_description = f"I've analyzed your request and can help with this file operation.\n\nHere's what I'll do:\n"
                        for i, step in enumerate(steps, 1):
                            step_description += f"{i}. {step}\n"
                        
                        return {
                            "success": True,
                            "result": step_description,
                            "task": task,
                            "operation": "file_operation_plan"
                        }
            except Exception as plan_error:
                logger.warning(f"Could not parse operation plan: {str(plan_error)}")
            
            # Default response if we couldn't handle the operation
            return await self._generate_completion(f"How to {task}")
        except Exception as e:
            logger.error(f"Error handling file operation task: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "task": task
            }
    
    async def _handle_create_command(self, args: str) -> Dict[str, Any]:
        """
        Handle the /create command for file creation.
        
        This command supports two syntax options:
        1. Standard syntax: /create [filename] [content]
        2. Natural language syntax: /create [request] and save to [filename]
        
        Args:
            args: The arguments for the command (everything after /create)
            
        Returns:
            A dictionary containing the result of the file creation operation
        """
        if not args:
            return {
                "success": False,
                "message": "Invalid /create command format. Use '/create [filename] [content]' or '/create [request] and save to [filename]'.",
                "error": "Missing arguments"
            }
        
        # Check for the natural language syntax: /create [request] and save to [filename]
        save_to_match = re.search(r'(.+?)\s+(?:and\s+)?(?:save|write)\s+(?:to|as|in)\s+([^\s]+)', args, re.IGNORECASE)
        
        if save_to_match:
            # Natural language format
            content_request = save_to_match.group(1).strip()
            filename = save_to_match.group(2).strip()
            return await self.create_file(content_request, filename)
        else:
            # Standard format - try to extract filename and content
            parts = args.split(None, 1)
            if len(parts) >= 2:
                filename = parts[0].strip()
                content = parts[1].strip()
                
                # For standard format, we need to swap the arguments
                # because create_file expects (request, filename) but we have (filename, content)
                # In this case, we're using the content directly, not as a request to generate content
                return await self.create_file(content, filename, is_direct_content=True)
            else:
                return {
                    "success": False,
                    "message": "Invalid /create command format. Use '/create [filename] [content]' or '/create [request] and save to [filename]'.",
                    "error": "Invalid command format"
                }
    
    def _extract_search_terms(self, task: str) -> Tuple[str, Dict[str, Any]]:
        """
        Extract search terms and parameters from a task description.
        
        Args:
            task: The task description
            
        Returns:
            Tuple containing extracted search terms and a dictionary of search parameters
        """
        # Initialize search parameters dictionary
        search_params = {
            'format': None,  # jpg, png, etc.
            'size': None,    # large, medium, small
            'color': None,   # color, black and white
            'type': None,    # photo, illustration, etc.
            'count': None    # number of images to download
        }
        
        # Extract image format preferences
        format_match = re.search(r'\b(jpe?g|png|gif|bmp|webp|svg)\s+(?:format|images?|pictures?|files?)\b', task, re.IGNORECASE)
        if format_match:
            search_params['format'] = format_match.group(1).lower()
            task = re.sub(r'\b' + re.escape(format_match.group(0)) + r'\b', '', task, flags=re.IGNORECASE)
        
        # Extract image size preferences
        size_match = re.search(r'\b(large|medium|small|high\s+resolution|low\s+resolution)\s+(?:size|images?|pictures?)\b', task, re.IGNORECASE)
        if size_match:
            search_params['size'] = size_match.group(1).lower()
            task = re.sub(r'\b' + re.escape(size_match.group(0)) + r'\b', '', task, flags=re.IGNORECASE)
        
        # Extract color preferences
        color_match = re.search(r'\b(colou?r|black\s+and\s+white|monochrome|grayscale)\s+(?:images?|pictures?)\b', task, re.IGNORECASE)
        if color_match:
            search_params['color'] = color_match.group(1).lower()
            task = re.sub(r'\b' + re.escape(color_match.group(0)) + r'\b', '', task, flags=re.IGNORECASE)
        
        # Extract image type preferences
        type_match = re.search(r'\b(photos?|illustrations?|cliparts?|line\s+drawings?|animations?)\b', task, re.IGNORECASE)
        if type_match:
            search_params['type'] = type_match.group(1).lower()
            task = re.sub(r'\b' + re.escape(type_match.group(0)) + r'\b', '', task, flags=re.IGNORECASE)
        
        # Extract count of images to download - improved pattern matching
        count_match = re.search(r'\b(\d+)\s+(?:images?|pictures?|photos?|pics?)\b', task, re.IGNORECASE)
        if not count_match:
            # Try alternative pattern that looks for numbers at the beginning of the request
            count_match = re.search(r'\b(?:search|find|get|download)\s+(?:for\s+)?(\d+)\b', task, re.IGNORECASE)
        
        if count_match:
            search_params['count'] = int(count_match.group(1))
            task = re.sub(r'\b' + re.escape(count_match.group(0)) + r'\b', '', task, flags=re.IGNORECASE)
            
        # First, remove folder/file save instructions to avoid including them in search terms
        clean_task = task
        
        # Remove folder save instructions - expanded patterns to catch more variations
        folder_patterns = [
            # Standard patterns with 'and save'
            r'\s+and\s+save\s+(?:them|it|the\s+results?|the\s+images?|the\s+photos?)\s+(?:to|in|into)\s+(?:a\s+)?(?:folder|directory)\s+(?:named|called)\s+["\'](.*?)["\'](\s|$)',
            r'\s+and\s+save\s+(?:them|it|the\s+results?|the\s+images?|the\s+photos?)\s+(?:to|in|into)\s+(?:a\s+)?(?:folder|directory)\s+(?:named|called)\s+([\w-]+)(\s|$)',
            
            # Direct save commands
            r'\s+(?:save|store)\s+(?:them|it|the\s+results?|the\s+images?|the\s+photos?)\s+(?:to|in|into)\s+(?:a\s+)?(?:folder|directory)\s+(?:named|called)\s+["\'](.*?)["\'](\s|$)',
            r'\s+(?:save|store)\s+(?:them|it|the\s+results?|the\s+images?|the\s+photos?)\s+(?:to|in|into)\s+(?:a\s+)?(?:folder|directory)\s+(?:named|called)\s+([\w-]+)(\s|$)',
            
            # Patterns with folder name first
            r'\s+(?:to|in|into)\s+(?:a\s+)?(?:folder|directory)\s+(?:named|called)\s+["\'](.*?)["\']\s+(?:save|store)\s+(?:them|it|the\s+results?|the\s+images?|the\s+photos?)(\s|$)',
            r'\s+(?:to|in|into)\s+(?:a\s+)?(?:folder|directory)\s+(?:named|called)\s+([\w-]+)\s+(?:save|store)\s+(?:them|it|the\s+results?|the\s+images?|the\s+photos?)(\s|$)',
            
            # Simpler patterns
            r'\s+(?:to|in|into)\s+(?:a\s+)?(?:folder|directory)\s+["\'](.*?)["\'](\s|$)',
            r'\s+(?:to|in|into)\s+(?:a\s+)?(?:folder|directory)\s+([\w-]+)(\s|$)'
        ]
        
        for pattern in folder_patterns:
            clean_task = re.sub(pattern, '', clean_task, flags=re.IGNORECASE)
        
        # Remove file save instructions - expanded patterns to catch more variations
        file_patterns = [
            # Standard patterns with 'and save'
            r'\s+and\s+save\s+(?:them|it|the\s+results?|the\s+images?|the\s+photos?)\s+(?:to|in|into)\s+(?:a\s+)?file\s+(?:named|called)\s+["\'](.*?)["\'](\s|$)',
            r'\s+and\s+save\s+(?:them|it|the\s+results?|the\s+images?|the\s+photos?)\s+(?:to|in|into)\s+(?:a\s+)?file\s+(?:named|called)\s+([\w.-]+)(\s|$)',
            
            # Direct save commands
            r'\s+(?:save|store)\s+(?:them|it|the\s+results?|the\s+images?|the\s+photos?)\s+(?:to|in|into)\s+(?:a\s+)?file\s+(?:named|called)\s+["\'](.*?)["\'](\s|$)',
            r'\s+(?:save|store)\s+(?:them|it|the\s+results?|the\s+images?|the\s+photos?)\s+(?:to|in|into)\s+(?:a\s+)?file\s+(?:named|called)\s+([\w.-]+)(\s|$)',
            
            # Patterns with file name first
            r'\s+(?:to|in|into)\s+(?:a\s+)?file\s+(?:named|called)\s+["\'](.*?)["\']\s+(?:save|store)\s+(?:them|it|the\s+results?|the\s+images?|the\s+photos?)(\s|$)',
            r'\s+(?:to|in|into)\s+(?:a\s+)?file\s+(?:named|called)\s+([\w.-]+)\s+(?:save|store)\s+(?:them|it|the\s+results?|the\s+images?|the\s+photos?)(\s|$)',
            
            # Direct file patterns
            r'\s+(?:to|in|into)\s+(?:a\s+)?file\s+["\'](.*?)["\'](\s|$)',
            r'\s+(?:to|in|into)\s+(?:a\s+)?file\s+([\w.-]+)(\s|$)',
            
            # File extension patterns
            r'\s+(?:to|in|into)\s+["\'](.*?\.txt)["\'](\s|$)',
            r'\s+(?:to|in|into)\s+([\w.-]+\.txt)(\s|$)'
        ]
        
        for pattern in file_patterns:
            clean_task = re.sub(pattern, '', clean_task, flags=re.IGNORECASE)
        
        # Log the cleaned task for debugging
        logger.debug(f"Original task: {task}")
        logger.debug(f"Cleaned task for search: {clean_task}")
        
        # Now extract search terms from the cleaned task
        patterns = [
            # Standard search patterns
            r"(?:search|find|look)\s+(?:for\s+)?(?:images?|pictures?|photos?)\s+(?:of\s+)?['\"]?([^'\"]+)['\"]?",
            r"(?:images?|pictures?|photos?)\s+(?:of|about|related to)\s+['\"]?([^'\"]+)['\"]?",
            r"(?:find|get|search)\s+['\"]?([^'\"]+)['\"]?\s+(?:images?|pictures?|photos?)",
            
            # More generic patterns
            r"(?:show|display|get)\s+me\s+(?:some\s+)?(?:images?|pictures?|photos?)\s+(?:of\s+)?['\"]?([^'\"]+)['\"]?",
            r"(?:I\s+want|I\s+need|I'm\s+looking\s+for)\s+(?:images?|pictures?|photos?)\s+(?:of\s+)?['\"]?([^'\"]+)['\"]?"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, clean_task, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Fallback: remove common words and extract the rest
        words = clean_task.lower().split()
        stop_words = ["search", "find", "for", "images", "image", "pictures", "picture", "photos", "photo", "of", "the", "a", "an", "please", "ten", "majestic"]
        search_terms = [word for word in words if word not in stop_words]
        
        # Initialize search parameters dictionary
        search_params = {
            'format': None,  # jpg, png, etc.
            'size': None,    # large, medium, small
            'color': None,   # color, black and white
            'type': None,    # photo, illustration, etc.
            'count': None    # number of images to download
        }
        
        # Return both the search terms and parameters
        return (" ".join(search_terms) if search_terms else "nature"), search_params  # Default to "nature" if nothing found
    
    def _perform_image_search(self, query: str, max_results: int = 10, search_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
        """
        Perform an actual image search using web search techniques.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            search_params: Optional dictionary of search parameters (format, size, color, type)
            
        Returns:
            List of image search results
        """
        # Initialize search parameters if not provided
        if search_params is None:
            search_params = {
                'format': None,
                'size': None,
                'color': None,
                'type': None,
                'count': None
            }
        try:
            # In a production environment, this would use a proper search API
            # For now, we'll use a combination of techniques to find real images
            
            # Construct search URL with parameters
            search_query = query
            search_params_list = []
            
            # Add format parameter if specified
            if search_params['format']:
                search_query += f" {search_params['format']} format"
                search_params_list.append(f"imgtype={search_params['format']}")
            
            # Add size parameter if specified
            if search_params['size']:
                size_param = None
                if search_params['size'] == 'large':
                    size_param = 'l'
                elif search_params['size'] == 'medium':
                    size_param = 'm'
                elif search_params['size'] == 'small':
                    size_param = 's'
                elif 'high' in search_params['size']:
                    size_param = 'l'
                elif 'low' in search_params['size']:
                    size_param = 's'
                
                if size_param:
                    search_query += f" {search_params['size']} size"
                    search_params_list.append(f"imgsz={size_param}")
            
            # Add color parameter if specified
            if search_params['color']:
                color_param = None
                if search_params['color'] in ['color', 'colour']:
                    color_param = 'color'
                elif any(term in search_params['color'] for term in ['black and white', 'monochrome', 'grayscale']):
                    color_param = 'mono'
                
                if color_param:
                    search_query += f" {search_params['color']}"
                    search_params_list.append(f"imgc={color_param}")
            
            # Add type parameter if specified
            if search_params['type']:
                type_param = None
                if 'photo' in search_params['type']:
                    type_param = 'photo'
                elif 'illustration' in search_params['type']:
                    type_param = 'clipart'
                elif 'clipart' in search_params['type']:
                    type_param = 'clipart'
                elif 'line drawing' in search_params['type']:
                    type_param = 'lineart'
                elif 'animation' in search_params['type']:
                    type_param = 'animated'
                
                if type_param:
                    search_query += f" {search_params['type']}"
                    search_params_list.append(f"imgtype={type_param}")
            
            # Construct the final search URL
            search_url = f"https://images.google.com/search?q={urllib.parse.quote(search_query)}&tbm=isch"
            
            # Add any additional search parameters
            if search_params_list:
                search_url += "&" + "&".join(search_params_list)
                
            logger.info(f"Constructed search URL: {search_url}")
            
            # Create a list to store results
            results = []
            
            # Try to fetch some image results from the search URL
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                response = requests.get(search_url, headers=headers, timeout=5)
                
                if response.status_code == 200:
                    # Extract image URLs from the response
                    # This is a simplified approach and might not work perfectly
                    img_urls = re.findall(r'"(https://[^"]+\.(?:jpg|jpeg|png|gif))"', response.text)
                    
                    # Create result entries for each found image
                    for i, img_url in enumerate(img_urls[:max_results]):
                        results.append({
                            "title": f"{query.title()} image {i+1}",
                            "url": img_url,
                            "thumbnail": img_url,
                            "source": "Google Images"
                        })
            except Exception as search_error:
                logger.warning(f"Error during image search: {str(search_error)}")
            
            # If we couldn't get results from the search, use some fallback images
            if not results:
                # Use Unsplash API for fallback images (no API key required for this URL format)
                # Construct the unsplash query with search parameters
                unsplash_query = query
                
                # Add format/type parameter if specified
                if search_params['type']:
                    unsplash_query += f",{search_params['type']}"
                elif search_params['format']:
                    unsplash_query += f",{search_params['format']}"
                
                # Add color parameter if specified
                if search_params['color']:
                    unsplash_query += f",{search_params['color']}"
                
                # Construct the final Unsplash URL
                unsplash_url = f"https://source.unsplash.com/featured/?{urllib.parse.quote(unsplash_query)}"
                
                # Create some fallback results
                for i in range(min(5, max_results)):
                    results.append({
                        "title": f"{query.title()} image {i+1}",
                        "url": f"{unsplash_url}&sig={i}",  # Add a parameter to get different images
                        "thumbnail": f"{unsplash_url}&sig={i}&w=100",
                        "source": "Unsplash"
                    })
            
            return results
        except Exception as e:
            logger.error(f"Error performing image search: {str(e)}")
            return []
    
    def _download_image(self, url: str, search_terms: str, target_folder: Optional[str] = None, search_params: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Download an image from a URL to a local file.
        
        Args:
            url: URL of the image to download
            search_terms: Search terms used to find the image (for filename)
            target_folder: Optional folder path to save the image to
            search_params: Optional dictionary of search parameters (format, size, color, type)
            
        Returns:
            Path to the downloaded image, or None if download failed
        """
        try:
            # Determine the download directory
            if target_folder and os.path.exists(target_folder):
                download_dir = target_folder
                logger.info(f"Using specified folder for image download: {download_dir}")
            else:
                # Create a default directory for downloaded images if it doesn't exist
                download_dir = os.path.expanduser("~/Downloads/ollama_shell_images")
                os.makedirs(download_dir, exist_ok=True)
                logger.info(f"Using default folder for image download: {download_dir}")
            
            # Generate a filename based on search terms and parameters
            safe_terms = search_terms.replace(" ", "_").replace("/", "_").lower()
            timestamp = int(time.time())
            
            # Add search parameters to filename if provided
            param_parts = []
            if search_params:
                if search_params.get('format'):
                    param_parts.append(search_params['format'])
                if search_params.get('size'):
                    param_parts.append(search_params['size'])
                if search_params.get('color'):
                    param_parts.append(search_params['color'].replace(" ", "_"))
                if search_params.get('type'):
                    param_parts.append(search_params['type'].replace(" ", "_"))
                    
            # Combine search terms with parameters if any exist
            if param_parts:
                safe_terms = f"{safe_terms}_{'_'.join(param_parts)}"
            
            # Try to determine the file extension from the URL
            extension = "jpg"  # Default extension
            url_lower = url.lower()
            if ".png" in url_lower:
                extension = "png"
            elif ".gif" in url_lower:
                extension = "gif"
            elif ".webp" in url_lower:
                extension = "webp"
            elif ".jpeg" in url_lower or ".jpg" in url_lower:
                extension = "jpg"
            
            filename = f"{safe_terms}_{timestamp}.{extension}"
            filepath = os.path.join(download_dir, filename)
            
            # Download the image with proper headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            # Try to download from the URL
            try:
                response = requests.get(url, headers=headers, stream=True, timeout=10)
                response.raise_for_status()
                
                # Check if the response is an image
                content_type = response.headers.get('Content-Type', '')
                if not content_type.startswith('image/'):
                    logger.warning(f"URL does not point to an image. Content-Type: {content_type}")
                    # Try to find an image URL in the response if it's HTML
                    if content_type.startswith('text/html'):
                        img_match = re.search(r'<img[^>]+src=["\']((?!data:)[^"\'>=]+)["\']', response.text)
                        if img_match:
                            img_url = img_match.group(1)
                            # Convert relative URL to absolute if needed
                            if img_url.startswith('/'):
                                parsed_url = urllib.parse.urlparse(url)
                                img_url = f"{parsed_url.scheme}://{parsed_url.netloc}{img_url}"
                            # Recursively try to download the found image URL
                            return self._download_image(img_url, search_terms, target_folder, search_params)
                
                # Save the image to file
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                logger.info(f"Successfully downloaded image to {filepath}")
                return filepath
            except Exception as download_error:
                logger.warning(f"Could not download from URL: {str(download_error)}")
                
                # Try an alternative approach with urllib
                try:
                    opener = urllib.request.build_opener()
                    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
                    urllib.request.install_opener(opener)
                    urllib.request.urlretrieve(url, filepath)
                    logger.info(f"Successfully downloaded image using urllib to {filepath}")
                    return filepath
                except Exception as urllib_error:
                    logger.warning(f"Could not download with urllib: {str(urllib_error)}")
                    
                    # As a last resort, try with Unsplash as a fallback
                    try:
                        # Construct the fallback query with search parameters
                        fallback_query = search_terms
                        
                        # Add parameters to the fallback query if available
                        if search_params:
                            if search_params.get('type'):
                                fallback_query += f",{search_params['type']}"
                            elif search_params.get('format'):
                                fallback_query += f",{search_params['format']}"
                            if search_params.get('color'):
                                fallback_query += f",{search_params['color']}"
                                
                        fallback_url = f"https://source.unsplash.com/featured/?{urllib.parse.quote(fallback_query)}"
                        urllib.request.urlretrieve(fallback_url, filepath)
                        logger.info(f"Used fallback image from Unsplash: {filepath}")
                        return filepath
                    except Exception as fallback_error:
                        logger.error(f"All download attempts failed: {str(fallback_error)}")
            
            return None
        except Exception as e:
            logger.error(f"Error in download_image: {str(e)}")
            return None
    
    def _extract_url(self, task: str) -> Optional[str]:
        """
        Extract a URL from a task description.
        
        Args:
            task: The task description
            
        Returns:
            Extracted URL or None if not found
        """
        url_match = re.search(r'https?://[^\s"\']+', task)
        if url_match:
            return url_match.group(0).rstrip('.,;:"')
        return None
    
    def _extract_path(self, task: str) -> Optional[str]:
        """
        Extract a file or directory path from a task description.
        
        Args:
            task: The task description
            
        Returns:
            Extracted path or None if not found
        """
        # Try to find path patterns
        path_patterns = [
            r"(?:to|in|at|into)\s+['\"]?((?:/|~/|\./)[^'\"\s]+)['\"]?",  # Unix-like paths
            r"(?:to|in|at|into)\s+['\"]?([A-Za-z]:\\[^'\"\s]+)['\"]?",  # Windows paths
            r"(?:to|in|at|into)\s+['\"]?((?:\w+/)+\w+(?:\.\w+)?)['\"]?",  # Relative paths
            r"(?:to|in|at|into)\s+['\"]?(~/[^'\"\s]+)['\"]?"  # Home directory paths
        ]
        
        for pattern in path_patterns:
            match = re.search(pattern, task, re.IGNORECASE)
            if match:
                path = match.group(1)
                # Expand user directory if needed
                if path.startswith("~"):
                    path = os.path.expanduser(path)
                return path
        
        return None
    
    def _extract_content(self, task: str) -> str:
        """
        Extract content to be saved from a task description.
        
        Args:
            task: The task description
            
        Returns:
            Extracted content or a default message
        """
        # Try to find content between quotes
        content_match = re.search(r"['\"]([^'\"]+)['\"](?:\s+to|\s+in|\s+into)", task)
        if content_match:
            return content_match.group(1)
        
        # If no explicit content is found, generate some based on the task
        content_prompt = f"Generate content based on this request: {task}"
        try:
            response = requests.post(
                f"{self.ollama_base_url}/generate",
                json={
                    "model": self.model,
                    "prompt": content_prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            return response.json().get("response", f"Content generated for: {task}")
        except Exception as e:
            logger.error(f"Error generating content: {str(e)}")
            return f"Content generated for: {task}\n\nThis is placeholder content."
    
    def _create_directory(self, directory_path: str) -> str:
        """
        Create a directory at the specified path.
        
        Args:
            directory_path: Path where the directory should be created
            
        Returns:
            Message indicating the result of the operation
        """
        try:
            # Ensure the directory path is absolute
            if not os.path.isabs(directory_path):
                directory_path = os.path.abspath(directory_path)
            
            # Create the directory and any necessary parent directories
            os.makedirs(directory_path, exist_ok=True)
            return f"Successfully created directory at {directory_path}"
        except Exception as e:
            logger.error(f"Error creating directory: {str(e)}")
            return f"Failed to create directory: {str(e)}"
    
    def _download_file(self, url: str, destination: str) -> str:
        """
        Download a file from a URL to a destination path.
        
        Args:
            url: URL of the file to download
            destination: Path where the file should be saved
            
        Returns:
            Message indicating the result of the operation
        """
        try:
            # Ensure the destination directory exists
            os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)
            
            # Download the file with proper headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            # Try to download from the URL
            try:
                response = requests.get(url, headers=headers, stream=True, timeout=10)
                response.raise_for_status()
                
                # Save the file
                with open(destination, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                return f"Successfully downloaded file from {url} to {destination}"
            except Exception as download_error:
                logger.error(f"Error downloading file with requests: {str(download_error)}")
                
                # Try an alternative approach with urllib
                try:
                    opener = urllib.request.build_opener()
                    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
                    urllib.request.install_opener(opener)
                    urllib.request.urlretrieve(url, destination)
                    return f"Successfully downloaded file from {url} to {destination}"
                except Exception as urllib_error:
                    logger.error(f"Error downloading file with urllib: {str(urllib_error)}")
                    return f"Failed to download file: {str(urllib_error)}"
        except Exception as e:
            logger.error(f"Error in download_file: {str(e)}")
            return f"Failed to download file: {str(e)}"
    
    def _save_text_file(self, path: str, content: str) -> str:
        """
        Save text content to a file.
        
        Args:
            path: Path where the file should be saved
            content: Text content to save
            
        Returns:
            Message indicating the result of the operation
        """
        
    async def analyze_image(self, image_path: str, custom_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze an image using vision-capable models.
        
        This method leverages Ollama's vision capabilities to analyze images that have been
        uploaded or dragged into the chat. It supports all common image formats and can
        provide detailed descriptions and analysis of image content.
        
        Args:
            image_path: Path to the image file to analyze
            custom_prompt: Optional custom prompt to guide the analysis
            
        Returns:
            Dict containing the analysis results
        """
        try:
            # Check if the image file exists
            if not os.path.exists(image_path):
                return {
                    "success": False,
                    "message": f"Image file not found: {image_path}",
                    "error": "File not found"
                }
                
            # Check if the file is an image by extension
            valid_extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]
            file_ext = os.path.splitext(image_path)[1].lower()
            
            if file_ext not in valid_extensions:
                return {
                    "success": False,
                    "message": f"File is not a supported image format: {file_ext}",
                    "error": "Unsupported format"
                }
            
            # Read the image file and encode it as base64
            with open(image_path, "rb") as img_file:
                image_data = img_file.read()
                base64_image = base64.b64encode(image_data).decode("utf-8")
            
            # Prepare the prompt for image analysis
            if custom_prompt:
                prompt = custom_prompt
            else:
                prompt = "Describe this image in detail. Include information about what is shown, any text visible, colors, objects, people, and the overall context or scene."
            
            # Prepare the request to the Ollama API
            request_data = {
                "model": self.vision_model,
                "prompt": prompt,
                "images": [base64_image],
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 1024
                }
            }
            
            logger.info(f"Analyzing image using {self.vision_model} model")
            
            # Send the request to the Ollama API
            response = requests.post(
                f"{self.ollama_base_url}/generate",
                json=request_data
            )
            response.raise_for_status()
            
            # Parse the response
            result = response.json()
            
            # Check if the response contains the expected fields
            if "response" in result:
                analysis_text = result["response"]
                
                return {
                    "success": True,
                    "message": "Image analysis completed successfully",
                    "analysis": analysis_text,
                    "model_used": self.vision_model,
                    "image_path": image_path,
                    "prompt_used": prompt
                }
            else:
                logger.error(f"Unexpected response format: {result}")
                return {
                    "success": False,
                    "message": "Failed to analyze image: Unexpected response format",
                    "error": "API response format error",
                    "raw_response": result
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API request error during image analysis: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to analyze image: API request error",
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Error analyzing image: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to analyze image: {str(e)}",
                "error": str(e)
            }
            
    def _save_text_file(self, path: str, content: str) -> str:
        """
        Save text content to a file.
        
        Args:
            path: Path where the file should be saved
            content: Text content to save
            
        Returns:
            Message indicating the result of the operation
        """
        try:
            # Ensure the destination directory exists
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            
            # Write the content to the file
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            
            return f"Successfully saved content to {path}"
        except Exception as e:
            logger.error(f"Error saving text file: {str(e)}")
            return f"Failed to save text file: {str(e)}"
            
    async def create_file(self, request: str, filename: Optional[str] = None, is_direct_content: bool = False) -> Dict[str, Any]:
        """
        Create a file with generated content based on the user's request.
        
        This method supports creating various file types including:
        - Text files (.txt)
        - CSV files (.csv)
        - Word documents (.doc, .docx) - requires python-docx
        - Excel spreadsheets (.xls, .xlsx) - requires pandas
        - PDF files (.pdf) - requires weasyprint
        
        Args:
            request: The content request or content to save
            filename: Optional filename to save the content to
            is_direct_content: If True, use the request as direct content instead of generating content
            
        Returns:
            Dict containing the result of the file creation operation
        """
        try:
            # Parse the request to extract filename if not provided
            if not filename:
                # Look for "save to [filename]" pattern
                save_to_match = re.search(r'(?:save|write)\s+(?:to|as|in)\s+[\'\"]*(\S+)[\'\"]', request, re.IGNORECASE)
                if save_to_match:
                    filename = save_to_match.group(1)
                    # Remove the "save to" part from the request
                    request = re.sub(r'(?:save|write)\s+(?:to|as|in)\s+[\'\"]*(\S+)[\'\"]', '', request, flags=re.IGNORECASE).strip()
                else:
                    return {
                        "success": False,
                        "message": "No filename specified. Please provide a filename to save the content to.",
                        "error": "Missing filename"
                    }
            
            # Ensure filename has an extension
            if '.' not in filename:
                filename += '.txt'  # Default to .txt if no extension
            
            # Get the file extension
            file_ext = os.path.splitext(filename)[1].lower()
            
            # If is_direct_content is True, use the provided content directly
            # Otherwise, generate content if it appears to be a request rather than content
            if is_direct_content:
                # Use the provided content directly
                content = request
            elif len(request.split()) > 3 and not request.startswith('{'): 
                # This looks like a request for content generation rather than raw content
                content_prompt = f"Generate content for a{file_ext} file based on this request: {request}"
                
                # Generate content using Ollama
                response = await self._generate_completion(content_prompt)
                if response.get("success", False):
                    content = response.get("response", "")
                else:
                    return {
                        "success": False,
                        "message": f"Failed to generate content: {response.get('error', 'Unknown error')}",
                        "error": response.get('error', 'Content generation failed')
                    }
            else:
                # Use the provided content directly
                content = request
            
            # Create the appropriate file type based on extension
            result = ""
            
            # Handle different file types
            if file_ext in [".txt", ".md", ".py", ".js", ".html", ".css", ".json"]:
                # Text files
                result = self._save_text_file(filename, content)
                
            elif file_ext == ".csv":
                # CSV files
                result = self._save_text_file(filename, content)
                
            elif file_ext in [".doc", ".docx"]:
                # Word documents - requires python-docx
                try:
                    from docx import Document
                    document = Document()
                    
                    # Split content by lines and add as paragraphs
                    for line in content.split('\n'):
                        if line.strip():
                            document.add_paragraph(line)
                    
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
                    
                    # Save the document
                    document.save(filename)
                    result = f"Successfully saved Word document to {filename}"
                except ImportError:
                    return {
                        "success": False,
                        "message": "Creating Word documents requires the python-docx package. Please install it with 'pip install python-docx'.",
                        "error": "Missing dependency: python-docx"
                    }
                
            elif file_ext in [".xls", ".xlsx"]:
                # Excel spreadsheets - requires pandas
                try:
                    import pandas as pd
                    
                    # Try to parse content as CSV
                    try:
                        # Create a temporary CSV file
                        temp_csv = os.path.join(os.path.dirname(os.path.abspath(filename)), "temp.csv")
                        with open(temp_csv, "w", encoding="utf-8") as f:
                            f.write(content)
                        
                        # Read CSV into DataFrame
                        df = pd.read_csv(temp_csv)
                        
                        # Save as Excel
                        df.to_excel(filename, index=False)
                        
                        # Remove temporary CSV
                        os.remove(temp_csv)
                        
                        result = f"Successfully saved Excel spreadsheet to {filename}"
                    except Exception as e:
                        # If parsing as CSV fails, create a simple one-column Excel file
                        df = pd.DataFrame({"Content": [line for line in content.split('\n') if line.strip()]})
                        df.to_excel(filename, index=False)
                        result = f"Successfully saved Excel spreadsheet to {filename}"
                except ImportError:
                    return {
                        "success": False,
                        "message": "Creating Excel spreadsheets requires the pandas package. Please install it with 'pip install pandas openpyxl'.",
                        "error": "Missing dependency: pandas"
                    }
                
            elif file_ext == ".pdf":
                # PDF files - requires weasyprint
                try:
                    from weasyprint import HTML
                    
                    # Convert content to HTML
                    html_content = f"<html><body>{content}</body></html>"
                    
                    # Create a temporary HTML file
                    temp_html = os.path.join(os.path.dirname(os.path.abspath(filename)), "temp.html")
                    with open(temp_html, "w", encoding="utf-8") as f:
                        f.write(html_content)
                    
                    # Convert HTML to PDF
                    HTML(filename=temp_html).write_pdf(filename)
                    
                    # Remove temporary HTML file
                    os.remove(temp_html)
                    
                    result = f"Successfully saved PDF to {filename}"
                except ImportError:
                    return {
                        "success": False,
                        "message": "Creating PDF files requires the weasyprint package. Please install it with 'pip install weasyprint'.",
                        "error": "Missing dependency: weasyprint"
                    }
                
            else:
                # Default to text file for unknown extensions
                result = self._save_text_file(filename, content)
            
            return {
                "success": "Failed" not in result,
                "message": result,
                "filename": filename,
                "content_preview": content[:100] + "..." if len(content) > 100 else content
            }
                
        except Exception as e:
            logger.error(f"Error creating file: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to create file: {str(e)}",
                "error": str(e)
            }
