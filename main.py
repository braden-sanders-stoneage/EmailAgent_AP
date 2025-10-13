import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.integrations.outlook.client import authenticate_graph_api, get_emails, get_email_attachments
from core.integrations.outlook.attachments import process_attachments
from core.ai.classifier import categorize_email
from core.utils.file_system import sort_email


def main():
    print("\n" + "="*80)
    print("  EMAIL CATEGORIZATION SYSTEM")
    print("="*80 + "\n")
    
    print("🔐 Authenticating with Graph API...")
    token_data = authenticate_graph_api()
    
    if not token_data:
        print("❌ Authentication failed!")
        return
    
    print("✓ Authentication successful!\n")
    
    print("📥 Fetching emails...")
    emails = get_emails(token_data, folder="inbox", limit=10, include_read=True)
    
    if not emails:
        print("📭 No emails found.")
        return
    
    print(f"✓ Found {len(emails)} email(s)\n")
    print("="*80)
    
    for i, email in enumerate(emails, 1):
        print(f"\n📧 Processing Email {i}/{len(emails)}")
        print("="*80)
        
        email_id = email.get('id')
        sender_email = email.get('sender_email', '')
        sender_name = email.get('sender_name', '')
        subject = email.get('subject', 'No Subject')
        body = email.get('body_content', '')
        has_attachments = email.get('has_attachments', False)
        
        print(f"\n{'FROM:':<15} {sender_name} <{sender_email}>")
        print(f"{'SUBJECT:':<15} {subject}")
        print(f"{'DATE:':<15} {email.get('received_datetime', 'N/A')}")
        
        processed_attachments = None
        attachment_filenames = []
        
        if has_attachments:
            raw_attachments = get_email_attachments(token_data, email_id)
            print(f"[DEBUG] Got {len(raw_attachments) if raw_attachments else 0} raw attachments")
            if raw_attachments:
                processed_attachments = process_attachments(raw_attachments)
                print(f"[DEBUG] Processed attachments: {processed_attachments.keys() if processed_attachments else 'None'}")
                images = processed_attachments.get('images', [])
                other_files = processed_attachments.get('other_files', [])
                for img in images:
                    attachment_filenames.append(img.get('filename', 'unknown'))
                for other in other_files:
                    attachment_filenames.append(other.get('filename', 'unknown'))
        
        if attachment_filenames:
            print(f"{'ATTACHMENTS:':<15} {len(attachment_filenames)} file(s)")
            for filename in attachment_filenames:
                print(f"{'':>15} - {filename}")
        else:
            print(f"{'ATTACHMENTS:':<15} None")
        
        print(f"\n{'BODY:':<15}")
        print("-"*80)
        if body:
            truncated_body = body[:200] + "..." if len(body) > 200 else body
            print(truncated_body)
        else:
            print("(Empty body)")
        print("-"*80)
        
        attachment_list = None
        if processed_attachments:
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
        
        print(f"\n[DEBUG] Passing to sort_email - processed_attachments type: {type(processed_attachments)}")
        if processed_attachments:
            print(f"[DEBUG] processed_attachments keys: {processed_attachments.keys()}")
            print(f"[DEBUG] Images count: {len(processed_attachments.get('images', []))}")
            print(f"[DEBUG] Other files count: {len(processed_attachments.get('other_files', []))}")
        
        folder_path = sort_email(
            email_data=email,
            category=categorization.email_type,
            attachments=processed_attachments
        )
        
        print(f"\n💾 Email saved to: {folder_path}")
        
        print("-"*80)

        input("TEMP DEBUG PAUSE: Press Enter to continue...")
    
    print("\n" + "="*80)
    print(f"  ✓ COMPLETED - Categorized {len(emails)} email(s)")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
