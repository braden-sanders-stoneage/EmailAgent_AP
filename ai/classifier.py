import sys
import os
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel
from openai import OpenAI

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.secret_manager import get_openai_secrets


class EmailCategorization(BaseModel):
    email_type: Literal[
        "new_invoice",
        "supplier_statement", 
        "request_for_status",
        "account_update",
        "misc_spam",
        "other"
    ]
    reason: str


def categorize_email(
    sender_email: str,
    sender_name: str,
    subject: str,
    body: str,
    attachments: Optional[List[Dict[str, Any]]] = None
) -> EmailCategorization:
    
    api_key = get_openai_secrets()
    client = OpenAI(api_key=api_key)
    
    system_prompt = """
    
    You are an email classification AI. Your job is to categorize emails into one of these 6 categories:

    1. **new_invoice** - Emails containing invoices, bills, or payment requests from vendors/suppliers
    2. **supplier_statement** - Monthly or periodic account statements from suppliers showing balance, transactions
    3. **request_for_status** - Emails asking about order status, shipment tracking, payment status, or project updates
    4. **account_update** - Notifications about account changes, password resets, profile updates, or account-related notices
    5. **misc_spam** - Marketing emails, newsletters, promotional content, or spam
    6. **other** - Anything that doesn't fit the above categories

    Analyze the sender, subject, body content, and any attachments to make your determination.
    Provide a clear reason for your categorization.

    """

    user_text = f"""Please categorize this email:

**From:** {sender_name} <{sender_email}>
**Subject:** {subject}

**Body:**
{body[:2000]}"""

    if len(body) > 2000:
        user_text += "\n\n[Body truncated for length]"
    
    user_content = []
    
    attachment_note = ""
    if attachments:
        pdf_count = 0
        image_count = 0
        
        for attachment in attachments:
            attachment_type = attachment.get('type')
            filename = attachment.get('filename', 'unknown')
            mime_type = attachment.get('mime_type', '')
            base64_data = attachment.get('base64_data', '')
            
            if attachment_type == 'image':
                image_count += 1
            
            elif filename.lower().endswith('.pdf') and base64_data:
                pdf_count += 1
                user_content.append({
                    "type": "input_file",
                    "filename": filename,
                    "file_data": f"data:application/pdf;base64,{base64_data}"
                })
        
        if image_count > 0 or pdf_count > 0:
            attachment_note = f"\n\n**Attachments:** {pdf_count} PDF(s), {image_count} image(s)"
    
    user_content.append({
        "type": "input_text",
        "text": user_text + attachment_note
    })
    
    try:
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
            text_format=EmailCategorization,
            reasoning={"effort": "minimal"}
        )
        
        categorization = response.output_parsed
        
        print(f"\n📧 Email Categorized:")
        print(f"   Type: {categorization.email_type}")
        print(f"   Reason: {categorization.reason}\n")
        
        return categorization
    
    except Exception as e:
        print(f"\n❌ Error categorizing email: {e}")
        print(f"   Defaulting to 'other' category")
        return EmailCategorization(
            email_type="other",
            reason=f"Error during classification: {str(e)}"
        )

