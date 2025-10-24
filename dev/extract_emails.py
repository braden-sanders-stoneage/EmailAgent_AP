import sys
import os
import base64
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.integrations.outlook.client import authenticate_graph_api, graph_api_request, get_email_attachments


def extract_emails_from_mailbox(mailbox_email, limit=100):
    
    print(f"\n{'='*80}")
    print(f"Extracting up to {limit} emails from mailbox: {mailbox_email}")
    print(f"{'='*80}\n")
    
    token_data = authenticate_graph_api()
    if not token_data:
        print("❌ Failed to authenticate with Graph API")
        return
    
    print("✓ Authenticated successfully\n")
    
    endpoint = f"users/{mailbox_email}/messages"
    params = {
        '$select': 'id,subject,sender,from,receivedDateTime,hasAttachments',
        '$orderby': 'receivedDateTime desc',
        '$top': limit
    }
    
    print(f"Fetching emails from mailbox {mailbox_email}...")
    result = graph_api_request(token_data, 'GET', endpoint, params=params)
    
    if not result or 'value' not in result:
        print("❌ Failed to fetch emails")
        return
    
    emails = result['value']
    print(f"✓ Found {len(emails)} email(s)\n")
    
    if not emails:
        print("No emails found in this mailbox")
        return
    
    output_dir = Path(__file__).parent / "test_attachments"
    output_dir.mkdir(exist_ok=True)
    
    total_attachments = 0
    emails_with_attachments = 0
    
    for idx, email in enumerate(emails, 1):
        email_id = email.get('id')
        subject = email.get('subject', 'No Subject')
        has_attachments = email.get('hasAttachments', False)
        received = email.get('receivedDateTime', 'Unknown')
        sender = email.get('from', {}).get('emailAddress', {}).get('address', 'Unknown')
        
        print(f"\n[{idx}/{len(emails)}] {subject[:60]}")
        print(f"    From: {sender}")
        print(f"    Received: {received}")
        
        if not has_attachments:
            print(f"    No attachments")
            continue
        
        attachments = get_email_attachments(token_data, email_id, mailbox_id=mailbox_email)
        
        if not attachments:
            print(f"    Failed to retrieve attachments")
            continue
        
        emails_with_attachments += 1
        print(f"    Attachments: {len(attachments)}")
        
        for att_idx, attachment in enumerate(attachments, 1):
            filename = attachment.get('name', f'attachment_{att_idx}')
            content_bytes = attachment.get('contentBytes')
            attachment_type = attachment.get('@odata.type', '')
            
            if '#microsoft.graph.fileAttachment' in attachment_type and content_bytes:
                try:
                    file_data = base64.b64decode(content_bytes)
                    
                    safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '.', '_', '-')).strip()
                    if not safe_filename:
                        safe_filename = f'attachment_{att_idx}'
                    
                    file_path = output_dir / safe_filename
                    
                    counter = 1
                    original_path = file_path
                    while file_path.exists():
                        stem = original_path.stem
                        suffix = original_path.suffix
                        file_path = output_dir / f"{stem}_{counter}{suffix}"
                        counter += 1
                    
                    with open(file_path, 'wb') as f:
                        f.write(file_data)
                    
                    file_size = len(file_data) / 1024
                    print(f"      ✓ {filename} ({file_size:.1f} KB)")
                    total_attachments += 1
                    
                except Exception as e:
                    print(f"      ✗ Failed to save {filename}: {e}")
            
            elif '#microsoft.graph.itemAttachment' in attachment_type:
                print(f"      ⊙ {filename} (embedded message - skipped)")
            
            else:
                print(f"      ⊙ {filename} (unsupported type - skipped)")
    
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Total emails found: {len(emails)}")
    print(f"Emails with attachments: {emails_with_attachments}")
    print(f"Total attachments saved: {total_attachments}")
    print(f"Output directory: {output_dir.absolute()}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        mailbox_email = sys.argv[1]
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    else:
        mailbox_email = input("Enter mailbox/inbox email address: ").strip()
        limit_input = input("Enter max number of emails to fetch (default 100): ").strip()
        limit = int(limit_input) if limit_input else 100
    
    extract_emails_from_mailbox(mailbox_email, limit)

