"""
JavaScript content extraction helpers for news sites.
This module provides JavaScript execution methods to enhance content extraction
from news sites by bypassing paywalls and handling dynamic content.
"""

import time
import logging
from typing import Dict, Any

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

logger = logging.getLogger('js_content_extraction')

def extract_with_enhanced_javascript(url: str, domain: str, server_url: str) -> Dict[str, Any]:
    """
    Extract content from a news site using enhanced JavaScript execution techniques.
    This method uses Selenium WebDriver to execute JavaScript that helps bypass paywalls
    and extract content from dynamically loaded pages.
    
    Args:
        url: URL of the news site to extract content from
        domain: Domain of the news site (e.g., 'cnn.com')
        server_url: URL of the Selenium server
        
    Returns:
        Dict containing the extraction results
    """
    driver = None
    try:
        # Create a new remote WebDriver instance with optimized settings
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-notifications')
        
        # Use a more realistic user agent
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
        
        # Performance optimizations
        prefs = {
            "profile.managed_default_content_settings.images": 2,  # Disable images
            "profile.default_content_setting_values.notifications": 2,  # Disable notifications
            "profile.managed_default_content_settings.stylesheets": 2,  # Disable CSS
            "profile.managed_default_content_settings.cookies": 1,  # Allow cookies
            "profile.managed_default_content_settings.javascript": 1,  # Allow JavaScript
            "profile.managed_default_content_settings.plugins": 2,  # Disable plugins
            "profile.managed_default_content_settings.popups": 2,  # Disable popups
            "profile.managed_default_content_settings.geolocation": 2,  # Disable geolocation
            "profile.managed_default_content_settings.media_stream": 2,  # Disable media stream
        }
        options.add_experimental_option("prefs", prefs)
        
        # Connect to the remote Selenium server
        logger.info(f"Connecting to Selenium server at {server_url}")
        driver = webdriver.Remote(
            command_executor=server_url,
            options=options
        )
        
        # Set reasonable timeouts
        driver.set_page_load_timeout(30)  # Reduced from 45 to avoid long hangs
        driver.set_script_timeout(20)  # Add script timeout
        
        try:
            # Navigate to the URL with a more resilient approach
            logger.info(f"Navigating to {url} with enhanced JavaScript execution")
            driver.get(url)
            
            # Wait for the page to load with a shorter timeout
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                logger.info(f"Page body loaded for {url}")
            except TimeoutException:
                logger.warning(f"Timeout waiting for body element on {url}, but continuing anyway")
            
            # Get initial page source even before executing scripts
            initial_source = driver.page_source
            initial_title = driver.title if hasattr(driver, 'title') else ""
            
            # Execute site-specific JavaScript to help with content extraction
            try:
                if 'cnn.com' in domain:
                    logger.info(f"Executing CNN-specific scripts for {url}")
                    execute_cnn_scripts(driver)
                elif 'wsj.com' in domain:
                    logger.info(f"Executing WSJ-specific scripts for {url}")
                    execute_wsj_scripts(driver)
                elif 'washingtonpost.com' in domain:
                    logger.info(f"Executing Washington Post-specific scripts for {url}")
                    execute_wapo_scripts(driver)
                elif 'reuters.com' in domain:
                    logger.info(f"Executing Reuters-specific scripts for {url}")
                    execute_reuters_scripts(driver)
                elif 'theguardian.com' in domain:
                    logger.info(f"Executing Guardian-specific scripts for {url}")
                    execute_guardian_scripts(driver)
                elif 'bbc.com' in domain or 'bbc.co.uk' in domain:
                    logger.info(f"Executing BBC-specific scripts for {url}")
                    execute_bbc_scripts(driver)
                else:
                    # For other news sites, try generic paywall bypass techniques
                    logger.info(f"Executing generic paywall bypass for {domain}")
                    execute_generic_paywall_bypass(driver)
                
                # Wait briefly for dynamic content to load (reduced wait time)
                logger.info(f"Waiting for dynamic content to load on {url}")
                time.sleep(2)
                
                # Scroll down to load lazy-loaded content
                logger.info(f"Scrolling for content on {url}")
                scroll_for_content(driver)
                
                # Get the page source after JavaScript execution
                logger.info(f"Extracting page source from {url}")
                page_source = driver.page_source
                
                # Get page title for additional context
                try:
                    title = driver.title
                except:
                    title = initial_title
            except Exception as script_error:
                logger.warning(f"Error during script execution for {url}: {str(script_error)}")
                # Use the initial source if script execution fails
                page_source = initial_source
                title = initial_title
            
            # Close the browser
            logger.info(f"Closing browser session for {url}")
            driver.quit()
            driver = None
            
            return {
                "success": True,
                "content": page_source,
                "url": url,
                "title": title
            }
            
        except TimeoutException as te:
            logger.warning(f"Page load timeout for {url}: {str(te)}")
            # Try to get whatever content we can
            try:
                partial_source = driver.page_source if driver else ""
                partial_title = driver.title if driver and hasattr(driver, 'title') else ""
                if driver:
                    driver.quit()
                    driver = None
                
                if partial_source and len(partial_source) > 1000:  # If we have some meaningful content
                    return {
                        "success": True,  # Mark as success if we got some content
                        "content": partial_source,
                        "url": url,
                        "title": partial_title,
                        "partial": True  # Flag that this is partial content
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Page load timeout: {str(te)}",
                        "url": url
                    }
            except Exception as inner_e:
                logger.error(f"Error recovering from timeout for {url}: {str(inner_e)}")
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = None
                return {
                    "success": False,
                    "error": f"Page load timeout and recovery failed: {str(te)}, {str(inner_e)}",
                    "url": url
                }
        except Exception as e:
            logger.error(f"Navigation error for {url}: {str(e)}")
            if driver:
                try:
                    driver.quit()
                except:
                    pass
                driver = None
            return {
                "success": False,
                "error": f"Navigation error: {str(e)}",
                "url": url
            }
    except WebDriverException as e:
        logger.error(f"WebDriver error in enhanced JavaScript extraction for {url}: {str(e)}")
        if driver:
            try:
                driver.quit()
            except:
                pass
        return {
            "success": False,
            "error": f"WebDriver error: {str(e)}",
            "url": url
        }
    except Exception as e:
        logger.error(f"Error in enhanced JavaScript extraction for {url}: {str(e)}")
        if driver:
            try:
                driver.quit()
            except:
                pass
        return {
            "success": False,
            "error": str(e),
            "url": url
        }

