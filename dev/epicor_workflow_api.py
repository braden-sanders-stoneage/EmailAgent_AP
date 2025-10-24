import csv
import json
from datetime import datetime

# Handle imports for both direct execution and module import
try:
    from epicor_integration.epicor_utils import epicor_api_request, generate_group_name, format_date_for_epicor, get_vendor_data
except ModuleNotFoundError:
    from epicor_utils import epicor_api_request, generate_group_name, format_date_for_epicor, get_vendor_data

def build_misc_charges(invoice_num,vendor_id,misc_charges,company):
    
    # Mapping of GL codes to MiscCodes for miscellaneous charges
    GL_TO_MISCCODE_MAPPING = {
        '01-18000-00-000': '1',
        '01-18010-00-000': '2', 
        '01-59000-00-540': '3',
        '02-59000-00-540': '4',
        '03-59000-00-540': '5',
        '04-59000-00-540': '6',
        '01-59100-00-570': '7',
        '02-59100-00-570': '8',
        '03-59100-00-570': '9',
        '04-59100-00-570': '10',
        '01-40000-00-000': '11',
        '02-40000-00-000': '12',
        '03-40000-00-000': '13',
        '04-40000-00-000': '14'
    }

    misc_charges_data = []

    for i,misc_charge in enumerate(misc_charges):
        gl_code = misc_charge['gl_code']
        
        # Skip lines with failed coding
        if gl_code in ['CODING_FAILED', 'UNCODED', '', None]:
            print(f"⚠️  Skipping line with failed/missing GL code: {gl_code} (Tracking: {misc_charge.get('tracking_number', 'Unknown')})")
            continue
            
        # Check if GL code exists in mapping
        if gl_code not in GL_TO_MISCCODE_MAPPING:
            print(f"❌ Unknown GL code '{gl_code}' not found in mapping (Tracking: {misc_charge.get('tracking_number', 'Unknown')})")
            continue
            
        misc_charges_data.append(
        {
            'Company': company,
            'InvoiceNum': invoice_num,
            'MscNum': i+1,
            'VendorNumVendorID': vendor_id,
            'MiscCode': GL_TO_MISCCODE_MAPPING[gl_code],
            'MiscAmt': float(misc_charge['total_amount']),
            'Description': 'Placeholder description'    
        }
    )

    print(f"Misc charges created: {invoice_num}")

    return misc_charges_data

def build_standard_lines(invoice_num,vendor_id,standard_lines,company):
    
    print(f"Building standard lines: {invoice_num}")

    standard_lines_data = []
    
    for i,standard_line in enumerate(standard_lines):
        standard_lines_data.append(
            {
                'Company': company,
                'InvoiceNum': invoice_num,
                'InvoiceLine': i+1,
                'PartNum': '',
                'Description': 'promo' if standard_line['gl_code'] == '01-60748-00-630' else 'Temporary SAINC/SATX/SAOH->SAFR',
                'VendorNumVendorID': vendor_id,
                'DocUnitCost': abs(float(standard_line['total_amount'])),
                'ScrVendorQty': -1 if float(standard_line['total_amount']) < 0 else 1,
            }
        )

    print(f"Standard lines created: {invoice_num}")

    return standard_lines_data

def build_invoice_data(file_path):

    print(f"Building invoice data: {file_path}")

    # GL codes that should be standard invoice lines instead of misc charges
    STANDARD_LINE_GL_CODES = ['01-60748-00-630', '01-18020-00-000']

    # Read and parse the coded invoice CSV file
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        invoice_data = list(reader)
    
    invoice_num = invoice_data[0]['invoice_number'][:50]
    vendor_id = invoice_data[0]['vendor_code']
    invoice_date = invoice_data[0]['invoice_date']
    company = 'SAINC'

    grouped_invoice_data = []

    # Group invoice lines by GL code
    gl_code_groups = {}
    for invoice in invoice_data:
        gl_code = invoice['gl_account_code']
        if gl_code not in gl_code_groups:
            gl_code_groups[gl_code] = []
        gl_code_groups[gl_code].append(invoice)
    
    # Convert grouped data to list format
    for gl_code, invoices in gl_code_groups.items():
        grouped_invoice = {
            'gl_code': gl_code,
            'total_amount': round(sum(float(inv['billed_charge']) for inv in invoices), 2),
        }
        grouped_invoice_data.append(grouped_invoice)

    # Sort grouped invoice data into standard lines and misc charges

    standard_lines = []
    misc_charges = []

    for line in grouped_invoice_data:
        
        if line['gl_code'] in STANDARD_LINE_GL_CODES:
            standard_lines.append(line)
        else:
            misc_charges.append(line)

    misc_charges_data = build_misc_charges(invoice_num,vendor_id,misc_charges,company)
    standard_lines_data = build_standard_lines(invoice_num,vendor_id,standard_lines,company)

    vendor_data = get_vendor_data(vendor_id, company)
    if vendor_data is None:
        print(f"❌ Could not find vendor data for vendor ID: {vendor_id}")
        return None
    vendor_num, terms_code = vendor_data

    final_invoice_data = {
        'company': company,
        'misc_charges_data': misc_charges_data,
        'standard_lines_data': standard_lines_data,
        'invoice_num': invoice_num,
        'vendor_num': vendor_num,
        'vendor_id': vendor_id,
        'terms_code': terms_code,
        'invoice_date': invoice_date,
        'invoice_sum': round(sum(float(line['DocUnitCost']) for line in standard_lines_data) + sum(float(line['MiscAmt']) for line in misc_charges_data), 2)
    }

    print(f'Invoice data created: {invoice_num}')

    return final_invoice_data

