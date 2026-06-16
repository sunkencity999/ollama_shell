import asyncio
import logging
from glama_mcp_integration import LocalWebIntegration

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_multiple_topics():
    print("\n" + "="*80)
    print("TESTING SEARCH QUERY GENERATION AND WEBSITE SELECTION ACROSS TOPICS")
    print("="*80)
    
    lwi = LocalWebIntegration()
    
    # Define test queries for different topics
    test_queries = [
        {"query": "What are the most popular smartphones in 2025", "expected_category": "tech"},
        {"query": "Best diets for weight loss in 2025", "expected_category": "health"},
        {"query": "Top movies of 2025 so far", "expected_category": "entertainment"},
        {"query": "Current stock market trends for beginners", "expected_category": "finance"},
        {"query": "Best fishing spots in California", "expected_category": "fishing"}
    ]
    
    # Test each query
    for test in test_queries:
        query = test["query"]
        expected_category = test["expected_category"]
        
        print(f"\n\n{'='*40}")
        print(f"TESTING: {query}")
        print(f"EXPECTED CATEGORY: {expected_category}")
        print(f"{'='*40}")
        
        # 1. Analyze topic and category
        topic_prompt = f"""
        Analyze the following user query and identify the main topic and category:
        
        USER QUERY: {query}
        
        Respond in this exact format:
        Topic: [main topic]
        Category: [category]
        
        Choose the most specific category from: tech, health, entertainment, sports, finance, news, gaming, fishing, travel, cooking, education
        """
        
        topic_analysis = await lwi._query_local_model(topic_prompt)
        print(f"\nTOPIC ANALYSIS: {topic_analysis}")
        
        # 2. Generate optimized search query
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
        print(f"\nOPTIMIZED SEARCH QUERY: {optimized_query}")
        
        # 3. Get relevant websites
        category = None
        for line in topic_analysis.split('\n'):
            if line.startswith("Category:"):
                category = line.replace("Category:", "").strip().lower()
                break
        
        if not category:
            category = expected_category
        
        websites = await lwi.determine_relevant_websites(optimized_query, category)
        print(f"\nSELECTED WEBSITES: {websites}")
        
        # 4. Test analyze_search_results method
        prioritized_websites = await lwi.analyze_search_results(websites, optimized_query)
        print(f"\nPRIORITIZED WEBSITES: {prioritized_websites}")
        
    print("\n" + "="*80)
    print("TESTING COMPLETE")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_multiple_topics())
