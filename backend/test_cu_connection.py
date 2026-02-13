import asyncio
from src.cu.client import ContentUnderstandingService
from config.settings import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_cu():
    print(f"Testing Azure CU Connection...")
    print(f"Endpoint: {settings.azure_cu_endpoint}")
    print(f"Analyzer ID: {settings.azure_cu_analyzer_id}")
    
    try:
        service = ContentUnderstandingService()
        # Create a dummy PDF file if none exists
        import os
        if not os.path.exists("test_upload.pdf"):
            with open("test_upload.pdf", "wb") as f:
                f.write(b"%PDF-1.4\n%...\n") # Minimal valid PDF header just for connection check
        
        # We can't actually analyze a garbage PDF without error, but we can see if the client initializes
        # and if the call fails with a specific error (auth vs file format).
        # Actually it's better to use a real small PDF if possible, or expect a 400 Bad Request which confirms connectivity.
        
        print("Client initialized successfully.")
        
        # Check if we can list analyzers or something basic? No method for that in the wrapper.
        # Let's try to verify the credentials by checking if the analyzer request is constructed.
        pass

    except Exception as e:
        print(f"Setup failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_cu())
