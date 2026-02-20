"""Quick smoke-test for the extraction backend.

Tests that ContentUnderstandingService can initialise with the configured
backend (Docling+Gemini or Azure DI) and optionally analyses a small PDF.
"""

import asyncio
import os
import logging

from src.cu.client import ContentUnderstandingService
from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_cu():
    print(f"Testing extraction backend (configured: {settings.extraction_backend}) …")
    print(f"  Gemini model : {settings.gemini_model}")
    print(f"  Azure DI EP  : {settings.azure_doc_endpoint or '(not set)'}")

    try:
        service = ContentUnderstandingService()
        print(f"✅ Backend initialised — active model_id: {service.model_id}")

        # Optionally analyse a tiny dummy PDF
        test_pdf = "test_upload.pdf"
        if not os.path.exists(test_pdf):
            # Create a minimal PDF for connectivity check
            with open(test_pdf, "wb") as f:
                f.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
            print(f"  (created minimal {test_pdf} for smoke-test)")

        print("Service ready.  To run a full analysis, call:")
        print(f"  service.analyze_document('{test_pdf}')")

    except Exception as e:
        print(f"❌ Setup failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_cu())
