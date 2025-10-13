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

# DMT (Data Migration Tool) Functions
def generate_group_name():
    timestamp = datetime.now().strftime("%d%H%M")  # day + hour + minute = 6 digits
    return f"AI{timestamp}"  # AI + 6 digits = 8 chars total

def execute_dmt(template_name, data_records, company=None):
    username = os.getenv('EPICOR_USERNAME')
    password = os.getenv('EPICOR_PASSWORD')
    instance = os.getenv('EPICOR_INSTANCE')
    
    if not company:
        company = 'SAINC'  # Default company
    
    # Create temporary CSV file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
        if data_records:
            fieldnames = data_records[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data_records)
            temp_file = f.name
    
    # DMT command line call
    dmt_path = "C:\\Epicor\\ERP11.2.400.20Client\\Client\\DMT.exe"
    
    dmt_command = [
        dmt_path,
        "-NoUI",
        "-NoCompleteLog", 
        "-NoErrorInput",
        "-DisableUpdateService",
        "-User", username,
        "-Pass", password,
        "-ConfigValue", instance,
        "-Add",
        "-Import", template_name,
        "-Source", temp_file
    ]
    
    try:
        
        result = subprocess.run(dmt_command, capture_output=True, text=True, timeout=None)
        
        print('DEBUG: DMT result:', result)

        # Clean up temp file
        os.unlink(temp_file)
        
        # Filter out log4net errors but keep other actual errors
        filtered_errors = ""
        if result.stderr:
            lines = result.stderr.split('\n')
            filtered_lines = [line for line in lines if not (
                'log4net:ERROR' in line or 
                'appender named [console]' in line or
                'XmlHierarchyConfigurator' in line
            )]
            filtered_errors = '\n'.join(filtered_lines).strip()
        
        # DMT succeeds if return code is 0, regardless of log4net warnings in stderr
        is_success = result.returncode == 0
        
        return {
            'success': is_success,
            'return_code': result.returncode,
            'output': result.stdout,
            'errors': filtered_errors
        }
        
    except subprocess.TimeoutExpired:
        os.unlink(temp_file)
        return {
            'success': False,
            'return_code': -1,
            'output': '',
            'errors': 'DMT command timed out'
        }
    except FileNotFoundError:
        os.unlink(temp_file)
        return {
            'success': False,
            'return_code': -1,
            'output': '',
            'errors': f'DMT executable not found at: {dmt_path}'
        }
    except Exception as e:
        os.unlink(temp_file)
        return {
            'success': False,
            'return_code': -1,
            'output': '',
            'errors': f'Error executing DMT: {str(e)}'
        }

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

def get_vendor_data(vendor_id, company='SAINC'):
    endpoint = 'Erp.BO.VendorSvc/Vendors'
    
    params = {
        '$filter': f"Company eq '{company}' and VendorID eq '{vendor_id}'",
        '$select': 'VendorNum, TermsCode'
    }
    
    response = epicor_api_request(endpoint, 'GET', company, params=params)

    if response.status_code == 200:
        data = response.json()
        vendor_num = data['value'][0]['VendorNum'] 
        terms_code = data['value'][0]['TermsCode']
        return vendor_num, terms_code

    return None

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