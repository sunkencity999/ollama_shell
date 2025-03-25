#!/usr/bin/env python3
"""
MCP Browser Integration for Ollama Shell

This module provides integration with the browser-use-mcp-server for enhanced
web browsing capabilities in Ollama Shell, including JavaScript rendering,
interactive browsing, and advanced content extraction.
"""
import os
import json
import logging
import asyncio
import requests
import time
from typing import Dict, Any, List, Optional, Tuple, Union
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import SSL utilities
try:
    from ssl_utils import configure_ssl_verification, should_skip_verification
    SSL_UTILS_AVAILABLE = True
    # Configure SSL verification with PostHog domains
    configure_ssl_verification(disable_all=False)
except ImportError:
    SSL_UTILS_AVAILABLE = False
    logger.warning("SSL utilities not available. SSL certificate verification issues may occur.")

# Import Selenium WebDriver
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# Logging is already configured above

class MCPBrowser:
    """
    MCP Browser integration for Ollama Shell.
    
    This class provides methods to interact with a Selenium WebDriver
    for enhanced web browsing capabilities.
    """
    
    def __init__(self, server_url: str = "http://localhost:4444"):
        """
        Initialize the MCP Browser integration.
        
        Args:
            server_url: URL of the Selenium server
        """
        self.server_url = server_url
        self.driver = None
        self.check_server_status()
    
    def check_server_status(self) -> bool:
        """
        Check if the Selenium server is running.
        
        Returns:
            True if the server is running, False otherwise
        """
        try:
            # Apply SSL verification handling
            verify = True
            # Check if SSL utilities are available and if verification should be skipped
            if 'SSL_UTILS_AVAILABLE' in globals() and SSL_UTILS_AVAILABLE:
                if 'should_skip_verification' in globals() and should_skip_verification(self.server_url):
                    verify = False
                    logger.debug(f"SSL verification disabled for request to {self.server_url}")
            
            response = requests.get(f"{self.server_url}/status", timeout=5, verify=verify)
            if response.status_code == 200:
                logger.info("Selenium server is running")
                return True
            else:
                logger.warning(f"Selenium server returned status code {response.status_code}")
                return False
        except Exception as e:
            logger.warning(f"Selenium server is not running: {str(e)}")
            return False
    
    async def browse_url(self, url: str, action: str = "extract content") -> Dict[str, Any]:
        """
        Browse a URL using the Selenium WebDriver.
        
        Args:
            url: URL to browse
            action: Action to perform (e.g., "extract content", "take screenshot")
            
        Returns:
            Dict containing the browsing results
        """
        try:
            # Create a new remote WebDriver instance
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            # Connect to the remote Selenium server
            driver = webdriver.Remote(
                command_executor=self.server_url,
                options=options
            )
            
            # Set a page load timeout
            driver.set_page_load_timeout(30)
            
            # Navigate to the URL
            logger.info(f"Navigating to {url}")
            driver.get(url)
            
            # Wait for the page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Perform the requested action
            result = {}
            if action == "extract content" or action == "extract content and structure of the page":
                # Get the page source
                page_source = driver.page_source
                result = {
                    "success": True,
                    "content": page_source,
                    "url": url
                }
            elif action == "take screenshot":
                # Take a screenshot
                screenshot = driver.get_screenshot_as_base64()
                result = {
                    "success": True,
                    "screenshot": screenshot,
                    "url": url
                }
            else:
                result = {
                    "success": False,
                    "error": f"Unsupported action: {action}",
                    "url": url
                }
            
            # Close the browser
            driver.quit()
            
            return result
        except Exception as e:
            logger.error(f"Error browsing URL {url}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
            
    def browse_url_sync(self, url: str, action: str = "extract content") -> Dict[str, Any]:
        """
        Synchronous version of browse_url method for use in non-async contexts.
        Browse a URL using the Selenium WebDriver.
        
        Args:
            url: URL to browse
            action: Action to perform (e.g., "extract content", "take screenshot")
            
        Returns:
            Dict containing the browsing results
        """
        try:
            # Create a new remote WebDriver instance
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            # Connect to the remote Selenium server
            driver = webdriver.Remote(
                command_executor=self.server_url,
                options=options
            )
            
            # Set a page load timeout
            driver.set_page_load_timeout(30)
            
            # Navigate to the URL
            logger.info(f"Navigating to {url}")
            driver.get(url)
            
            # Wait for the page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Perform the requested action
            result = {}
            if action == "extract content" or action == "extract content and structure of the page":
                # Get the page source
                page_source = driver.page_source
                result = {
                    "success": True,
                    "content": page_source,
                    "url": url
                }
            elif action == "take screenshot":
                # Take a screenshot
                screenshot = driver.get_screenshot_as_base64()
                result = {
                    "success": True,
                    "screenshot": screenshot,
                    "url": url
                }
            else:
                result = {
                    "success": False,
                    "error": f"Unsupported action: {action}",
                    "url": url
                }
            
            # Close the browser
            driver.quit()
            
            return result
        except Exception as e:
            logger.error(f"Error browsing URL {url}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
    
    async def extract_content(self, url: str) -> Dict[str, Any]:
        """
        Extract content from a URL using the Selenium WebDriver.
        
        Args:
            url: URL to extract content from
            
        Returns:
            Dict containing the extracted content
        """
        return await self.browse_url(url, "extract content")
    
    async def extract_links(self, url: str) -> Dict[str, Any]:
        """
        Extract links from a URL using the Selenium WebDriver.
        
        Args:
            url: URL to extract links from
            
        Returns:
            Dict containing the extracted links
        """
        try:
            # Create a new remote WebDriver instance
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            # Connect to the remote Selenium server
            driver = webdriver.Remote(
                command_executor=self.server_url,
                options=options
            )
            
            # Set a page load timeout
            driver.set_page_load_timeout(30)
            
            # Navigate to the URL
            logger.info(f"Navigating to {url} to extract links")
            driver.get(url)
            
            # Wait for the page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Find all links on the page
            links = driver.find_elements(By.TAG_NAME, "a")
            link_data = []
            
            for link in links:
                try:
                    href = link.get_attribute("href")
                    text = link.text.strip()
                    if href and text:
                        link_data.append({
                            "href": href,
                            "text": text
                        })
                except Exception as e:
                    logger.warning(f"Error extracting link data: {str(e)}")
            
            # Close the browser
            driver.quit()
            
            return {
                "success": True,
                "links": link_data,
                "url": url
            }
        except Exception as e:
            logger.error(f"Error extracting links from URL {url}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
    
    async def take_screenshot(self, url: str) -> Dict[str, Any]:
        """
        Take a screenshot of a webpage using the Selenium WebDriver.
        
        Args:
            url: URL to take a screenshot of
            
        Returns:
            Dict containing the screenshot data (base64 encoded)
        """
        return await self.browse_url(url, "take screenshot")
    
    async def fill_form(self, url: str, form_data: Dict[str, str]) -> Dict[str, Any]:
        """
        Fill a form on a webpage using the Selenium WebDriver.
        
        Args:
            url: URL containing the form
            form_data: Dict mapping form field selectors to values
            
        Returns:
            Dict containing the form submission results
        """
        try:
            # Create a new remote WebDriver instance
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            # Connect to the remote Selenium server
            driver = webdriver.Remote(
                command_executor=self.server_url,
                options=options
            )
            
            # Set a page load timeout
            driver.set_page_load_timeout(30)
            
            # Navigate to the URL
            logger.info(f"Navigating to {url} to fill form")
            driver.get(url)
            
            # Wait for the page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Fill the form fields
            for selector, value in form_data.items():
                try:
                    # Find the form field
                    field = driver.find_element(By.CSS_SELECTOR, selector)
                    
                    # Clear the field if it's an input or textarea
                    if field.tag_name.lower() in ["input", "textarea"]:
                        field.clear()
                    
                    # Fill the field with the value
                    field.send_keys(value)
                except Exception as e:
                    logger.warning(f"Error filling form field {selector}: {str(e)}")
            
            # Get the updated page content
            page_source = driver.page_source
            
            # Close the browser
            driver.quit()
            
            return {
                "success": True,
                "content": page_source,
                "url": url
            }
        except Exception as e:
            logger.error(f"Error filling form on URL {url}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
    
    async def click_element(self, url: str, selector: str) -> Dict[str, Any]:
        """
        Click an element on a webpage using the Selenium WebDriver.
        
        Args:
            url: URL containing the element
            selector: CSS selector for the element to click
            
        Returns:
            Dict containing the click results
        """
        try:
            # Create a new remote WebDriver instance
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            # Connect to the remote Selenium server
            driver = webdriver.Remote(
                command_executor=self.server_url,
                options=options
            )
            
            # Set a page load timeout
            driver.set_page_load_timeout(30)
            
            # Navigate to the URL
            logger.info(f"Navigating to {url} to click element")
            driver.get(url)
            
            # Wait for the page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Wait for the element to be clickable
            element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            
            # Click the element
            element.click()
            
            # Wait for any page changes to complete
            time.sleep(2)
            
            # Get the updated page content
            page_source = driver.page_source
            current_url = driver.current_url
            
            # Close the browser
            driver.quit()
            
            return {
                "success": True,
                "content": page_source,
                "url": current_url  # Return the current URL which may have changed after clicking
            }
        except Exception as e:
            logger.error(f"Error clicking element on URL {url}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
    
    async def scroll_page(self, url: str, direction: str = "down") -> Dict[str, Any]:
        """
        Scroll a webpage using the Selenium WebDriver.
        
        Args:
            url: URL to scroll
            direction: Direction to scroll (up, down, left, right)
            
        Returns:
            Dict containing the scroll results
        """
        try:
            # Create a new remote WebDriver instance
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            # Connect to the remote Selenium server
            driver = webdriver.Remote(
                command_executor=self.server_url,
                options=options
            )
            
            # Set a page load timeout
            driver.set_page_load_timeout(30)
            
            # Navigate to the URL
            logger.info(f"Navigating to {url} to scroll page")
            driver.get(url)
            
            # Wait for the page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Determine the scroll direction and amount
            scroll_script = ""
            if direction.lower() == "down":
                scroll_script = "window.scrollBy(0, window.innerHeight);"
            elif direction.lower() == "up":
                scroll_script = "window.scrollBy(0, -window.innerHeight);"
            elif direction.lower() == "right":
                scroll_script = "window.scrollBy(window.innerWidth, 0);"
            elif direction.lower() == "left":
                scroll_script = "window.scrollBy(-window.innerWidth, 0);"
            
            # Execute the scroll script
            driver.execute_script(scroll_script)
            
            # Wait for a moment to allow any dynamic content to load
            time.sleep(1)
            
            # Get the updated page content
            page_source = driver.page_source
            
            # Close the browser
            driver.quit()
            
            return {
                "success": True,
                "content": page_source,
                "url": url
            }
        except Exception as e:
            logger.error(f"Error scrolling page on URL {url}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
    
    async def extract_structured_content(self, url: str) -> Dict[str, Any]:
        """
        Extract structured content from a URL using the Selenium WebDriver.
        
        Args:
            url: URL to extract structured content from
            
        Returns:
            Dict containing the structured content of the page
        """
        try:
            # Create a new remote WebDriver instance
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            # Connect to the remote Selenium server
            driver = webdriver.Remote(
                command_executor=self.server_url,
                options=options
            )
            
            # Set a page load timeout
            driver.set_page_load_timeout(30)
            
            # Navigate to the URL
            logger.info(f"Navigating to {url} to extract structured content")
            driver.get(url)
            
            # Wait for the page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Extract various types of structured content
            structured_data = {
                "headings": self._extract_headings(driver),
                "paragraphs": self._extract_paragraphs(driver),
                "links": self._extract_links_from_html(driver),
                "images": self._extract_images(driver),
                "tables": self._extract_tables(driver),
                "metadata": self._extract_metadata(driver),
                "title": driver.title or "",
                "raw_text": driver.find_element(By.TAG_NAME, "body").text
            }
            
            # Get the page content
            page_source = driver.page_source
            logger.info(f"Extracted page source: {len(page_source)} bytes")
            
            # Close the browser
            driver.quit()
            
            return {
                "success": True,
                "content": structured_data,  # Return the structured data in the content field
                "html_content": page_source,  # Include the HTML content in the html_content field
                "structured_data": structured_data,
                "url": url
            }
        except Exception as e:
            logger.error(f"Error extracting structured content from URL {url}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
    
    async def execute_javascript(self, url: str, script: str) -> Dict[str, Any]:
        """
        Execute JavaScript on a URL using the Selenium WebDriver.
        
        Args:
            url: URL to execute JavaScript on
            script: JavaScript code to execute
            
        Returns:
            Dict containing the result of the JavaScript execution
        """
        try:
            # Create a new remote WebDriver instance
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            # Connect to the remote Selenium server
            driver = webdriver.Remote(
                command_executor=self.server_url,
                options=options
            )
            
            # Set a page load timeout
            driver.set_page_load_timeout(30)
            
            # Navigate to the URL
            logger.info(f"Navigating to {url} to execute JavaScript")
            driver.get(url)
            
            # Wait for the page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Execute the JavaScript code
            result = driver.execute_script(script)
            
            # Convert the result to a string if it's not serializable
            if result is not None and not isinstance(result, (dict, list, str, int, float, bool)):
                result = str(result)
            
            # Get the updated page content
            page_source = driver.page_source
            
            # Close the browser
            driver.quit()
            
            return {
                "success": True,
                "content": page_source,
                "result": result,
                "url": url
            }
        except Exception as e:
            logger.error(f"Error executing JavaScript on URL {url}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
    
    # Helper methods for extracting structured content
    def _extract_headings(self, driver) -> List[Dict[str, str]]:
        """Extract headings from a webpage."""
        headings = []
        for level in range(1, 7):
            elements = driver.find_elements(By.CSS_SELECTOR, f"h{level}")
            for element in elements:
                headings.append({
                    "level": level,
                    "text": element.text.strip()
                })
        return headings
    
    def _extract_paragraphs(self, driver) -> List[str]:
        """Extract paragraphs from a webpage."""
        paragraphs = []
        elements = driver.find_elements(By.TAG_NAME, "p")
        for element in elements:
            text = element.text.strip()
            if text:  # Only include non-empty paragraphs
                paragraphs.append(text)
        return paragraphs
    
    def _extract_links_from_html(self, driver) -> List[Dict[str, str]]:
        """Extract links from a webpage."""
        links = []
        elements = driver.find_elements(By.TAG_NAME, "a")
        for element in elements:
            href = element.get_attribute("href")
            text = element.text.strip()
            if href and text:  # Only include links with both href and text
                links.append({
                    "href": href,
                    "text": text
                })
        return links
    
    def _extract_images(self, driver) -> List[Dict[str, str]]:
        """Extract images from a webpage."""
        images = []
        elements = driver.find_elements(By.TAG_NAME, "img")
        for element in elements:
            src = element.get_attribute("src")
            alt = element.get_attribute("alt") or ""
            if src:  # Only include images with src attribute
                images.append({
                    "src": src,
                    "alt": alt
                })
        return images
    
    def _extract_tables(self, driver) -> List[Dict[str, Any]]:
        """Extract tables from a webpage."""
        tables = []
        table_elements = driver.find_elements(By.TAG_NAME, "table")
        
        for table_idx, table in enumerate(table_elements):
            headers = []
            header_elements = table.find_elements(By.TAG_NAME, "th")
            for header in header_elements:
                headers.append(header.text.strip())
            
            rows = []
            row_elements = table.find_elements(By.TAG_NAME, "tr")
            for row in row_elements:
                cell_elements = row.find_elements(By.TAG_NAME, "td")
                if cell_elements:  # Skip header rows
                    row_data = [cell.text.strip() for cell in cell_elements]
                    rows.append(row_data)
            
            tables.append({
                "id": table_idx,
                "headers": headers,
                "rows": rows
            })
        
        return tables
    
    def _extract_metadata(self, driver) -> Dict[str, str]:
        """Extract metadata from a webpage."""
        metadata = {}
        
        # Extract title
        try:
            title = driver.title
            if title:
                metadata["title"] = title
        except:
            pass
        
        # Extract meta tags
        meta_elements = driver.find_elements(By.TAG_NAME, "meta")
        for element in meta_elements:
            name = element.get_attribute("name")
            content = element.get_attribute("content")
            if name and content:
                metadata[name] = content
            
            # Also check for property attribute (Open Graph tags)
            prop = element.get_attribute("property")
            if prop and content:
                metadata[prop] = content
        
        return metadata

# Helper function to start the MCP server using Docker
def start_mcp_server() -> bool:
    """
    Start the MCP server using Docker.
    
    Returns:
        True if the server was started successfully, False otherwise
    """
    try:
        # Check if Docker is installed
        import subprocess
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error("Docker is not installed or not in PATH")
            return False
        
        # Check if the MCP server is already running
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=mcp-browser", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )
        
        if "mcp-browser" in result.stdout:
            logger.info("MCP browser server is already running")
            return True
        
        # Start the MCP server
        logger.info("Starting MCP browser server...")
        result = subprocess.run([
            "docker", "run", "-d",
            "--name", "mcp-browser",
            "-p", "4444:4444",  # Selenium port
            "-p", "7900:7900",  # noVNC port
            "--shm-size=2g",
            "seleniarm/standalone-chromium:latest"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Failed to start MCP browser server: {result.stderr}")
            return False
        
        logger.info("MCP browser server started successfully")
        return True
    except Exception as e:
        logger.error(f"Error starting MCP browser server: {str(e)}")
        return False

# Helper function to stop the MCP server
def stop_mcp_server() -> bool:
    """
    Stop the MCP server.
    
    Returns:
        True if the server was stopped successfully, False otherwise
    """
    try:
        import subprocess
        result = subprocess.run(
            ["docker", "stop", "mcp-browser"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Failed to stop MCP browser server: {result.stderr}")
            return False
        
        # Remove the container
        result = subprocess.run(
            ["docker", "rm", "mcp-browser"],
            capture_output=True,
            text=True
        )
        
        logger.info("MCP browser server stopped successfully")
        return True
    except Exception as e:
        logger.error(f"Error stopping MCP browser server: {str(e)}")
        return False

# Test the module if run directly
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "start":
            start_mcp_server()
        elif sys.argv[1] == "stop":
            stop_mcp_server()
        elif sys.argv[1] == "test":
            async def test_browser():
                try:
                    browser = MCPBrowser()
                    print("Testing browser with a simple URL...")
                    result = await browser.extract_content("https://example.com")
                    print(json.dumps(result, indent=2))
                except Exception as e:
                    print(f"Error during browser test: {str(e)}")
            
            asyncio.run(test_browser())
    else:
        print("Usage: python mcp_browser.py [start|stop|test]")
