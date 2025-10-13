import os
import requests
import subprocess
import tempfile
import csv
import base64
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

server = os.getenv('EPICOR_SERVER')
instance = os.getenv('EPICOR_INSTANCE')
api_key = os.getenv('EPICOR_API_KEY')
username = os.getenv('EPICOR_USERNAME')
password = os.getenv('EPICOR_PASSWORD')

def epicor_api_request(endpoint, method, company='SAINC', payload=None, params=None):
    
    # Use v1 for GetByID endpoint, v2 for others
    if 'GetByID' in endpoint:
        url = f"https://{server}/{instance}/api/v1/{endpoint}"
    else:
        url = f"https://{server}/{instance}/api/v2/odata/{company}/{endpoint}"
    
    headers = {
        'Authorization': f'Basic {base64.b64encode(f"{username}:{password}".encode()).decode()}',
        'x-api-key': api_key,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    if payload is None:
        response = requests.request(
        method=method,
        url=url,
        headers=headers,
        json=payload,
        params=params,
        auth=(username, password)
    )

    response = requests.request(
        method=method,
        url=url,
        headers=headers,
        json=payload,
        params=params,
        auth=(username, password)
    )
    
    # Debug prints
    debug_mode = True

    if debug_mode:

        print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
        print(f"\n🔍 API Request Details:")
        print(f"  URL: {url}")
        print(f"  Method: {method}")
        print(f"  Company: {company}")
        print(f"  Params: {params}")
        if payload:
            print(f"  Payload: {payload}")
        
        print(f"\n📡 Response Details:")
        print(f"  Status Code: {response.status_code}")
        print(f"  Headers: {dict(response.headers)}")
        try:
            print(f"  Response Body: {response.json()}")
        except:
            print(f"  Response Text: {response.text}")
        print("")
        print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')

    return response
    
def format_date_for_epicor(date_obj=None):
    if date_obj is None:
        date_obj = datetime.now()
    
    # Handle string dates from CSV
    if isinstance(date_obj, str):
        try:
            # Try parsing common date formats
            if '/' in date_obj:
                date_obj = datetime.strptime(date_obj, "%m/%d/%Y")
            elif '-' in date_obj:
                date_obj = datetime.strptime(date_obj, "%Y-%m-%d")
        except ValueError:
            # If parsing fails, use current date
            date_obj = datetime.now()
    
    return date_obj.strftime("%Y-%m-%d")

if __name__ == "__main__":
    # Test the connection with a common endpoint
    print("Testing Epicor connection...")
    
    try:
        # Test endpoint: Company service to get basic company information
        # This is a common, safe endpoint available in most Epicor instances
        response = epicor_api_request('Ice.BO.CompanySvc/Companies', 'GET')
        
        if response.status_code == 200:
            print(f"✅ Success! Status Code: {response.status_code}")
            data = response.json()
            if 'value' in data and len(data['value']) > 0:
                company = data['value'][0]
                print(f"Connected to company: {company.get('Company', 'Unknown')}")
                print(f"Company name: {company.get('Name', 'N/A')}")
            else:
                print("Connected successfully but no company data returned")
        else:
            print(f"❌ Request failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing connection: {str(e)}")
        print("Check your .env file configuration and network connectivity")