def scroll_for_content(driver):
    """
    Scroll the page to load lazy-loaded content.
    
    Args:
        driver: Selenium WebDriver instance
    """
    try:
        # Get initial page height
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        # Scroll down in increments
        for _ in range(5):  # Scroll 5 times
            # Scroll down to the bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Wait for new content to load
            time.sleep(1)
            
            # Calculate new scroll height and compare with last scroll height
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break  # No more new content
            last_height = new_height
    except Exception as e:
        logger.warning(f"Error scrolling for content: {str(e)}")

def execute_cnn_scripts(driver):
    """
    Execute CNN-specific JavaScript to help with content extraction.
    
    Args:
        driver: Selenium WebDriver instance
    """
    try:
        # Wait for article content to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".article__content, .article-body, .zn-body__paragraph"))
        )
        
        # Disable CNN's ad blocker detection
        driver.execute_script("""
            if (window.NREUM) { window.NREUM = undefined; }
            if (window.CNN && window.CNN.contentModel) { window.CNN.contentModel.adModel = undefined; }
        """)
        
        # Expand any collapsed content sections
        driver.execute_script("""
            document.querySelectorAll('.el__leafmedia--sourced-paragraph').forEach(function(el) {
                el.style.display = 'block';
            });
        """)
    except Exception as e:
        logger.warning(f"Error executing CNN scripts: {str(e)}")

