import asyncio
import logging
import json
from glama_mcp_integration import LocalWebIntegration

# Set up logging
logging.basicConfig(level=logging.INFO)

async def test_web_search():
    print("Testing improved web search functionality...")
    lwi = LocalWebIntegration()
    
    # Test case 1: Technology query
    print("\n===== TEST CASE 1: TECHNOLOGY QUERY =====")
    query1 = "Find information about the latest smartphone models in 2025"
    print(f"Query: {query1}")
    
    # Create a modified version of execute_web_task that captures intermediate results
    original_analyze_search_results = lwi.analyze_search_results
    original_determine_relevant_websites = lwi.determine_relevant_websites
    
    captured_data = {}
    
    # Override the methods to capture data
    async def capture_analyze_search_results(websites, query):
        result = await original_analyze_search_results(websites, query)
        captured_data['final_websites'] = result
        return result
    
    async def capture_determine_relevant_websites(query, category=None, max_sites=5):
        result = await original_determine_relevant_websites(query, category, max_sites)
        captured_data['initial_websites'] = result
        return result
    
    # Apply the overrides
    lwi.analyze_search_results = capture_analyze_search_results
    lwi.determine_relevant_websites = capture_determine_relevant_websites
    
    # Execute the tasks
    print("\n----- Technology Query Test -----")
    result1 = await lwi.execute_web_task(query1)
    print(f"Generated search query: {captured_data.get('search_query', lwi.specific_query)}")
    print(f"Initial websites: {json.dumps(captured_data.get('initial_websites', []), indent=2)}")
    print(f"Final prioritized websites: {json.dumps(captured_data.get('final_websites', []), indent=2)}")
    
    # Reset captured data
    captured_data = {}
    
    print("\n----- Health Query Test -----")
    query2 = "What are the most effective weight loss strategies in 2025"
    print(f"Query: {query2}")
    result2 = await lwi.execute_web_task(query2)
    print(f"Generated search query: {captured_data.get('search_query', lwi.specific_query)}")
    print(f"Initial websites: {json.dumps(captured_data.get('initial_websites', []), indent=2)}")
    print(f"Final prioritized websites: {json.dumps(captured_data.get('final_websites', []), indent=2)}")
    
    # Reset captured data
    captured_data = {}
    
    print("\n----- Entertainment Query Test -----")
    query3 = "Who are the most popular actors in 2025"
    print(f"Query: {query3}")
    result3 = await lwi.execute_web_task(query3)
    print(f"Generated search query: {captured_data.get('search_query', lwi.specific_query)}")
    print(f"Initial websites: {json.dumps(captured_data.get('initial_websites', []), indent=2)}")
    print(f"Final prioritized websites: {json.dumps(captured_data.get('final_websites', []), indent=2)}")
    
    # Restore original methods
    lwi.analyze_search_results = original_analyze_search_results
    lwi.determine_relevant_websites = original_determine_relevant_websites
    
    print("\nTesting completed!")

if __name__ == "__main__":
    asyncio.run(test_web_search())
