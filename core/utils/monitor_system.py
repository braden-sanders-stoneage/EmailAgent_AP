import threading
import time
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.integrations.outlook.client import get_emails, authenticate_graph_api, graph_api_request
from core.utils.secret_manager import get_outlook_secrets
from core.utils.email_processor import process_email


CATEGORY_MAPPING = {
    "new_invoice": "Green category",
    "supplier_statement": "Blue category",
    "request_for_status": "Yellow category",
    "account_update": "Orange category",
    "misc_spam": "Red category",
    "other": "Purple category"
}


def apply_category_to_email(token_data, email_id, category):
    secrets = get_outlook_secrets()
    mailbox_id = secrets['mailbox_id']
    
    category_name = CATEGORY_MAPPING.get(category, "Purple category")
    
    endpoint = f"users/{mailbox_id}/messages/{email_id}"
    data = {"categories": [category_name]}
    
    result = graph_api_request(token_data, 'PATCH', endpoint, data=data)
    return result is not None


def save_processed_email(email_result):
    os.makedirs('emails_data', exist_ok=True)
    
    email_id = email_result['email_id']
    internet_message_id = email_result.get('internet_message_id', '')
    
    file_path = os.path.join('emails_data', f"{email_id}.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(email_result, f, indent=2)
    
    id_mapping_path = os.path.join('emails_data', 'id_mapping.json')
    if os.path.exists(id_mapping_path):
        with open(id_mapping_path, 'r', encoding='utf-8') as f:
            id_mapping = json.load(f)
    else:
        id_mapping = {}
    
    if internet_message_id:
        id_mapping[internet_message_id] = email_id
        with open(id_mapping_path, 'w', encoding='utf-8') as f:
            json.dump(id_mapping, f, indent=2)


def monitor_emails():
    print("Email monitor started, checking every 60 seconds...")
    
    while True:
        try:
            token_data = authenticate_graph_api()
            if not token_data:
                print("Authentication failed, retrying in 60 seconds...")
                time.sleep(60)
                continue
            
            emails = get_emails(token_data, folder="inbox", limit=10, include_read=False)
            
            if emails:
                print(f"Found {len(emails)} unread email(s), processing...")
                
                for email in emails:
                    email_id = email.get('id')
                    subject = email.get('subject', 'No Subject')
                    
                    cache_path = os.path.join('emails_data', f"{email_id}.json")
                    if os.path.exists(cache_path):
                        continue
                    
                    print(f"Processing: {subject}")
                    
                    result = process_email(token_data, email)
                    save_processed_email(result)
                    apply_category_to_email(token_data, email_id, result['category'])
                    
                    print(f"  ✓ Categorized as: {result['category']}")
                    if result['has_invoice']:
                        print(f"  ✓ Invoices: {', '.join(result['invoice_numbers'])}")
            
        except Exception as e:
            print(f"Error in monitor: {e}")
        
        time.sleep(60)


def start_monitor():
    thread = threading.Thread(target=monitor_emails, daemon=True)
    thread.start()