def execute_wsj_scripts(driver):
    """
    Execute WSJ-specific JavaScript to help with content extraction.
    
    Args:
        driver: Selenium WebDriver instance
    """
    try:
        # Try to bypass paywall by removing overlay elements
        driver.execute_script("""
            // Remove paywall and overlay elements
            document.querySelectorAll('[class*="paywall"], [class*="overlay"], [id*="paywall"], [id*="overlay"]').forEach(function(el) {
                el.remove();
            });
            
            // Enable scrolling on body
            document.body.style.overflow = 'auto';
            document.body.style.position = 'static';
            
            // Make article content visible
            document.querySelectorAll('[class*="article-content"], [class*="article__body"]').forEach(function(el) {
                el.style.display = 'block';
            });
        """)
    except Exception as e:
        logger.warning(f"Error executing WSJ scripts: {str(e)}")

def execute_wapo_scripts(driver):
    """
    Execute Washington Post-specific JavaScript to help with content extraction.
    
    Args:
        driver: Selenium WebDriver instance
    """
    try:
        # Try to bypass paywall by removing overlay elements
        driver.execute_script("""
            // Remove paywall and overlay elements
            document.querySelectorAll('[class*="paywall"], [class*="overlay"], [id*="paywall"], [id*="overlay"]').forEach(function(el) {
                el.remove();
            });
            
            // Enable scrolling on body
            document.body.style.overflow = 'auto';
            document.body.style.position = 'static';
            
            // Make article content visible
            document.querySelectorAll('[data-qa="article-body"], [class*="article-body"]').forEach(function(el) {
                el.style.display = 'block';
            });
        """)
    except Exception as e:
        logger.warning(f"Error executing Washington Post scripts: {str(e)}")

def execute_reuters_scripts(driver):
    """
    Execute Reuters-specific JavaScript to help with content extraction.
    
    Args:
        driver: Selenium WebDriver instance
    """
    try:
        # Try to wait for article content to load, but continue if timeout
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".article-body, [class*='article-body'], [class*='ArticleBody'], .article, .story-content"))
            )
        except TimeoutException:
            logger.warning("Timeout waiting for Reuters article content, continuing anyway")
        
        # Execute a more comprehensive script to handle Reuters content
        driver.execute_script("""
        (function() {
            // Handle various paywall and overlay elements
            const elementsToRemove = [
                '[class*="paywall"]', '[class*="overlay"]', '[id*="paywall"]', '[id*="overlay"]',
                '.tp-modal', '.tp-backdrop', '.tp-container', '.registration-prompt',
                '.message-container', '[data-testid="paywall-container"]',
                '.ad-slot', '.ad-container', '#onetrust-consent-sdk',
                '.cookie-banner', '.newsletter-signup', '.trust-badge',
                '.inline-newsletter', '.inline-prompt'
            ];
            
            // Remove all matching elements
            elementsToRemove.forEach(selector => {
                document.querySelectorAll(selector).forEach(el => {
                    if (el && el.parentNode) {
                        el.parentNode.removeChild(el);
                    }
                });
            });
            
            // Ensure body content is visible
            const contentSelectors = [
                '[class*="article-body"]', '[class*="ArticleBody"]', '.article', '.story-content',
                '.article-text', '.body-content', '.main-content', '.content-container'
            ];
            
            contentSelectors.forEach(selector => {
                document.querySelectorAll(selector).forEach(el => {
                    el.style.display = 'block';
                    el.style.visibility = 'visible';
                    el.style.opacity = '1';
                    el.style.maxHeight = 'none';
                    el.style.overflow = 'visible';
                });
            });
            
            // Enable scrolling
            document.documentElement.style.overflow = 'auto';
            document.body.style.overflow = 'auto';
            
            // Remove blur effects
            document.querySelectorAll('*[style*="blur"]').forEach(el => {
                el.style.filter = 'none';
                el.style.webkitFilter = 'none';
            });
        })();
        """)
        
        logger.info("Successfully executed Reuters scripts")
    except Exception as e:
        logger.warning(f"Error executing Reuters scripts: {str(e)}")

