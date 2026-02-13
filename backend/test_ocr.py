from src.ocr.azure_ocr import AzureOCRService

ocr = AzureOCRService()

result = ocr.extract_invoice("sample.pdf")

print("OCR RESULT:")
print(result)
