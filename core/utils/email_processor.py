import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.integrations.outlook.client import get_email_attachments
from core.integrations.outlook.attachments import process_attachments
from core.ai.classifier import categorize_email
from core.ai.invoice_extractor import extract_invoice_data
from core.integrations.epicor.invoices import get_invoice_from_epicor
from core.utils.vendor_finder import match_vendor_from_invoice


def process_email(token_data, email_data):
    email_id = email_data.get('id')
    sender_email = email_data.get('sender_email', '')
    sender_name = email_data.get('sender_name', '')
    subject = email_data.get('subject', 'No Subject')
    body = email_data.get('body_content', '')
    has_attachments = email_data.get('has_attachments', False)
    
    processed_attachments = None
    attachment_list = None
    
    if has_attachments:
        raw_attachments = get_email_attachments(token_data, email_id)
        if raw_attachments:
            processed_attachments = process_attachments(raw_attachments)
            images = processed_attachments.get('images', [])
            other_files = processed_attachments.get('other_files', [])
            attachment_list = images + other_files if (images or other_files) else None
    
    categorization = categorize_email(
        sender_email=sender_email,
        sender_name=sender_name,
        subject=subject,
        body=body,
        attachments=attachment_list
    )
    
    epicor_results = []
    if categorization.has_invoice and categorization.invoice_numbers:
        for invoice_num in categorization.invoice_numbers:
            result = get_invoice_from_epicor(invoice_num)
            
            invoice_entry = {
                "invoice_number": invoice_num,
                "found_in_epicor": result["found"],
                "epicor_url": result.get("epicor_url"),
                "invoice_data": result.get("invoice_details")
            }
            epicor_results.append(invoice_entry)
    
    extracted_invoice_data = None
    vendor_matches = []
    
    if categorization.email_type == 'new_invoice':
        print(f"\n🔍 Email categorized as new_invoice - extracting invoice data...")
        
        invoice_data = extract_invoice_data(
            sender_email=sender_email,
            sender_name=sender_name,
            subject=subject,
            body=body,
            attachments=attachment_list
        )
        
        if invoice_data:
            vendor_matches = match_vendor_from_invoice(invoice_data.vendor_name)
            
            extracted_invoice_data = {
                "vendor_name": invoice_data.vendor_name,
                "vendor_name_confidence": invoice_data.vendor_name_confidence,
                "invoice_number": invoice_data.invoice_number,
                "invoice_number_confidence": invoice_data.invoice_number_confidence,
                "invoice_date": invoice_data.invoice_date,
                "invoice_date_confidence": invoice_data.invoice_date_confidence,
                "invoice_total": invoice_data.invoice_total,
                "invoice_total_confidence": invoice_data.invoice_total_confidence,
                "line_items": [
                    {
                        "part_number": item.part_number,
                        "description": item.line_description,
                        "quantity": item.quantity,
                        "unit_price": item.unit_price,
                        "line_total": item.line_total or (item.quantity * item.unit_price),
                        "confidence": item.confidence
                    }
                    for item in invoice_data.line_items
                ],
                "extraction_notes": invoice_data.extraction_notes,
                "vendor_matches": vendor_matches
            }
            
            print(f"✅ Invoice data extraction complete")
    
    return {
        "email_id": email_id,
        "subject": subject,
        "sender_name": sender_name,
        "sender_email": sender_email,
        "category": categorization.email_type,
        "reason": categorization.reason,
        "has_invoice": categorization.has_invoice,
        "invoice_numbers": categorization.invoice_numbers,
        "epicor_results": epicor_results,
        "extracted_invoice_data": extracted_invoice_data,
        "internet_message_id": email_data.get('internet_message_id')
    }

