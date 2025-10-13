import requests
import json
import os
import sys
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import html2text

# Add project root to path for direct execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.utils.secret_manager import get_outlook_secrets
from core.utils.log_manager.log_manager import log_error

BASE_URL = "https://graph.microsoft.com/v1.0"


def clean_html_body(html_content: str) -> str:
    if not html_content:
        return ""
    
    try:
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.ignore_emphasis = True
        h.body_width = 0
        h.unicode_snob = True
        h.skip_internal_links = True
        
        text = h.handle(html_content)
        
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()
        
        return text
    except Exception as e:
        return html_content


def authenticate_graph_api():
    try:
        secrets = get_outlook_secrets()
        tenant_id = secrets['tenant_id']
        client_id = secrets['client_id']
        client_secret = secrets['client_secret']
        
        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': 'https://graph.microsoft.com/.default'
        }
        
        response = requests.post(token_url, headers=headers, data=data, timeout=30)
        
        if response.status_code == 200:
            token_data = response.json()
            
            # Calculate expiration time
            expires_in = token_data.get('expires_in', 3600)
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            return {
                'access_token': token_data['access_token'],
                'token_type': token_data.get('token_type', 'Bearer'),
                'expires_at': expires_at,
                'scope': token_data.get('scope', '')
            }
        else:
            log_error(f"Graph API authentication failed: {response.status_code} - {response.text}",
                     Exception("Graph API authentication error"))
            return None
            
    except Exception as e:
        log_error("Graph API authentication failed", e)
        return None


def graph_api_request(token_data, method, endpoint, data=None, params=None):
    if not token_data or not token_data.get('access_token'):
        log_error("Graph API request failed - no valid access token available",
                 Exception("Missing or invalid access token"))
        return None
        
    try:
        url = f"{BASE_URL}/{endpoint}"
        
        headers = {
            'Authorization': f"Bearer {token_data['access_token']}",
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Make the request
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, params=params, timeout=30)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=headers, json=data, params=params, timeout=30)
        elif method.upper() == 'PATCH':
            response = requests.patch(url, headers=headers, json=data, params=params, timeout=30)
        elif method.upper() == 'DELETE':
            response = requests.delete(url, headers=headers, params=params, timeout=30)
        else:
            log_error(f"Graph API request failed - unsupported HTTP method: {method}",
                     Exception("Unsupported HTTP method"))
            return None
        
        # Handle response
        if response.status_code in [200, 201, 202, 204]:
            if response.status_code == 204:
                return {"success": True}  # No content response
            try:
                return response.json()
            except json.JSONDecodeError:
                return {"success": True}  # Success but no JSON content
        else:
            log_error(f"Graph API {method} {endpoint} failed: {response.status_code} - {response.text}",
                     Exception("Graph API request error"))
            return None
            
    except Exception as e:
        log_error(f"Graph API {method} {endpoint} failed", e)
        return None

# =============================================================================
# EMAIL OPERATIONS
# =============================================================================