def create_ap_invoice_group(company):


    group_id = generate_group_name()

    print(f"Creating invoice group: {group_id}")

    # Get default values from Epicor

    invoice_group_defaults_endpoint = 'Erp.BO.APInvGrpSvc/GetNewAPInvGrpNoLock'

    invoice_group_defaults_payload = {
        "ds": {
            "APInvGrp": [
            ]
        }
    }

    response = epicor_api_request(invoice_group_defaults_endpoint, 'POST', company, invoice_group_defaults_payload)

    # Build update payload

    invoice_group_endpoint = 'Erp.BO.APInvGrpSvc/Update'

    invoice_group_payload = response.json()['parameters']
    invoice_group_payload['ds']['APInvGrp'][0]['GroupID'] = group_id
    invoice_group_payload['ds']['APInvGrp'][0].pop('SysRevID', None)
    invoice_group_payload['ds']['APInvGrp'][0].pop('SysReowID', None)

    # Create Invoice Group
    
    response = epicor_api_request(invoice_group_endpoint, 'POST', company, invoice_group_payload)
    
    if response.status_code == 200:
        print(f"✅ Invoice group '{group_id}' created successfully!")
        return group_id
    elif "duplicate" in response.json()['ErrorMessage'].lower():
        print(f"⚠️ Invoice group '{group_id}' already exists in Epicor - skipping")
        return group_id
    else:
        print(f"❌ Failed to create invoice group: {response.text}")
        return None

def create_ap_invoice_header(invoice_num, invoice_date, invoice_sum, group_id, company, vendor_id, terms_code):
  
    print(f"Creating invoice header: {invoice_num}")
    
    # Get default values from Epicor

    invoice_header_defaults_endpoint = 'Erp.BO.APInvoiceSvc/GetNewAPInvHedInvoice'

    invoice_header_defaults_payload = {
        'cGroupID' : group_id,
        'ds' : {}
    }

    response = epicor_api_request(invoice_header_defaults_endpoint, 'POST', company, invoice_header_defaults_payload)

    # Build update payload

    invoice_header_endpoint = 'Erp.BO.APInvoiceSvc/Update'

    invoice_header_payload = response.json()['parameters']

    invoice_header_payload['ds']['APInvHed'][0]['InvoiceNum'] = invoice_num
    invoice_header_payload['ds']['APInvHed'][0]['InvoiceDate'] = format_date_for_epicor(invoice_date)
    invoice_header_payload['ds']['APInvHed'][0]['ScrDocInvoiceVendorAmt'] = invoice_sum
    invoice_header_payload['ds']['APInvHed'][0]['VendorNumVendorID'] = vendor_id
    invoice_header_payload['ds']['APInvHed'][0]['TermsCode'] = terms_code
    invoice_header_payload['ds']['APInvHed'][0]['Description'] = 'This invoice was generated automatically by a brilliant AI assistant.'

    # Create AP Invoice Header
    response = epicor_api_request(invoice_header_endpoint, 'POST', company, invoice_header_payload)
    
    if response.status_code == 200:
        print(f"✅ Invoice header '{invoice_num}' created successfully!")
    elif "duplicate" in response.json()['ErrorMessage'].lower():
        print(f"⚠️ Invoice '{invoice_num}' already exists in Epicor - skipping")
    else:
        print(f"❌ Failed to create invoice header: {response.text}")

