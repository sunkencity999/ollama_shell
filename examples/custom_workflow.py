#!/usr/bin/env python3
"""
Custom Workflow Script

This script demonstrates a custom workflow that:
1. Fetches headlines from CNN
2. Writes a short story based on the top headline
3. Saves the story to a file
"""

import asyncio
import os
from agentic_ollama import AgenticOllama
from web_browsing import WebBrowser

async def run_workflow():
    """
    Run the custom workflow.
    """
    print('\n===== Starting Custom Workflow =====')
    
    # Step 1: Fetch headlines from CNN
    print('Step 1: Fetching headlines from CNN...')
    ollama = AgenticOllama()
    headlines_result = await ollama.browse_web('Get headlines from https://cnn.com')
    
    # Extract the top headline
    headlines = headlines_result.get('artifacts', {}).get('headlines', [])
    top_headline = headlines[0] if headlines else 'Breaking News'
    print(f'Top headline: {top_headline}')
    
    # Step 2: Write a short story based on the headline
    print('\nStep 2: Writing short story based on headline...')
    story_prompt = f'Write a short creative story (300-500 words) inspired by this headline: "{top_headline}"'
    story_result_dict = await ollama._generate_completion(story_prompt)
    story_result = story_result_dict.get('result', '')
    print('Story generated successfully.')
    
    # Step 3: Save the story to a file
    print('\nStep 3: Saving story to file...')
    filename = '/Users/christopher.bradford/Documents/headline_story.txt'
    with open(filename, 'w') as f:
        f.write(f'# Story inspired by: {top_headline}\n\n{story_result}')
    print(f'Story saved to {filename}')
    
    print('\n===== Workflow Completed Successfully =====')
    
    # Preview the story
    print('\nPreview of the story:')
    with open(filename, 'r') as f:
        content = f.read()
        preview = content[:300] + '...' if len(content) > 300 else content
        print(preview)

if __name__ == '__main__':
    asyncio.run(run_workflow())
