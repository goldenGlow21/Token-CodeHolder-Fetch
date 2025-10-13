# ERC20 Token Data Fetcher

Automated tool to fetch token holder information, contract source code, and bytecode for ERC20 tokens.

## Setup

1. Install dependencies:
```bash
pip install requests python-dotenv
```

2. Configure API keys in `.env`:
```bash
cp .env.example .env
# Edit .env with your API keys
```

**Required API Keys:**
- Moralis API: https://moralis.io
- Etherscan API: https://etherscan.io/myapikey
- Alchemy API: https://www.alchemy.com

3. Add token addresses to `address.json`

## Usage

```bash
python fetcher.py
```

## Output

```
result/
├── holders.csv              # All token holders data
├── sourcecode/
│   └── {address}.sol       # Contract source code
└── bytecode/
    └── {address}.evm       # Contract bytecode
```

**holders.csv format:**
- `token_addr`: Token contract address
- `holder_addr`: Holder wallet address
- `balance`: Token balance
- `rel_to_total`: Holding percentage

## Notes

- Fetches top 20 holders per token
- Rate limited to avoid API restrictions
- Skips contracts without verified source code
