#!/usr/bin/env python3
"""
Test connection to Kalshi API.
Run this after creating your .env file.
"""

import sys
from kalshi_client import KalshiClient


def main():
    print("\n" + "="*60)
    print("KALSHI API CONNECTION TEST")
    print("="*60 + "\n")
    
    try:
        print("1. Initializing client...")
        client = KalshiClient()
        print("   ✓ Client created")
        
        print("\n2. Fetching account info...")
        account = client.get_account()
        print(f"   ✓ Connected to Kalshi")
        print(f"   ✓ Account ID: {account.get('account_id', 'N/A')}")
        print(f"   ✓ Balance: ${account.get('balance_cash', 0):.2f}")
        
        print("\n3. Fetching markets...")
        markets = client.get_markets(limit=3)
        print(f"   ✓ Found {len(markets)} markets (showing first 3):")
        for market in markets[:3]:
            print(f"      - {market.get('ticker')}: {market.get('title')}")
        
        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED - Ready to trade!")
        print("="*60)
        print("\nNext step: python live_bot.py\n")
        
        return 0
    
    except ValueError as e:
        print(f"\n✗ Configuration error: {e}")
        print("\nMake sure you have a .env file with:")
        print("  KALSHI_PUBLIC_KEY=...")
        print("  KALSHI_PRIVATE_KEY=...")
        return 1
    
    except Exception as e:
        print(f"\n✗ Connection error: {e}")
        print("\nPossible reasons:")
        print("  - Invalid API keys")
        print("  - Kalshi API is down")
        print("  - Network connection issue")
        print("  - Private key format is wrong")
        return 1


if __name__ == '__main__':
    sys.exit(main())
