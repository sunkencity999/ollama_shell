import asyncio
import logging
import os
from glama_mcp_integration import LocalWebIntegration

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_information_extraction():
    print("\n" + "="*80)
    print("TESTING IMPROVED INFORMATION EXTRACTION")
    print("="*80)
    
    lwi = LocalWebIntegration()
    
    # Test query
    query = "What are the health benefits of drinking green tea"
    print(f"\nQUERY: {query}")
    
    # 1. Generate optimized search query
    information_prompt = f"""
    You are a search engine optimization expert tasked with creating the most effective search query to find precise information about: {query}
    
    IMPORTANT GUIDELINES:
    1. Create a search query that will find CURRENT, FACTUAL, and SPECIFIC information about this topic
    2. DO NOT include site-specific operators (like site:) in your query
    3. DO include the current year (2025) for any time-sensitive topics to ensure up-to-date information
    4. Focus on terms that major authoritative websites would use in their content
    5. Include specific technical terms, proper nouns, and industry terminology when relevant
    6. Format the query for maximum relevance on major search engines
    7. Prioritize terms that would appear in titles and headings of relevant pages
    
    STRUCTURE YOUR QUERY WITH:
    - Primary topic/subject first
    - Specific attributes or qualifiers
    - Time frame indicators (2025, current, latest, etc.)
    - Content type indicators (guide, review, comparison, analysis, etc.)
    - Authority indicators (expert, official, research, etc.)
    
    Respond with ONLY the optimized query text, no additional text or explanations.
    """
    
    optimized_query = await lwi._query_local_model(information_prompt)
    print(f"\nOPTIMIZED SEARCH QUERY: {optimized_query}")
    
    # 2. Get relevant websites
    websites = [
        "https://www.healthline.com",
        "https://www.medicalnewstoday.com",
        "https://www.mayoclinic.org",
        "https://www.webmd.com",
        "https://www.nih.gov"
    ]
    print(f"\nSELECTED WEBSITES: {websites}")
    
    # 3. Gather information from websites
    print("\nGATHERING INFORMATION FROM WEBSITES...")
    result = await lwi.gather_information(websites, optimized_query)
    
    # 4. Display results
    print("\n" + "="*80)
    print("INFORMATION EXTRACTION RESULTS")
    print("="*80)
    print(f"\nSUCCESS: {result.get('success', False)}")
    print(f"\nCONTENT:\n{result.get('content', 'No content extracted')}")
    print("\n" + "="*80)
    
    # 5. Save the results to a file for inspection
    output_path = os.path.expanduser("~/Documents/green_tea_benefits.txt")
    with open(output_path, "w") as f:
        f.write(result.get('content', 'No content extracted'))
    print(f"\nResults saved to: {output_path}")

if __name__ == "__main__":
    asyncio.run(test_information_extraction())