def execute_guardian_scripts(driver):
    """
    Execute Guardian-specific JavaScript to help with content extraction.
    
    Args:
        driver: Selenium WebDriver instance
    """
    try:
        # Wait for article content to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".article-body, .content__article-body, [itemprop='articleBody']"))
        )
        
        # Remove cookie banners and subscription prompts
        driver.execute_script("""
            // Remove cookie banners and subscription prompts
            document.querySelectorAll('[class*="cookie"], [class*="subscribe"], [class*="banner"], [class*="message"]').forEach(function(el) {
                el.remove();
            });
            
            // Ensure article content is visible
            document.querySelectorAll('.article-body, .content__article-body, [itemprop="articleBody"]').forEach(function(el) {
                el.style.display = 'block';
            });
        """)
    except Exception as e:
        logger.warning(f"Error executing Guardian scripts: {str(e)}")

def execute_bbc_scripts(driver):
    """
    Execute BBC-specific JavaScript to help with content extraction.
    
    Args:
        driver: Selenium WebDriver instance
    """
    try:
        # Wait for article content to load
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".ssrcss-pv1rh6-ArticleWrapper, article, .story-body, .story-body__inner"))
            )
        except TimeoutException:
            logger.warning("Timeout waiting for BBC article content, continuing anyway")
        
        # Execute script to optimize BBC content extraction
        driver.execute_script("""
        (function() {
            // Remove cookie banners, ads, and other distractions
            const elementsToRemove = [
                '#bbccookies', '.orb-banner', '.bbccom_slot', '.bbccom_advert',
                '.tp-modal', '.tp-backdrop', '.tp-container',
                '.sign-in-banner', '.sign-in-prompt', '.nw-c-sign-in-banner',
                '.media-player__guidance--over-16', '.media-player__guidance--over-18',
                '.media-player__guidance--guidance-message', '.media-player__guidance',
                '.gs-u-display-none', '.nw-c-toaster', '.nw-c-top-banner',
                '.ssrcss-1jdn9xz-ConsentBanner', '.ssrcss-1jdn9xz-ConsentBanner-ConsentBanner',
                '.ssrcss-1jdn9xz-ConsentBanner', '.ssrcss-1pvh0x6-Banner',
                '.ssrcss-1pvh0x6-Banner-Banner', '.ssrcss-1pvh0x6-Banner'
            ];
            
            // Remove all matching elements
            elementsToRemove.forEach(selector => {
                document.querySelectorAll(selector).forEach(el => {
                    if (el && el.parentNode) {
                        el.parentNode.removeChild(el);
                    }
                });
            });
            
            // Ensure article content is visible
            const contentSelectors = [
                '.ssrcss-pv1rh6-ArticleWrapper', 'article', '.story-body', '.story-body__inner',
                '.ssrcss-1q0x1qg-Wrapper', '.ssrcss-1q0x1qg-Wrapper-Wrapper', '.ssrcss-1q0x1qg-Wrapper',
                '.ssrcss-1ocoo3l-Wrap', '.ssrcss-1ocoo3l-Wrap-Wrap', '.ssrcss-1ocoo3l-Wrap',
                '.gel-layout__item', '.gel-layout', '.bbc-news-vj-wrapper',
                '.bbc-news-vj-wrapper-wrapper', '.bbc-news-vj-wrapper'
            ];
            
            contentSelectors.forEach(selector => {
                document.querySelectorAll(selector).forEach(el => {
                    el.style.display = 'block';
                    el.style.visibility = 'visible';
                    el.style.opacity = '1';
                    el.style.maxHeight = 'none';
                    el.style.overflow = 'visible';
                });
            });
            
            // Expand any collapsed content
            document.querySelectorAll('[data-component="text-block"]').forEach(el => {
                el.style.display = 'block';
                el.style.maxHeight = 'none';
            });
            
            // Show any hidden images
            document.querySelectorAll('img[hidden], img.lazyload').forEach(img => {
                img.hidden = false;
                if (img.dataset.src) {
                    img.src = img.dataset.src;
                }
                img.style.display = 'block';
                img.style.visibility = 'visible';
            });
        })();
        """)
        
        logger.info("Successfully executed BBC scripts")
    except Exception as e:
        logger.warning(f"Error executing BBC scripts: {str(e)}")

