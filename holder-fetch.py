import os
import sys
import json
import requests
from datetime import datetime

MORALIS_API_KEY = os.getenv('MORALIS_API_KEY', '')
MAX_HOLDERS = 20

def fetch_all_holders(token_address):
    url = f"https://deep-index.moralis.io/api/v2.2/erc20/{token_address}/owners"
    headers = {
        "accept": "application/json",
        "X-API-Key": MORALIS_API_KEY
    }
    
    all_holders = []
    cursor = None
    
    while len(all_holders) < MAX_HOLDERS:
        params = {"chain": "eth", "limit": 100}
        if cursor:
            params['cursor'] = cursor
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        holders = data.get('result', [])
        if not holders:
            break
        
        # Filter fields
        filtered_holders = [{
            'owner_address': h.get('owner_address'),
            'balance': h.get('balance'),
            'balance_formatted': h.get('balance_formatted'),
            'is_contract': h.get('is_contract'),
            'percentage_relative_to_total_supply': h.get('percentage_relative_to_total_supply')
        } for h in holders]
        
        all_holders.extend(filtered_holders)
        
        # Stop if reached max
        if len(all_holders) >= MAX_HOLDERS:
            all_holders = all_holders[:MAX_HOLDERS]
            break
        
        cursor = data.get('cursor')
        if not cursor:
            break
    
    return all_holders

def get_token_metadata(token_address):
    url = f"https://deep-index.moralis.io/api/v2.2/erc20/metadata"
    headers = {
        "accept": "application/json",
        "X-API-Key": MORALIS_API_KEY
    }
    params = {
        "chain": "eth",
        "addresses": [token_address]
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        return data[0] if data else None
    except:
        return None

def save_to_json(token_address, holders_data, metadata=None):
    os.makedirs('./result', exist_ok=True)
    
    output_data = {
        'token_address': token_address,
        'fetched_at': datetime.now().isoformat(),
        'total_holders': len(holders_data),
        'holders': holders_data
    }
    
    if metadata:
        output_data['token_info'] = metadata
    
    file_path = f'./result/{token_address}.json'
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    return file_path

def main():
    if len(sys.argv) != 2:
        print("Usage: python holder-fetch.py <token_address>")
        sys.exit(1)
    
    token_address = sys.argv[1]
    
    if not token_address.startswith('0x') or len(token_address) != 42:
        print("Invalid address")
        sys.exit(1)
    
    if not MORALIS_API_KEY:
        print("Set MORALIS_API_KEY environment variable")
        print("Get free key at: https://moralis.io")
        sys.exit(1)
    
    try:
        metadata = get_token_metadata(token_address)
        holders = fetch_all_holders(token_address)
        file_path = save_to_json(token_address, holders, metadata)
        
        print(f"Fetched {len(holders)} holders")
        print(f"Saved to: {file_path}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()