#!/usr/bin/env python3
"""
Test script to verify filename extraction for quotes at the end of sentences.
"""

import re
import logging
from agentic_assistant_enhanced import EnhancedAgenticAssistant

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_filename_extraction():
    """Test the filename extraction functionality for quotes at the end of sentences."""
    print("\n===== Testing Filename Extraction for Quotes =====")
    
    # Create an instance of the enhanced assistant
    assistant = EnhancedAgenticAssistant()
    
    # Test cases for filename extraction
    test_cases = [
        # Filenames in quotes at the end of sentences
        "Please analyze the headlines of CNN.com, save them in a file, and then create a report about the broad concerns of humanity based on the content of those headlines named \"CNNReport\".",
        "Research quantum computing and write a summary named \"QuantumReport\"",
        "Find information about climate change and create a document named \"ClimateChange\".",
        "Write a story about dragons and save it as a file named \"DragonTale\".",
        "Analyze the stock market trends and compile a report named \"StockAnalysis\".",
        "Look up recent space discoveries and create a summary named \"SpaceNews\".",
        "Research the history of artificial intelligence and write an article named \"AIHistory\".",
        "Find information about renewable energy sources and create a document named \"RenewableEnergy\".",
        "Analyze the latest political news and compile a report named \"PoliticalAnalysis\".",
        "Research the impact of social media on society and write an essay named \"SocialMediaImpact\"."
    ]
    
    # Test each case
    for i, task in enumerate(test_cases):
        filename = assistant._extract_filename(task)
        print(f"Test {i+1}: '{task}'")
        print(f"  Extracted filename: '{filename}'")
        print()

def main():
    """Main function to run all tests."""
    print("===== Testing Filename Extraction for Quotes =====")
    
    # Test filename extraction
    test_filename_extraction()
    
    print("\n===== All Tests Completed =====")

if __name__ == "__main__":
    main()
