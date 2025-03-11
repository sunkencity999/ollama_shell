#!/usr/bin/env python3
"""
Test script for Filesystem MCP Protocol integration

This script tests the Filesystem MCP Protocol integration with Ollama Shell.
"""

import os
import sys
import json
import logging
import unittest
import tempfile
import shutil
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_filesystem_mcp_protocol")

# Try to import MCP
try:
    from mcp.client import MCPClient
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("MCP library not available. Please install it with 'pip install mcp'")

# Import the Filesystem MCP Protocol integration
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from filesystem_mcp_integration import get_filesystem_mcp_integration

class TestFilesystemMCPProtocol(unittest.TestCase):
    """Test cases for the Filesystem MCP Protocol integration."""
    
    @classmethod
    def setUpClass(cls):
        """Set up the test environment."""
        # Skip tests if MCP is not available
        if not MCP_AVAILABLE:
            logger.warning("Skipping tests because MCP is not available")
            return
        
        # Create a temporary directory for testing
        cls.temp_dir = tempfile.mkdtemp(prefix="test_filesystem_mcp_")
        logger.info(f"Created temporary directory: {cls.temp_dir}")
        
        # Create some test files and directories
        cls.test_file_path = os.path.join(cls.temp_dir, "test_file.txt")
        with open(cls.test_file_path, "w") as f:
            f.write("This is a test file for the Filesystem MCP Protocol integration.")
        
        cls.test_dir_path = os.path.join(cls.temp_dir, "test_dir")
        os.makedirs(cls.test_dir_path, exist_ok=True)
        
        # Create a test file in the test directory
        cls.test_nested_file_path = os.path.join(cls.test_dir_path, "nested_file.txt")
        with open(cls.test_nested_file_path, "w") as f:
            f.write("This is a nested test file.")
        
        # Get the Filesystem MCP integration
        cls.integration = get_filesystem_mcp_integration()
        
        # Skip tests if the integration is not available
        if not cls.integration.available:
            logger.warning("Skipping tests because Filesystem MCP Protocol integration is not available")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up the test environment."""
        # Skip cleanup if MCP is not available
        if not MCP_AVAILABLE:
            return
        
        # Shutdown the integration
        if hasattr(cls, "integration") and cls.integration:
            cls.integration.shutdown()
        
        # Remove the temporary directory
        if hasattr(cls, "temp_dir") and os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir)
            logger.info(f"Removed temporary directory: {cls.temp_dir}")
    
    def setUp(self):
        """Set up each test."""
        # Skip tests if MCP is not available
        if not MCP_AVAILABLE or not self.integration.available:
            self.skipTest("MCP or Filesystem MCP Protocol integration is not available")
    
    def test_server_connection(self):
        """Test connection to the Filesystem MCP Protocol server."""
        # Create a client to test the connection
        client = MCPClient(self.integration.server_url)
        
        # Test the connection by getting the server info
        info = client.get_server_info()
        
        # Check that the server info contains the expected name
        self.assertIn("name", info)
        self.assertEqual(info["name"], "Filesystem MCP")
    
    def test_server_resources(self):
        """Test the server resources."""
        # Create a client to test the resources
        client = MCPClient(self.integration.server_url)
        
        # Get the server resources
        resources = client.get_resources()
        
        # Check that the resources contain the expected resources
        expected_resources = [
            "filesystem://config",
            "filesystem://allowed_paths",
            "filesystem://directory/{path}",
            "filesystem://file/{path}",
            "filesystem://analyze/{path}"
        ]
        
        for resource in expected_resources:
            self.assertIn(resource, [r["id"] for r in resources])
    
    def test_server_tools(self):
        """Test the server tools."""
        # Create a client to test the tools
        client = MCPClient(self.integration.server_url)
        
        # Get the server tools
        tools = client.get_tools()
        
        # Check that the tools contain the expected tools
        expected_tools = [
            "fs_list_directory",
            "fs_create_directory",
            "fs_read_file",
            "fs_write_file",
            "fs_append_file",
            "fs_analyze_text",
            "fs_calculate_hash",
            "fs_find_duplicates",
            "fs_create_zip",
            "fs_extract_zip"
        ]
        
        for tool in expected_tools:
            self.assertIn(tool, [t["name"] for t in tools])
    
    def test_list_directory_tool(self):
        """Test the list directory tool."""
        # Create a client to test the tool
        client = MCPClient(self.integration.server_url)
        
        # Call the tool to list the temporary directory
        result = client.call_tool("fs_list_directory", {"path": self.temp_dir})
        
        # Parse the result
        result_data = json.loads(result)
        
        # Check that the result contains the expected data
        self.assertTrue(result_data["success"])
        self.assertIn("entries", result_data)
        
        # Check that the entries contain the test file and directory
        entry_names = [entry["name"] for entry in result_data["entries"]]
        self.assertIn("test_file.txt", entry_names)
        self.assertIn("test_dir", entry_names)
    
    def test_read_file_tool(self):
        """Test the read file tool."""
        # Create a client to test the tool
        client = MCPClient(self.integration.server_url)
        
        # Call the tool to read the test file
        result = client.call_tool("fs_read_file", {"path": self.test_file_path})
        
        # Parse the result
        result_data = json.loads(result)
        
        # Check that the result contains the expected data
        self.assertTrue(result_data["success"])
        self.assertIn("content", result_data)
        self.assertEqual(result_data["content"], "This is a test file for the Filesystem MCP Protocol integration.")
    
    def test_write_file_tool(self):
        """Test the write file tool."""
        # Create a client to test the tool
        client = MCPClient(self.integration.server_url)
        
        # Create a new file path
        new_file_path = os.path.join(self.temp_dir, "new_file.txt")
        
        # Call the tool to write to the new file
        result = client.call_tool("fs_write_file", {
            "path": new_file_path,
            "content": "This is a new file created by the Filesystem MCP Protocol integration."
        })
        
        # Parse the result
        result_data = json.loads(result)
        
        # Check that the result contains the expected data
        self.assertTrue(result_data["success"])
        
        # Check that the file was created with the expected content
        with open(new_file_path, "r") as f:
            content = f.read()
        
        self.assertEqual(content, "This is a new file created by the Filesystem MCP Protocol integration.")
    
    def test_analyze_text_tool(self):
        """Test the analyze text tool."""
        # Create a client to test the tool
        client = MCPClient(self.integration.server_url)
        
        # Call the tool to analyze the test file
        result = client.call_tool("fs_analyze_text", {"path": self.test_file_path})
        
        # Parse the result
        result_data = json.loads(result)
        
        # Check that the result contains the expected data
        self.assertTrue(result_data["success"])
        self.assertIn("analysis", result_data)
        
        # Check that the analysis contains the expected data
        analysis = result_data["analysis"]
        self.assertEqual(analysis["line_count"], 1)
        self.assertEqual(analysis["word_count"], 12)
        self.assertEqual(analysis["char_count"], 65)
        self.assertEqual(analysis["extension"], ".txt")

def main():
    """Run the tests."""
    unittest.main()

if __name__ == "__main__":
    main()
