import sys
import os
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from openai import OpenAI

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.utils.secret_manager import get_openai_secrets


class InvoiceLineItem(BaseModel):
    part_number: Optional[str] = None
    line_description: str
    quantity: float
    unit_price: float
    line_total: Optional[float] = None
    confidence: int


class InvoiceData(BaseModel):
    vendor_name: str
    vendor_name_confidence: int
    invoice_number: str
    invoice_number_confidence: int
    invoice_date: str
    invoice_date_confidence: int
    invoice_total: float
    invoice_total_confidence: int
    line_items: List[InvoiceLineItem]
    extraction_notes: str


def extract_invoice_data(
    sender_email: str,
    sender_name: str,
    subject: str,
    body: str,
    attachments: Optional[List[Dict[str, Any]]] = None
) -> Optional[InvoiceData]:
    
    api_key = get_openai_secrets()
    client = OpenAI(api_key=api_key)
    
    system_prompt = """
    
    You are an invoice data extraction AI. Your job is to extract structured invoice data from emails and attachments.
    
    **Extract the following header fields:**
    - vendor_name: The name of the vendor/supplier sending the invoice
    - invoice_number: The invoice number (max 50 characters)
    - invoice_date: The invoice date in MM/DD/YYYY or YYYY-MM-DD format
    - invoice_total: The total amount of the invoice (as a number)
    
    **Extract line items with:**
    - part_number: Part number or SKU (optional - often appears at start of description or in a separate column)
    - line_description: Description of the item/service (full description including part number if it's embedded)
    - quantity: Quantity ordered (as a number)
    - unit_price: Price per unit (as a number)
    - line_total: Total for this line (optional - if not explicitly stated, leave as null)
    
    **For each field, provide a confidence score (0-100):**
    - 90-100: Very confident, explicitly stated in the document
    - 70-89: Somewhat confident, inferred from context
    - 0-69: Low confidence, guessing or unclear
    
    **Important notes:**
    - If invoice has no line item details, create a single line item with description "Invoice Total" and the total amount
    - Be precise with numbers - don't add or modify amounts
    - Extract vendor name exactly as it appears on the invoice
    - Look for invoice data in both the email body and any attached PDFs
    - Provide extraction_notes explaining any challenges or assumptions made
    
    """

    user_text = f"""
    
    Please extract invoice data from this email:

    **From:** {sender_name} <{sender_email}>
    **Subject:** {subject}

    **Body:**

    {body[:3000]}
    
    """

    if len(body) > 3000:
        user_text += "\n\n[Body truncated for length]"
    
    user_content = []
    
    attachment_note = ""
    if attachments:
        pdf_count = 0
        
        for attachment in attachments:
            attachment_type = attachment.get('type')
            filename = attachment.get('filename', 'unknown')
            base64_data = attachment.get('base64_data', '')
            
            if filename.lower().endswith('.pdf') and base64_data:
                pdf_count += 1
                user_content.append({
                    "type": "input_file",
                    "filename": filename,
                    "file_data": f"data:application/pdf;base64,{base64_data}"
                })
        
        if pdf_count > 0:
            attachment_note = f"\n\n**Attachments:** {pdf_count} PDF(s) attached - please analyze them for invoice data"
    
    user_content.append({
        "type": "input_text",
        "text": user_text + attachment_note
    })
    
    try:
        print(f"\n📄 Extracting invoice data from email...")
        
        response = client.responses.parse(
            model="gpt-5",
            input=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ],
            text_format=InvoiceData,
            reasoning={"effort": "medium"}
        )
        
        invoice_data = response.output_parsed
        
        print(f"\n✅ Invoice Data Extracted:")
        print(f"   Vendor: {invoice_data.vendor_name} (confidence: {invoice_data.vendor_name_confidence}%)")
        print(f"   Invoice #: {invoice_data.invoice_number} (confidence: {invoice_data.invoice_number_confidence}%)")
        print(f"   Date: {invoice_data.invoice_date} (confidence: {invoice_data.invoice_date_confidence}%)")
        print(f"   Total: ${invoice_data.invoice_total} (confidence: {invoice_data.invoice_total_confidence}%)")
        print(f"   Line Items: {len(invoice_data.line_items)}")
        
        for i, item in enumerate(invoice_data.line_items, 1):
            part_info = f"Part: {item.part_number} | " if item.part_number else ""
            print(f"      {i}. {part_info}{item.line_description}")
            print(f"         Qty: {item.quantity}, Price: ${item.unit_price}, Total: ${item.line_total or (item.quantity * item.unit_price)}")
            print(f"         Confidence: {item.confidence}%")
        
        if invoice_data.extraction_notes:
            print(f"   Notes: {invoice_data.extraction_notes}")
        
        return invoice_data
    
    except Exception as e:
        print(f"\n❌ Error extracting invoice data: {e}")
        return None

