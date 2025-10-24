import os
import sys
import json
import csv
import requests
from datetime import datetime
import time
import argparse
from dotenv import load_dotenv

load_dotenv()

MORALIS_API_KEY = os.getenv('MORALIS_API_KEY')
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')
ALCHEMY_API_KEY = os.getenv('ALCHEMY_API_KEY')
MAX_HOLDERS = 20
ADDRESS_FILE = './address.json'

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

        filtered_holders = [{
            'owner_address': h.get('owner_address'),
            'balance_formatted': h.get('balance_formatted'),
            'percentage_relative_to_total_supply': h.get('percentage_relative_to_total_supply')
        } for h in holders]

        all_holders.extend(filtered_holders)

        if len(all_holders) >= MAX_HOLDERS:
            all_holders = all_holders[:MAX_HOLDERS]
            break

        cursor = data.get('cursor')
        if not cursor:
            break

    return all_holders

def fetch_source_code(contract_address):
    url = "https://api.etherscan.io/v2/api"
    params = {
        "chainid": "1",
        "module": "contract",
        "action": "getsourcecode",
        "address": contract_address,
        "apikey": ETHERSCAN_API_KEY
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data['status'] == '1' and data['result'] and len(data['result']) > 0:
            source_code = data['result'][0].get('SourceCode', '')
            if source_code and source_code.strip():
                return source_code
        return None
    except Exception as e:
        print(f"  Error fetching source code: {str(e)}")
        return None

def fetch_bytecode(contract_address):
    url = f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_getCode",
        "params": [contract_address, "latest"]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        if 'result' in data:
            return data['result']
        return None
    except Exception as e:
        print(f"  Error fetching bytecode: {str(e)}")
        return None

def save_holders_csv(token_address, holders_data):
    os.makedirs('./result', exist_ok=True)
    file_path = './result/holders.csv'

    file_exists = os.path.exists(file_path)

    with open(file_path, 'a', encoding='utf-8', newline='') as f:
        if holders_data:
            writer = csv.DictWriter(f, fieldnames=['token_addr', 'holder_addr', 'balance', 'rel_to_total'])

            if not file_exists:
                writer.writeheader()

            for holder in holders_data:
                holder_row = {
                    'token_addr': token_address,
                    'holder_addr': holder['owner_address'],
                    'balance': holder['balance_formatted'],
                    'rel_to_total': holder['percentage_relative_to_total_supply']
                }
                writer.writerow(holder_row)

    return file_path

def save_source_code(token_address, source_code):
    if not source_code:
        return None

    dir_path = f'./result/sourcecode'
    os.makedirs(dir_path, exist_ok=True)
    file_path = f'{dir_path}/{token_address}.sol'

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(source_code)

    return file_path

def save_bytecode(token_address, bytecode):
    if not bytecode:
        return None

    dir_path = f'./result/bytecode'
    os.makedirs(dir_path, exist_ok=True)
    file_path = f'{dir_path}/{token_address}.evm'

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(bytecode)

    return file_path

def load_addresses():
    if not os.path.exists(ADDRESS_FILE):
        print(f"Error: {ADDRESS_FILE} not found")
        sys.exit(1)
    
    with open(ADDRESS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return list(data.keys())

def parse_args():
    parser = argparse.ArgumentParser(
        description='Fetch Ethereum token data (holders, bytecode, sourcecode)',
        usage='python fetcher.py [options]'
    )
    parser.add_argument('-H', '--holders', action='store_true',
                        help='Fetch holders data')
    parser.add_argument('-b', '--bytecode', action='store_true',
                        help='Fetch bytecode')
    parser.add_argument('-s', '--sourcecode', action='store_true',
                        help='Fetch source code')

    args = parser.parse_args()

    # If no options specified, fetch everything
    if not (args.holders or args.bytecode or args.sourcecode):
        args.holders = True
        args.bytecode = True
        args.sourcecode = True

    return args

def get_last_collected_holder_address():
    """Get the last token address that was collected in holders.csv"""
    csv_path = './result/holders.csv'

    if not os.path.exists(csv_path):
        return None

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Read all lines and get the last one
            lines = f.readlines()
            if len(lines) <= 1:  # Only header or empty
                return None

            # Parse the last line
            last_line = lines[-1].strip()
            if last_line:
                # CSV format: token_addr,holder_addr,balance,rel_to_total
                token_addr = last_line.split(',')[0]
                return token_addr
    except Exception as e:
        print(f"Warning: Error reading holders.csv: {str(e)}")

    return None

def get_collected_addresses(args):
    collected = set()

    if args.bytecode and os.path.exists('./result/bytecode'):
        collected.update(f.replace('.evm', '') for f in os.listdir('./result/bytecode') if f.endswith('.evm'))

    if args.sourcecode and os.path.exists('./result/sourcecode'):
        collected.update(f.replace('.sol', '') for f in os.listdir('./result/sourcecode') if f.endswith('.sol'))

    return collected

def main():
    args = parse_args()

    # Validate API keys based on what's being fetched
    if args.holders and not MORALIS_API_KEY:
        print("Error: MORALIS_API_KEY not set (required for holders)")
        sys.exit(1)
    if args.sourcecode and not ETHERSCAN_API_KEY:
        print("Error: ETHERSCAN_API_KEY not set (required for sourcecode)")
        sys.exit(1)
    if args.bytecode and not ALCHEMY_API_KEY:
        print("Error: ALCHEMY_API_KEY not set (required for bytecode)")
        sys.exit(1)

    addresses = load_addresses()

    # Skip already collected addresses for bytecode/sourcecode
    collected = get_collected_addresses(args)
    if collected:
        addresses = [addr for addr in addresses if addr not in collected]
        print(f"Skipping {len(collected)} already collected addresses (bytecode/sourcecode)")

    # For holders, resume from the last collected address
    if args.holders:
        last_holder_addr = get_last_collected_holder_address()
        if last_holder_addr:
            try:
                last_idx = addresses.index(last_holder_addr)
                # Skip all addresses up to and including the last collected one
                addresses = addresses[last_idx + 1:]
                print(f"Resuming holders collection after: {last_holder_addr}")
            except ValueError:
                # Last collected address not in current list, start from beginning
                print(f"Last collected address {last_holder_addr} not found in address list")

    total = len(addresses)

    # Display what will be fetched
    fetch_list = []
    if args.holders:
        fetch_list.append('holders')
    if args.bytecode:
        fetch_list.append('bytecode')
    if args.sourcecode:
        fetch_list.append('sourcecode')

    print(f"Found {total} tokens to process")
    print(f"Fetching: {', '.join(fetch_list)}\n")

    for idx, token_address in enumerate(addresses, 1):
        try:
            print(f"[{idx}/{total}] Processing {token_address}")

            # Fetch holders data
            if args.holders:
                holders = fetch_all_holders(token_address)
                save_holders_csv(token_address, holders)
                print(f"  Saved {len(holders)} holders")

            # Fetch source code
            if args.sourcecode:
                source_code = fetch_source_code(token_address)
                if source_code:
                    save_source_code(token_address, source_code)
                    print(f"  Saved source code")
                else:
                    print(f"  No source code available")

            # Fetch bytecode
            if args.bytecode:
                bytecode = fetch_bytecode(token_address)
                if bytecode:
                    save_bytecode(token_address, bytecode)
                    print(f"  Saved bytecode")
                else:
                    print(f"  No bytecode available")

            print()

            # Rate limiting
            if idx < total:
                time.sleep(0.5)

        except Exception as e:
            print(f"  Error: {str(e)}\n")
            continue

    print(f"Completed: {total} tokens processed")

if __name__ == '__main__':
    main()
