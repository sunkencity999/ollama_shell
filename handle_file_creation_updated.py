"""
Updated implementation of the _handle_file_creation method that uses the improved _extract_filename method.
"""

async def _handle_file_creation(self, task_description: str) -> Dict[str, Any]:
    """
    Handle file creation tasks directly, bypassing the task management system.
    This method overrides the parent class method to add enhanced functionality.
    
    Args:
        task_description: Description of the file creation task
        
    Returns:
        Dict containing the result of the file creation operation
    """
    logger.info(f"Handling file creation task directly: {task_description}")
    
    try:
        # Extract the filename from the task description using our improved method
        filename = self._extract_filename(task_description)
        
        if not filename:
            logger.error(f"No filename could be extracted from: {task_description}")
            return {
                "success": False,
                "task_type": "file_creation",
                "error": "No filename specified",
                "message": "No filename specified. Please provide a filename to save the content to."
            }
        
        # Use the AgenticOllama's create_file method directly
        result = await self.agentic_ollama.create_file(task_description, filename)
        
        # Return a properly formatted result
        success = result.get("success", False)
        message = result.get("message", "File creation completed")
        
        # Extract the result data
        result_data = {}
        if success and "result" in result and isinstance(result["result"], dict):
            result_data = {
                "filename": result["result"].get("filename", "Unknown"),
                "file_type": result["result"].get("file_type", "txt"),
                "content_preview": result["result"].get("content_preview", "No preview available")
            }
        
        return {
            "success": success,
            "task_type": "file_creation",
            "result": result_data,
            "message": message
        }
        
    except Exception as e:
        logger.error(f"Error handling file creation task: {str(e)}")
        return {
            "success": False,
            "task_type": "file_creation",
            "error": str(e),
            "message": f"Failed to create file: {str(e)}"
        }
