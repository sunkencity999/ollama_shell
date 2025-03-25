"""
SSL Certificate Verification Utilities

This module provides utilities for managing SSL certificate verification
in the application, particularly for handling self-signed certificates
or certificate verification issues with external services like PostHog.
"""

import os
import requests
import urllib3
import logging
from functools import wraps
from typing import List, Optional, Callable, Any

# Configure logging
logger = logging.getLogger(__name__)

# List of domains for which SSL verification should be disabled
UNVERIFIED_DOMAINS = [
    "app.posthog.com",  # PostHog analytics service
    "eu.posthog.com",   # PostHog EU region
    "us.posthog.com",   # PostHog US region
    "posthog.com"       # PostHog main domain
]

def disable_ssl_warnings():
    """
    Disable SSL verification warnings from urllib3.
    Call this function once at application startup.
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    logger.info("SSL verification warnings have been disabled")

def is_ssl_verification_disabled() -> bool:
    """
    Check if SSL verification is disabled via environment variable.
    
    Returns:
        bool: True if SSL verification is disabled, False otherwise
    """
    return os.environ.get('DISABLE_SSL_VERIFICATION', '').lower() in ('true', '1', 'yes')

def should_skip_verification(url: str) -> bool:
    """
    Determine if SSL verification should be skipped for a given URL.
    
    Args:
        url: The URL to check
        
    Returns:
        bool: True if verification should be skipped, False otherwise
    """
    # If global SSL verification is disabled, skip verification for all URLs
    if is_ssl_verification_disabled():
        return True
        
    # Otherwise, check if the URL contains any of the unverified domains
    return any(domain in url for domain in UNVERIFIED_DOMAINS)

def patch_requests_session():
    """
    Patch the requests library to disable SSL verification for specific domains.
    This function should be called once at application startup.
    """
    original_get = requests.Session.get
    original_post = requests.Session.post
    original_put = requests.Session.put
    original_delete = requests.Session.delete
    
    @wraps(original_get)
    def patched_get(self, url, **kwargs):
        if should_skip_verification(url):
            kwargs['verify'] = False
            logger.debug(f"SSL verification disabled for GET request to {url}")
        return original_get(self, url, **kwargs)
    
    @wraps(original_post)
    def patched_post(self, url, **kwargs):
        if should_skip_verification(url):
            kwargs['verify'] = False
            logger.debug(f"SSL verification disabled for POST request to {url}")
        return original_post(self, url, **kwargs)
    
    @wraps(original_put)
    def patched_put(self, url, **kwargs):
        if should_skip_verification(url):
            kwargs['verify'] = False
            logger.debug(f"SSL verification disabled for PUT request to {url}")
        return original_put(self, url, **kwargs)
    
    @wraps(original_delete)
    def patched_delete(self, url, **kwargs):
        if should_skip_verification(url):
            kwargs['verify'] = False
            logger.debug(f"SSL verification disabled for DELETE request to {url}")
        return original_delete(self, url, **kwargs)
    
    # Apply the patches
    requests.Session.get = patched_get
    requests.Session.post = patched_post
    requests.Session.put = patched_put
    requests.Session.delete = patched_delete
    
    logger.info("Patched requests library to disable SSL verification for specific domains")

def add_unverified_domain(domain: str):
    """
    Add a domain to the list of domains for which SSL verification should be disabled.
    
    Args:
        domain: The domain to add (e.g., 'example.com')
    """
    if domain not in UNVERIFIED_DOMAINS:
        UNVERIFIED_DOMAINS.append(domain)
        logger.info(f"Added {domain} to unverified domains list")

def configure_ssl_verification(disable_all: bool = False, domains: Optional[List[str]] = None):
    """
    Configure SSL verification settings for the application.
    
    Args:
        disable_all: If True, disable SSL verification for all requests
        domains: List of additional domains to disable SSL verification for
    """
    # Disable SSL warnings to avoid console spam
    disable_ssl_warnings()
    
    # Set environment variable if disabling all SSL verification
    if disable_all:
        os.environ['DISABLE_SSL_VERIFICATION'] = 'true'
        logger.warning("SSL verification has been disabled for all requests. This is not recommended for production.")
    
    # Add additional domains if provided
    if domains:
        for domain in domains:
            add_unverified_domain(domain)
    
    # Patch the requests library
    patch_requests_session()
    
    logger.info("SSL verification configuration complete")

# Initialize the patch when the module is imported
patch_requests_session()