def create_ap_invoice_lines(group_id,invoice_num,vendor_num,standard_lines_data,company):

    # Get default values from Epicor

    invoice_lines_defaults_endpoint = 'Erp.BO.APInvoiceSvc/GetNewAPInvDtlMiscellaneous'

    invoice_lines_defaults_payload = {
        'cInvoiceNum' : invoice_num,
        'iVendorNum' : vendor_num,
        'ds' : {}
    }

    response = epicor_api_request(invoice_lines_defaults_endpoint, 'POST', company, invoice_lines_defaults_payload)

    # Build update payload

    invoice_lines_endpoint = 'Erp.BO.APInvoiceSvc/UpdateMaster'

    invoice_lines_payload = response.json()['parameters']
    
    invoice_lines_payload['cGroupID'] = group_id
    invoice_lines_payload['cTableName'] = 'APInvDtl'
    invoice_lines_payload['runChkBankRef'] = False
    invoice_lines_payload['runChkCPay'] = False
    invoice_lines_payload['runChkRevChrg'] = False
    invoice_lines_payload['suppressUserPrompts'] = False

    for line in standard_lines_data:
        
        invoice_lines_payload['ds']['APInvDtl'][0]['InvoiceLine'] = line['InvoiceLine']
        invoice_lines_payload['ds']['APInvDtl'][0]['DocUnitCost'] = line['DocUnitCost'] 
        invoice_lines_payload['ds']['APInvDtl'][0]['ScrVendorQty'] = line['ScrVendorQty']
        invoice_lines_payload['ds']['APInvDtl'][0]['Description'] = line['Description']

        response = epicor_api_request(invoice_lines_endpoint, 'POST', company, invoice_lines_payload)

        if response.status_code == 200:
            print(f"✅ Invoice {invoice_num} line {line['InvoiceLine']} created successfully!")
        elif "duplicate" in response.json()['ErrorMessage'].lower():
            print(f"⚠️ Invoice {invoice_num} line {line['InvoiceLine']} already exists in Epicor - skipping")
        else:
            print(f"❌ Failed to create invoice line: {response.text}")

def create_ap_invoice_misc_charges(group_id,invoice_num,vendor_num,misc_charges_data,company):
    
    invoice_lines_defaults_endpoint = 'Erp.BO.APInvoiceSvc/GetNewHdrCharge'

    invoice_lines_defaults_payload = {
        'cInvoiceNum' : invoice_num,
        'iVendorNum' : vendor_num,
        'lcFlag' : False,
        'ds' : {}
    }

    response = epicor_api_request(invoice_lines_defaults_endpoint, 'POST', company, invoice_lines_defaults_payload)

    # Build update payload

    invoice_lines_endpoint = 'Erp.BO.APInvoiceSvc/UpdateMaster'

    invoice_lines_payload = response.json()['parameters']

    invoice_lines_payload['cGroupID'] = group_id
    invoice_lines_payload['cTableName'] = 'APIHAPInvMsc'
    invoice_lines_payload['runChkBankRef'] = False
    invoice_lines_payload['runChkCPay'] = False
    invoice_lines_payload['runChkRevChrg'] = False
    invoice_lines_payload['suppressUserPrompts'] = False

    for line in misc_charges_data:
        
        invoice_lines_payload['ds']['APIHAPInvMsc'][0]['MiscCode'] = line['MiscCode']
        invoice_lines_payload['ds']['APIHAPInvMsc'][0]['ScrMiscAmt'] = line['MiscAmt']
        invoice_lines_payload['ds']['APIHAPInvMsc'][0]['ScrDocMiscAmt'] = line['MiscAmt']

        response = epicor_api_request(invoice_lines_endpoint, 'POST', company, invoice_lines_payload)
    
        if response.status_code == 200:
            print(f"✅ Invoice {invoice_num} misc charge {line['MscNum']} created successfully!")
        elif "duplicate" in response.json()['ErrorMessage'].lower():
            print(f"⚠️ Invoice {invoice_num} misc charge {line['MscNum']} already exists in Epicor - skipping")
        else:
            print(f"❌ Failed to create invoice misc charge: {response.text}")

def upload_to_epicor(file_path):
    """Master function to orchestrate Epicor upload workflow"""
    
    # Build invoice data
    invoice_data = build_invoice_data(file_path)
    
    if invoice_data is None:
        print("❌ Failed to build invoice data. Aborting upload.")
        return False
    
    # Create invoice group
    group_id = create_ap_invoice_group(invoice_data['company'])

    # Create invoice header
    create_ap_invoice_header(invoice_data['invoice_num'], invoice_data['invoice_date'], invoice_data['invoice_sum'], group_id, invoice_data['company'], invoice_data['vendor_id'], invoice_data['terms_code'])

    # Create invoice lines
    if invoice_data['standard_lines_data']:
        create_ap_invoice_lines(group_id,invoice_data['invoice_num'],invoice_data['vendor_num'],invoice_data['standard_lines_data'],invoice_data['company'])

    # Create invoice misc charges
    if invoice_data['misc_charges_data']:
        create_ap_invoice_misc_charges(group_id,invoice_data['invoice_num'],invoice_data['vendor_num'],invoice_data['misc_charges_data'],invoice_data['company'])
    
    # Return success if we made it this far
    return True

if __name__ == "__main__":
    
    # Test the function with a sample file
    upload_to_epicor(r'invoice_coding\output\coded_invoice_812846305_20250801_092601.csv')