def get_emails(token_data, mailbox_id=None, folder="inbox", limit=100, include_read=True):
    try:
        # Use configured mailbox if none provided
        if not mailbox_id:
            secrets = get_outlook_secrets()
            mailbox_id = secrets['mailbox_id']
        
        # Build endpoint
        if folder:
            endpoint = f"users/{mailbox_id}/mailFolders/{folder}/messages"
        else:
            endpoint = f"users/{mailbox_id}/messages"
        
        # Parameters for the request
        params = {
            '$select': 'id,subject,sender,from,toRecipients,receivedDateTime,createdDateTime,body,bodyPreview,isRead,importance,hasAttachments,internetMessageId,conversationId',
            '$orderby': 'receivedDateTime desc',
            '$top': limit
        }
        
        # Add filter for unread only if specified
        if not include_read:
            params['$filter'] = 'isRead eq false'
        
        # Make the API request
        result = graph_api_request(token_data, 'GET', endpoint, params=params)
        
        if result and 'value' in result:
            emails = result['value']
            
            # Process and format the emails (same formatting as get_unread_emails)
            formatted_emails = []
            for email in emails:
                raw_body = email.get('body', {}).get('content', '')
                body_type = email.get('body', {}).get('contentType', 'text')
                
                if body_type.lower() == 'html':
                    cleaned_body = clean_html_body(raw_body)
                else:
                    cleaned_body = raw_body
                
                formatted_email = {
                    'id': email.get('id'),
                    'subject': email.get('subject', 'No Subject'),
                    'sender_email': email.get('sender', {}).get('emailAddress', {}).get('address', ''),
                    'sender_name': email.get('sender', {}).get('emailAddress', {}).get('name', ''),
                    'from_email': email.get('from', {}).get('emailAddress', {}).get('address', ''),
                    'from_name': email.get('from', {}).get('emailAddress', {}).get('name', ''),
                    'received_datetime': email.get('receivedDateTime'),
                    'created_datetime': email.get('createdDateTime'),
                    'body_content': cleaned_body,
                    'body_content_type': body_type,
                    'body_preview': email.get('bodyPreview', ''),
                    'is_read': email.get('isRead', True),
                    'importance': email.get('importance', 'normal'),
                    'has_attachments': email.get('hasAttachments', False),
                    'internet_message_id': email.get('internetMessageId'),
                    'conversation_id': email.get('conversationId'),
                    'to_recipients': [
                        {
                            'email': recipient.get('emailAddress', {}).get('address', ''),
                            'name': recipient.get('emailAddress', {}).get('name', '')
                        }
                        for recipient in email.get('toRecipients', [])
                    ]
                }
                formatted_emails.append(formatted_email)
            
            return formatted_emails
        else:
            return []
            
    except Exception as e:
        log_error("Failed to fetch emails from Outlook", e)
        return []


def get_email_attachments(token_data, message_id: str, mailbox_id: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
    try:
        if not mailbox_id:
            secrets = get_outlook_secrets()
            mailbox_id = secrets['mailbox_id']

        # Expand item for ItemAttachment to get nested message details when possible
        endpoint = f"users/{mailbox_id}/messages/{message_id}/attachments"
        params = {
            "$expand": "microsoft.graph.itemattachment/item"
        }
        result = graph_api_request(token_data, 'GET', endpoint, params=params)
        if result and 'value' in result:
            return result['value']
        return []
    except Exception as e:
        log_error(f"Failed to fetch attachments for message {message_id}", e)
        return None


def reply_to_email(token_data, message_id, reply_body, reply_subject=None, mailbox_id=None, content_type="HTML"):
    try:
        # Use configured mailbox if none provided
        if not mailbox_id:
            secrets = get_outlook_secrets()
            mailbox_id = secrets['mailbox_id']
        
        # Build endpoint for reply
        endpoint = f"users/{mailbox_id}/messages/{message_id}/reply"
        
        # Prepare reply data using 'comment' field to preserve email thread history
        # The 'comment' field automatically includes previous messages in the thread
        reply_data = {
            "comment": reply_body,
            "message": {
                "ccRecipients": [
                    {
                        "emailAddress": {
                            "address": "braden.sanders@stoneagetools.com",
                            "name": "Braden Sanders"
                        }
                    }
                ]
            }
        }
        
        # Add custom subject if provided
        if reply_subject:
            reply_data["message"]["subject"] = reply_subject
        
        # Send the reply
        result = graph_api_request(token_data, 'POST', endpoint, data=reply_data)
        
        if result:
            return True
        else:
            return False
            
    except Exception as e:
        log_error("Failed to reply to email", e)
        return False


def mark_email_as_read(token_data, message_id, mailbox_id=None, is_read=True):
    try:
        # Use configured mailbox if none provided
        if not mailbox_id:
            secrets = get_outlook_secrets()
            mailbox_id = secrets['mailbox_id']
        
        # Build endpoint for updating message
        endpoint = f"users/{mailbox_id}/messages/{message_id}"
        
        # Prepare update data
        update_data = {
            "isRead": is_read
        }
        
        # Update the message
        result = graph_api_request(token_data, 'PATCH', endpoint, data=update_data)
        
        if result:
            return True
        else:
            return False
            
    except Exception as e:
        action = "mark as read" if is_read else "mark as unread"
        log_error(f"Failed to {action} email", e)
        return False