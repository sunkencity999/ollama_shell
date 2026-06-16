import asyncio
import logging
from glama_mcp_integration import LocalWebIntegration

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    print("\n" + "="*80)
    print("VERIFYING WEB SEARCH IMPROVEMENTS")
    print("="*80)
    
    lwi = LocalWebIntegration()
    
    # Test the improved search query generation
    query = "What are the best fishing spots in California"
    
    # Generate optimized search query
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
    
    Respond with ONLY the optimized query text, no additional text or explanations.
    """
    
    optimized_query = await lwi._query_local_model(information_prompt)
    print(f"\nOriginal query: {query}")
    print(f"Optimized query: {optimized_query}")
    
    # Test the improved website selection
    websites = await lwi.determine_relevant_websites(optimized_query, "fishing")
    print(f"\nSelected websites for fishing query: {websites}")
    
    # Test another category
    health_query = "What are the most effective weight loss strategies in 2025"
    health_websites = await lwi.determine_relevant_websites(health_query, "health")
    print(f"\nSelected websites for health query: {health_websites}")
    
    # Test the fallback mechanism
    tech_query = "Latest smartphone models in 2025"
    tech_websites = await lwi.determine_relevant_websites(tech_query, "tech")
    print(f"\nSelected websites for tech query: {tech_websites}")
    
    # Test the analyze_search_results method
    print("\nTesting analyze_search_results method...")
    prioritized_websites = await lwi.analyze_search_results(websites, optimized_query)
    print(f"Prioritized websites: {prioritized_websites}")
    
    print("\n" + "="*80)
    print("VERIFICATION COMPLETE")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(main())
