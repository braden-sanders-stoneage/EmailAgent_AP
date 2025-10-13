import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.integrations.epicor.epicor_utils import epicor_api_request
from core.utils.secret_manager import get_secret


def build_epicor_invoice_url(vendor_num, invoice_num):
    server = get_secret('EPICOR_SERVER')
    instance = get_secret('EPICOR_INSTANCE')
    channel_id = get_secret('EPICOR_CHANNEL_ID')
    
    url = (
        f"https://{server}/{instance}/Apps/ERP/Home/#/view/APGO1070/Erp.UI.APInvoiceTracker"
        f"?channelid={channel_id}"
        f"&layerVersion=0"
        f"&baseAppVersion=0"
        f"&company=SAINC"
        f"&site=MfgSys"
        f"&pageId=Details"
        f"&KeyFields.VendorNum={vendor_num}"
        f"&KeyFields.InvoiceNum={invoice_num}"
        f"&pageChanged=true"
    )
    
    return url


def get_invoice_from_epicor(invoice_number, company='SAINC'):
    endpoint = 'BaqSvc/APInvDtl/Data'
    
    params = {
        '$filter': f"APInvHed_InvoiceNum eq '{invoice_number}'"
    }
    
    response = epicor_api_request(endpoint, 'GET', company, params=params)
    
    if response and response.status_code == 200:
        try:
            data = response.json()
            print(f"\n[INVOICE CHECK] Invoice {invoice_number}:")
            print(f"  Full Response: {data}")
            
            if 'value' in data and len(data['value']) > 0:
                print(f"  ✓ Found in Epicor ({len(data['value'])} record(s))")
                
                invoice_data = data['value'][0]
                vendor_num = invoice_data.get('APInvHed_VendorNum')
                
                epicor_url = None
                if vendor_num:
                    epicor_url = build_epicor_invoice_url(vendor_num, invoice_number)
                
                invoice_details = {
                    "VendorName": invoice_data.get('Vendor_Name'),
                    "VendorEmailAddress": invoice_data.get('Vendor_EMailAddress'),
                    "DocInvoiceAmt": invoice_data.get('APInvHed_DocInvoiceAmt'),
                    "DocInvoiceBal": invoice_data.get('APInvHed_DocInvoiceBal'),
                    "PaymentStatus": invoice_data.get('Calculated_PaymentStatus'),
                    "OpenPayable": invoice_data.get('APInvHed_OpenPayable')
                }
                
                return {
                    "found": True,
                    "data": invoice_data,
                    "invoice_details": invoice_details,
                    "epicor_url": epicor_url
                }
            else:
                print(f"  ✗ Not found in Epicor")
                return {
                    "found": False,
                    "data": None,
                    "invoice_details": None,
                    "epicor_url": None
                }
        except Exception as e:
            print(f"  ✗ Error parsing response: {e}")
            return {
                "found": False,
                "data": None,
                "invoice_details": None,
                "epicor_url": None
            }
    else:
        print(f"\n[INVOICE CHECK] Invoice {invoice_number}: API request failed")
        return {
            "found": False,
            "data": None,
            "invoice_details": None,
            "epicor_url": None
        }