def execute_generic_paywall_bypass(driver):
    """
    Execute generic JavaScript to help bypass paywalls and extract content from news sites.
    This function applies common techniques that work across many news sites.
    
    Args:
        driver: Selenium WebDriver instance
    """
    try:
        # General approach for bypassing paywalls and removing overlays
        driver.execute_script("""
            // Common selectors for paywalls and overlays
            const paywall_selectors = [
                // Paywall and overlay selectors
                '[class*="paywall"]', '[id*="paywall"]',
                '[class*="overlay"]', '[id*="overlay"]',
                '[class*="subscribe"]', '[id*="subscribe"]',
                '[class*="subscription"]', '[id*="subscription"]',
                '[class*="premium"]', '[id*="premium"]',
                '[class*="register"]', '[id*="register"]',
                '[class*="signup"]', '[id*="signup"]',
                '[class*="sign-up"]', '[id*="sign-up"]',
                '[class*="login"]', '[id*="login"]',
                '[class*="barrier"]', '[id*="barrier"]',
                '[class*="modal"]', '[id*="modal"]',
                '[class*="popup"]', '[id*="popup"]',
                '[class*="banner"]', '[id*="banner"]',
                '[class*="ad-"]', '[id*="ad-"]',
                '[class*="cookie"]', '[id*="cookie"]',
                // Common class names for modals and overlays
                '.modal', '.overlay', '.paywall', '.subscribe',
                '.subscription', '.premium', '.register', '.signup',
                '.sign-up', '.login', '.barrier', '.popup', '.banner'
            ];
            
            // Remove all elements matching the selectors
            paywall_selectors.forEach(selector => {
                document.querySelectorAll(selector).forEach(el => {
                    el.remove();
                });
            });
            
            // Enable scrolling and fix body styles
            document.body.style.overflow = 'auto';
            document.body.style.position = 'static';
            document.body.style.height = 'auto';
            document.documentElement.style.overflow = 'auto';
            document.documentElement.style.position = 'static';
            document.documentElement.style.height = 'auto';
            
            // Common article content selectors
            const content_selectors = [
                '[class*="article-body"]', '[id*="article-body"]',
                '[class*="article-content"]', '[id*="article-content"]',
                '[class*="story-body"]', '[id*="story-body"]',
                '[class*="story-content"]', '[id*="story-content"]',
                '[class*="content-body"]', '[id*="content-body"]',
                '[class*="post-body"]', '[id*="post-body"]',
                '[class*="entry-content"]', '[id*="entry-content"]',
                '[itemprop="articleBody"]', '[property="articleBody"]',
                // Common class names for article content
                '.article', '.article-body', '.article-content',
                '.story', '.story-body', '.story-content',
                '.post', '.post-body', '.post-content',
                '.entry', '.entry-content', '.content'
            ];
            
            // Make all content elements visible
            content_selectors.forEach(selector => {
                document.querySelectorAll(selector).forEach(el => {
                    el.style.display = 'block';
                    el.style.visibility = 'visible';
                    el.style.opacity = '1';
                });
            });
            
            // Remove blur effects that might be hiding content
            document.querySelectorAll('*').forEach(el => {
                if (getComputedStyle(el).filter.includes('blur')) {
                    el.style.filter = 'none';
                }
            });
        """)
        
        # Wait a bit for the DOM changes to take effect
        time.sleep(1)
        
    except Exception as e:
        logger.warning(f"Error executing generic paywall bypass scripts: {str(e)}")
