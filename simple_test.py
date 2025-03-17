import asyncio
import logging
from glama_mcp_integration import LocalWebIntegration

# Set up logging
logging.basicConfig(level=logging.INFO)

async def test_search_query_generation():
    print("Testing improved search query generation...")
    lwi = LocalWebIntegration()
    
    # Test queries
    test_queries = [
        "Find information about the latest smartphone models in 2025",
        "What are the most effective weight loss strategies in 2025",
        "Who are the most popular actors in 2025",
        "What are the best fishing spots in California",
        "How to invest in the stock market in 2025"
    ]
    
    for query in test_queries:
        print("\n" + "="*50)
        print(f"ORIGINAL QUERY: {query}")
        
        # Extract the topic and category
        topic_prompt = f"""
        You are an AI assistant tasked with analyzing a user's information request.
        
        User request: {query}
        
        Please analyze this request and extract the following information:
        1. The main topic or subject - be as specific as possible (e.g., "fishing rods for beginners", "electric vehicles", "DSLR cameras for wildlife photography")
        2. The content category that best describes this topic - choose the most specific category possible
        
        For the category, consider these options but don't limit yourself to them:
        - fishing (for fishing-related topics)
        - outdoor (for hiking, camping, outdoor activities)
        - sports (for sports-related topics)
        - gaming (for video games, gaming hardware)
        - tech (for technology, gadgets, software)
        - health (for health, fitness, nutrition)
        - finance (for money, investing, economy)
        - news (for current events, headlines)
        - cooking (for recipes, food preparation)
        - travel (for destinations, travel tips)
        - education (for learning, courses)
        
        Respond in this exact format:
        Topic: [the specific topic]
        Category: [specific category]
        """
        
        topic_analysis = await lwi._query_local_model(topic_prompt)
        print(f"TOPIC ANALYSIS: {topic_analysis}")
        
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
        
        STRUCTURE YOUR QUERY WITH:
        - Primary topic/subject first
        - Specific attributes or qualifiers
        - Time frame indicators (2025, current, latest, etc.)
        - Content type indicators (guide, review, comparison, analysis, etc.)
        - Authority indicators (expert, official, research, etc.)
        
        EXAMPLES OF HIGHLY EFFECTIVE SEARCH QUERIES:
        - For entertainment: "top 10 highest-grossing actors 2025 box office rankings current data"
        - For products: "best premium fishing rods 2025 expert reviews comparison top brands specifications"
        - For technology: "latest flagship smartphone models 2025 features comparison battery life camera performance"
        - For health: "effective evidence-based weight loss strategies 2025 medical research clinical studies"
        - For finance: "stock market sector performance 2025 expert analysis trends predictions data"
        
        Respond with ONLY the optimized query text, no additional text or explanations.
        """
        
        optimized_query = await lwi._query_local_model(information_prompt)
        print(f"OPTIMIZED SEARCH QUERY: {optimized_query}")
        
        # Determine websites
        category = topic_analysis.split("Category:")[1].strip() if "Category:" in topic_analysis else "general"
        websites = await lwi.determine_relevant_websites(optimized_query, category)
        print(f"SELECTED WEBSITES: {websites}")
        
        print("="*50)

if __name__ == "__main__":
    asyncio.run(test_search_query_generation())
