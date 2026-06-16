import asyncio
from glama_mcp_integration import LocalWebIntegration

async def main():
    web = LocalWebIntegration()
    
    # Test determining relevant websites
    print("Testing website determination for 'Queen of England'...")
    websites = await web.determine_relevant_websites('Queen of England')
    print(f"Websites: {websites}")
    
    # Test full web task execution
    print("\nTesting full web task execution...")
    result = await web.execute_web_task('Please gather articles about the Queen of England and save them to a file named "queen.txt"')
    print(f"Task result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
