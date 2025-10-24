import sys
import os
from typing import Dict, Any, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.integrations.epicor.client import epicor_api_request, format_date_for_epicor, get_vendor_data, generate_group_name
from core.integrations.epicor.invoices import build_epicor_invoice_url


def create_ap_invoice_group(company='SAINC'):
    group_id = generate_group_name()
    
    print(f"\n📦 Creating invoice group: {group_id}")
    
    invoice_group_defaults_endpoint = 'Erp.BO.APInvGrpSvc/GetNewAPInvGrpNoLock'
    
    invoice_group_defaults_payload = {
        "ds": {
            "APInvGrp": []
        }
    }
    
    response = epicor_api_request(invoice_group_defaults_endpoint, 'POST', company, invoice_group_defaults_payload)
    
    if not response or response.status_code != 200:
        print(f"❌ Failed to get invoice group defaults")
        return None
    
    invoice_group_endpoint = 'Erp.BO.APInvGrpSvc/Update'
    
    invoice_group_payload = response.json()['parameters']
    invoice_group_payload['ds']['APInvGrp'][0]['GroupID'] = group_id
    invoice_group_payload['ds']['APInvGrp'][0].pop('SysRevID', None)
    invoice_group_payload['ds']['APInvGrp'][0].pop('SysRowID', None)
    
    response = epicor_api_request(invoice_group_endpoint, 'POST', company, invoice_group_payload)
    
    if response.status_code == 200:
        print(f"✅ Invoice group '{group_id}' created successfully!")
        return group_id
    elif response.json() and "duplicate" in response.json().get('ErrorMessage', '').lower():
        print(f"⚠️  Invoice group '{group_id}' already exists - using existing")
        return group_id
    else:
        print(f"❌ Failed to create invoice group: {response.text}")
        return None


def create_ap_invoice_header(invoice_num, invoice_date, invoice_sum, group_id, company, vendor_id, terms_code):
    print(f"\n📋 Creating invoice header: {invoice_num}")
    
    invoice_header_defaults_endpoint = 'Erp.BO.APInvoiceSvc/GetNewAPInvHedInvoice'
    
    invoice_header_defaults_payload = {
        'cGroupID': group_id,
        'ds': {}
    }
    
    response = epicor_api_request(invoice_header_defaults_endpoint, 'POST', company, invoice_header_defaults_payload)
    
    if not response or response.status_code != 200:
        print(f"❌ Failed to get invoice header defaults")
        return False
    
    invoice_header_endpoint = 'Erp.BO.APInvoiceSvc/Update'
    
    invoice_header_payload = response.json()['parameters']
    
    invoice_header_payload['ds']['APInvHed'][0]['InvoiceNum'] = invoice_num[:50]
    invoice_header_payload['ds']['APInvHed'][0]['InvoiceDate'] = format_date_for_epicor(invoice_date)
    invoice_header_payload['ds']['APInvHed'][0]['ScrDocInvoiceVendorAmt'] = float(invoice_sum)
    invoice_header_payload['ds']['APInvHed'][0]['VendorNumVendorID'] = vendor_id
    invoice_header_payload['ds']['APInvHed'][0]['TermsCode'] = terms_code
    invoice_header_payload['ds']['APInvHed'][0]['Description'] = 'This invoice was generated automatically by a brilliant AI assistant.'
    
    response = epicor_api_request(invoice_header_endpoint, 'POST', company, invoice_header_payload)
    
    if response.status_code == 200:
        print(f"✅ Invoice header '{invoice_num}' created successfully!")
        return True
    elif response.json() and "duplicate" in response.json().get('ErrorMessage', '').lower():
        print(f"⚠️  Invoice '{invoice_num}' already exists in Epicor")
        return True
    else:
        print(f"❌ Failed to create invoice header: {response.text}")
        return False


