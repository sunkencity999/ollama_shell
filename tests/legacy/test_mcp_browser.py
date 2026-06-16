#!/usr/bin/env python3
"""
Test script for the MCP Browser implementation.
"""
import asyncio
import sys
from mcp_browser import MCPBrowser, start_mcp_server

async def test_mcp_browser():
    """Test the MCP Browser implementation."""
    print("Starting MCP server...")
    start_mcp_server()
    
    browser = MCPBrowser()
    
    # Test extract_content
    print("\nTesting extract_content...")
    result = await browser.extract_content("https://www.example.com")
    print(f"Success: {result.get('success', False)}")
    print(f"Content length: {len(result.get('content', ''))}")
    
    # Test extract_links
    print("\nTesting extract_links...")
    result = await browser.extract_links("https://www.example.com")
    print(f"Success: {result.get('success', False)}")
    print(f"Links found: {len(result.get('links', []))}")
    
    # Test take_screenshot
    print("\nTesting take_screenshot...")
    result = await browser.take_screenshot("https://www.example.com")
    print(f"Success: {result.get('success', False)}")
    print(f"Screenshot available: {'screenshot' in result}")
    
    # Test scroll_page
    print("\nTesting scroll_page...")
    result = await browser.scroll_page("https://www.example.com", "down")
    print(f"Success: {result.get('success', False)}")
    
    # Test extract_structured_content
    print("\nTesting extract_structured_content...")
    result = await browser.extract_structured_content("https://www.example.com")
    print(f"Success: {result.get('success', False)}")
    if result.get('success', False):
        print(f"Structured data keys: {', '.join(result.get('structured_data', {}).keys())}")
    
    # Test execute_javascript
    print("\nTesting execute_javascript...")
    result = await browser.execute_javascript("https://www.example.com", "return document.title;")
    print(f"Success: {result.get('success', False)}")
    print(f"JavaScript result: {result.get('result', '')}")
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    asyncio.run(test_mcp_browser())
