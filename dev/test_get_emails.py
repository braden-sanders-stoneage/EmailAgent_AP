import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.integrations.outlook.client import authenticate_graph_api, get_emails


def print_separator(char="=", length=100):
    print(char * length)


def print_email(email, index):
    print_separator("=")
    print(f"📧 EMAIL #{index}")
    print_separator("=")
    
    print(f"\n{'ID:':<20} {email.get('id', 'N/A')}")
    print(f"{'Subject:':<20} {email.get('subject', 'N/A')}")
    print(f"{'From:':<20} {email.get('from_name', 'N/A')} <{email.get('from_email', 'N/A')}>")
    print(f"{'Sender:':<20} {email.get('sender_name', 'N/A')} <{email.get('sender_email', 'N/A')}>")
    
    to_recipients = email.get('to_recipients', [])
    if to_recipients:
        print(f"{'To:':<20} ", end="")
        for i, recipient in enumerate(to_recipients):
            if i == 0:
                print(f"{recipient.get('name', 'N/A')} <{recipient.get('email', 'N/A')}>")
            else:
                print(f"{'':<20} {recipient.get('name', 'N/A')} <{recipient.get('email', 'N/A')}>")
    
    received = email.get('received_datetime', 'N/A')
    print(f"{'Received:':<20} {received}")
    
    created = email.get('created_datetime', 'N/A')
    print(f"{'Created:':<20} {created}")
    
    print(f"{'Is Read:':<20} {'✓ Yes' if email.get('is_read') else '✗ No'}")
    print(f"{'Has Attachments:':<20} {'✓ Yes' if email.get('has_attachments') else '✗ No'}")
    print(f"{'Importance:':<20} {email.get('importance', 'N/A').upper()}")
    print(f"{'Content Type:':<20} {email.get('body_content_type', 'N/A')}")
    print(f"{'Conversation ID:':<20} {email.get('conversation_id', 'N/A')}")
    print(f"{'Message ID:':<20} {email.get('internet_message_id', 'N/A')}")
    
    print(f"\n{'Body Preview:':<20}")
    print_separator("-")
    preview = email.get('body_preview', 'N/A')
    if len(preview) > 500:
        print(preview[:500] + "...")
    else:
        print(preview)
    
    print("\n")


def main():
    print("\n")
    print_separator("=")
    print("  📬 EMAIL FETCHER TEST SCRIPT")
    print_separator("=")
    print("\n")
    
    print("🔐 Authenticating with Graph API...")
    token_data = authenticate_graph_api()
    
    if not token_data:
        print("❌ Authentication failed!")
        return
    
    print("✓ Authentication successful!\n")
    
    print("📥 Fetching emails...")
    emails = get_emails(token_data, folder="inbox", limit=10, include_read=False)
    
    if not emails:
        print("📭 No emails found or error occurred.")
        return
    
    print(f"✓ Found {len(emails)} email(s)\n")
    
    for i, email in enumerate(emails, 1):
        print_email(email, i)
    
    print_separator("=")
    print(f"  ✓ COMPLETED - Displayed {len(emails)} email(s)")
    print_separator("=")
    print("\n")


if __name__ == "__main__":
    main()