def create_ap_invoice_lines(group_id, invoice_num, vendor_num, line_items, company='SAINC'):
    print(f"\n📝 Creating {len(line_items)} invoice line(s)...")
    
    invoice_lines_defaults_endpoint = 'Erp.BO.APInvoiceSvc/GetNewAPInvDtlMiscellaneous'
    
    invoice_lines_defaults_payload = {
        'cInvoiceNum': invoice_num,
        'iVendorNum': vendor_num,
        'ds': {}
    }
    
    response = epicor_api_request(invoice_lines_defaults_endpoint, 'POST', company, invoice_lines_defaults_payload)
    
    if not response or response.status_code != 200:
        print(f"❌ Failed to get invoice line defaults")
        return False
    
    invoice_lines_endpoint = 'Erp.BO.APInvoiceSvc/UpdateMaster'
    
    invoice_lines_payload = response.json()['parameters']
    
    invoice_lines_payload['cGroupID'] = group_id
    invoice_lines_payload['cTableName'] = 'APInvDtl'
    invoice_lines_payload['runChkBankRef'] = False
    invoice_lines_payload['runChkCPay'] = False
    invoice_lines_payload['runChkRevChrg'] = False
    invoice_lines_payload['suppressUserPrompts'] = False
    
    success_count = 0
    
    for i, line in enumerate(line_items, 1):
        invoice_lines_payload['ds']['APInvDtl'][0]['InvoiceLine'] = i
        invoice_lines_payload['ds']['APInvDtl'][0]['PartNum'] = line.get('part_number', '') or ''
        invoice_lines_payload['ds']['APInvDtl'][0]['Description'] = line.get('description', '')
        invoice_lines_payload['ds']['APInvDtl'][0]['ScrVendorQty'] = float(line.get('quantity', 1))
        invoice_lines_payload['ds']['APInvDtl'][0]['DocUnitCost'] = float(line.get('unit_price', 0))
        
        line_total = line.get('line_total')
        if line_total:
            invoice_lines_payload['ds']['APInvDtl'][0]['ScrDocExtCost'] = float(line_total)
        else:
            calculated_total = float(line.get('quantity', 1)) * float(line.get('unit_price', 0))
            invoice_lines_payload['ds']['APInvDtl'][0]['ScrDocExtCost'] = calculated_total
        
        response = epicor_api_request(invoice_lines_endpoint, 'POST', company, invoice_lines_payload)
        
        if response.status_code == 200:
            part_info = f"[{line.get('part_number')}] " if line.get('part_number') else ""
            print(f"   ✅ Line {i}: {part_info}{line.get('description', '')[:50]}")
            success_count += 1
        elif response.json() and "duplicate" in response.json().get('ErrorMessage', '').lower():
            print(f"   ⚠️  Line {i} already exists - skipping")
            success_count += 1
        else:
            print(f"   ❌ Failed to create line {i}: {response.text[:100]}")
    
    print(f"\n✅ Created {success_count}/{len(line_items)} invoice lines")
    return success_count > 0


def create_invoice_in_epicor(invoice_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        company = invoice_data.get('company', 'SAINC')
        vendor_id = invoice_data.get('vendor_id')
        invoice_num = invoice_data.get('invoice_num')
        invoice_date = invoice_data.get('invoice_date')
        invoice_total = invoice_data.get('invoice_total')
        line_items = invoice_data.get('line_items', [])
        
        if not all([vendor_id, invoice_num, invoice_date, invoice_total]):
            return {
                'success': False,
                'error': 'Missing required fields: vendor_id, invoice_num, invoice_date, or invoice_total'
            }
        
        print(f"\n{'='*80}")
        print(f"🚀 Starting Invoice Import to Epicor")
        print(f"{'='*80}")
        print(f"Invoice Number: {invoice_num}")
        print(f"Vendor ID: {vendor_id}")
        print(f"Date: {invoice_date}")
        print(f"Total: ${invoice_total}")
        print(f"Line Items: {len(line_items)}")
        
        vendor_data = get_vendor_data(vendor_id, company)
        if vendor_data is None:
            return {
                'success': False,
                'error': f"Vendor '{vendor_id}' not found in Epicor"
            }
        
        vendor_num, terms_code = vendor_data
        print(f"✅ Vendor found - Vendor Num: {vendor_num}, Terms: {terms_code}")
        
        group_id = create_ap_invoice_group(company)
        if not group_id:
            return {
                'success': False,
                'error': 'Failed to create invoice group'
            }
        
        header_success = create_ap_invoice_header(
            invoice_num, invoice_date, invoice_total,
            group_id, company, vendor_id, terms_code
        )
        
        if not header_success:
            return {
                'success': False,
                'error': 'Failed to create invoice header'
            }
        
        if line_items:
            lines_success = create_ap_invoice_lines(
                group_id, invoice_num, vendor_num, line_items, company
            )
            
            if not lines_success:
                print(f"⚠️  Warning: Invoice header created but some lines failed")
        
        epicor_url = build_epicor_invoice_url(vendor_num, invoice_num)
        
        print(f"\n{'='*80}")
        print(f"✅ Invoice Import Complete!")
        print(f"{'='*80}")
        print(f"Epicor URL: {epicor_url}")
        
        return {
            'success': True,
            'epicor_url': epicor_url,
            'invoice_num': invoice_num,
            'vendor_num': vendor_num
        }
    
    except Exception as e:
        print(f"\n❌ Error creating invoice in Epicor: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }

