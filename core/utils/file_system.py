import os
import sys
import re
import base64
from datetime import datetime, timedelta
import pytz

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def sanitize_subject_to_snake_case(subject: str) -> str:
    if not subject or subject.strip() == "":
        return "no_subject"
    
    text = subject.lower()
    
    text = re.sub(r'[^\w\s-]', '', text)
    
    text = re.sub(r'[-\s]+', '_', text)
    
    text = text.strip('_')
    
    if len(text) > 50:
        text = text[:50].rstrip('_')
    
    if not text:
        return "no_subject"
    
    return text


def get_current_week_folder() -> str:
    mst = pytz.timezone('America/Denver')
    now = datetime.now(mst)
    
    days_since_monday = now.weekday()
    monday = now - timedelta(days=days_since_monday)
    
    month_name = monday.strftime("%b")
    day = monday.day
    year = monday.year
    
    return f"Week_Of_{month_name}_{day}_{year}"


def create_email_folder(category: str, subject: str) -> str:
    base_dir = "emails"
    
    week_folder = get_current_week_folder()
    week_path = os.path.join(base_dir, week_folder)
    os.makedirs(week_path, exist_ok=True)
    
    category_dir = os.path.join(week_path, category)
    os.makedirs(category_dir, exist_ok=True)
    
    sanitized_subject = sanitize_subject_to_snake_case(subject)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    folder_name = f"{sanitized_subject}_{timestamp}"
    
    folder_path = os.path.join(category_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    
    return folder_path


def save_email_details(folder_path: str, email_data: dict) -> None:
    file_path = os.path.join(folder_path, "email_details.txt")
    
    sender_name = email_data.get('sender_name', 'Unknown')
    sender_email = email_data.get('sender_email', 'unknown@email.com')
    subject = email_data.get('subject', 'No Subject')
    date = email_data.get('received_datetime', 'Unknown Date')
    body = email_data.get('body_content', '')
    
    content = f"""FROM: {sender_name} <{sender_email}>
SUBJECT: {subject}
DATE: {date}

BODY:
{body}
"""
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


def save_attachments(folder_path: str, attachments: dict) -> None:
    print(f"[DEBUG] save_attachments called with attachments: {type(attachments)}")
    
    if not attachments:
        print("[DEBUG] No attachments provided (None or empty)")
        return
    
    images = attachments.get('images', [])
    other_files = attachments.get('other_files', [])
    
    print(f"[DEBUG] Found {len(images)} images and {len(other_files)} other files")
    
    all_files = images + other_files
    
    if not all_files:
        print("[DEBUG] No files to save after combining images and other_files")
        return
    
    filename_counts = {}
    saved_count = 0
    
    for attachment in all_files:
        filename = attachment.get('filename', 'unnamed_file')
        base64_data = attachment.get('base64_data', '')
        
        print(f"[DEBUG] Processing attachment: {filename}, has_data: {bool(base64_data)}")
        
        if not base64_data:
            print(f"[DEBUG] Skipping {filename} - no base64 data")
            continue
        
        if filename in filename_counts:
            filename_counts[filename] += 1
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{filename_counts[filename]}{ext}"
        else:
            filename_counts[filename] = 0
        
        try:
            file_bytes = base64.b64decode(base64_data)
            
            file_path = os.path.join(folder_path, filename)
            
            with open(file_path, 'wb') as f:
                f.write(file_bytes)
            
            saved_count += 1
            print(f"[DEBUG] ✓ Saved attachment: {filename} ({len(file_bytes)} bytes)")
        except Exception as e:
            print(f"[DEBUG] ✗ Failed to save attachment {filename}: {e}")
    
    print(f"[DEBUG] Total attachments saved: {saved_count}/{len(all_files)}")


def sort_email(email_data: dict, category: str, attachments: dict = None) -> str:
    subject = email_data.get('subject', 'No Subject')
    
    folder_path = create_email_folder(category, subject)
    
    save_email_details(folder_path, email_data)
    
    if attachments:
        save_attachments(folder_path, attachments)
    
    return folder_path

