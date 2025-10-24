import sys
import os
from typing import List, Dict, Optional
from fuzzywuzzy import fuzz

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.integrations.epicor.client import epicor_api_request


def get_all_vendors(company='SAINC') -> Optional[List[Dict]]:
    endpoint = 'Erp.BO.VendorSvc/Vendors'
    
    params = {
        '$filter': f"Company eq '{company}'",
        '$select': 'VendorID,Name,VendorNum',
        '$top': 10000
    }
    
    print(f"\nFetching all vendors from Epicor for company: {company}")
    
    response = epicor_api_request(endpoint, 'GET', company, params=params, instance_override='KineticLive')
    
    if response and response.status_code == 200:
        data = response.json()
        vendors = data.get('value', [])
        print(f"✅ Retrieved {len(vendors)} vendors from Epicor")
        return vendors
    else:
        print(f"❌ Failed to retrieve vendors from Epicor")
        return None


def fuzzy_match_vendor(extracted_name: str, vendor_list: List[Dict]) -> List[Dict]:
    if not extracted_name or not vendor_list:
        print("⚠️  No extracted name or empty vendor list")
        return []
    
    print(f"\n🎯 Fuzzy matching vendor name: '{extracted_name}'")
    print(f"   Against {len(vendor_list)} vendors in Epicor")
    
    matches = []
    
    for vendor in vendor_list:
        vendor_id = vendor.get('VendorID', '')
        vendor_name = vendor.get('Name', '')
        vendor_num = vendor.get('VendorNum', '')
        
        if not vendor_name:
            continue
        
        ratio = fuzz.ratio(extracted_name.lower(), vendor_name.lower())
        partial_ratio = fuzz.partial_ratio(extracted_name.lower(), vendor_name.lower())
        token_sort_ratio = fuzz.token_sort_ratio(extracted_name.lower(), vendor_name.lower())
        
        confidence = max(ratio, partial_ratio, token_sort_ratio)
        
        matches.append({
            'vendor_id': vendor_id,
            'vendor_name': vendor_name,
            'vendor_num': vendor_num,
            'confidence': confidence,
            '_debug': {
                'ratio': ratio,
                'partial_ratio': partial_ratio,
                'token_sort_ratio': token_sort_ratio
            }
        })
    
    matches.sort(key=lambda x: x['confidence'], reverse=True)
    
    top_5 = matches[:5]
    
    print(f"\n📊 Top 5 Vendor Matches:")
    for i, match in enumerate(top_5, 1):
        print(f"   {i}. {match['vendor_name']} (ID: {match['vendor_id']})")
        print(f"      Confidence: {match['confidence']}%")
        print(f"      Debug - Ratio: {match['_debug']['ratio']}, Partial: {match['_debug']['partial_ratio']}, Token Sort: {match['_debug']['token_sort_ratio']}")
    
    if top_5:
        print(f"\n✅ Best match: {top_5[0]['vendor_name']} ({top_5[0]['confidence']}% confidence)")
    else:
        print(f"\n⚠️  No matches found for '{extracted_name}'")
    
    return top_5


def match_vendor_from_invoice(extracted_name: str, company='SAINC') -> List[Dict]:
    vendors = get_all_vendors(company)
    
    if not vendors:
        return []
    
    return fuzzy_match_vendor(extracted_name, vendors)

