"""
Kalshi API client for live trading.
Connects via REST + WebSocket, streams prices, places orders.
"""

import os
import json
import asyncio
import hashlib
import hmac
from datetime import datetime
from typing import Dict, List, Optional
import requests
import websockets
from dotenv import load_dotenv

load_dotenv()


class KalshiClient:
    """Kalshi API client for trading."""
    
    def __init__(self):
        self.public_key = os.getenv('KALSHI_PUBLIC_KEY')
        self.private_key = os.getenv('KALSHI_PRIVATE_KEY')
        self.base_url = os.getenv('KALSHI_BASE_URL', 'https://api.kalshi.com')
        self.ws_url = 'wss://api.kalshi.com/v1/events'
        
        if not self.public_key or not self.private_key:
            raise ValueError("KALSHI_PUBLIC_KEY and KALSHI_PRIVATE_KEY required in .env")
        
        self.session = requests.Session()
        self.account_balance = None
    
    def _sign_request(self, method: str, path: str, body: str = '') -> Dict[str, str]:
        """Sign request with HMAC-SHA256."""
        timestamp = str(int(datetime.utcnow().timestamp() * 1000))
        
        # Build message: method + path + body + timestamp
        message = method + path + body + timestamp
        
        # Sign with private key
        signature = hmac.new(
            self.private_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return {
            'Authorization': f'{self.public_key}:{signature}',
            'Kalshi-Timestamp': timestamp
        }
    
    def get_account(self) -> Dict:
        """Get account info and balance."""
        path = '/v1/account'
        headers = self._sign_request('GET', path)
        response = self.session.get(f'{self.base_url}{path}', headers=headers)
        response.raise_for_status()
        data = response.json()
        self.account_balance = data.get('balance_cash', 0)
        return data
    
    def get_markets(self, **filters) -> List[Dict]:
        """Get available markets."""
        path = '/v1/markets'
        headers = self._sign_request('GET', path)
        response = self.session.get(f'{self.base_url}{path}', headers=headers, params=filters)
        response.raise_for_status()
        return response.json().get('markets', [])
    
    def get_market_prices(self, ticker: str) -> Dict:
        """Get live prices for a market."""
        path = f'/v1/markets/{ticker}'
        headers = self._sign_request('GET', path)
        response = self.session.get(f'{self.base_url}{path}', headers=headers)
        response.raise_for_status()
        return response.json()
    
    def create_order(self, ticker: str, side: str, price: float, quantity: int) -> Dict:
        """
        Place an order.
        side: 'Yes' or 'No'
        price: order price (0.0 to 1.0)
        quantity: number of contracts
        """
        path = '/v1/orders'
        body = json.dumps({
            'ticker': ticker,
            'side': side,
            'price': price,
            'quantity': quantity,
            'order_type': 'Limit'
        })
        
        headers = self._sign_request('POST', path, body)
        headers['Content-Type'] = 'application/json'
        
        response = self.session.post(f'{self.base_url}{path}', data=body, headers=headers)
        response.raise_for_status()
        return response.json()
    
    def cancel_order(self, order_id: str) -> Dict:
        """Cancel an open order."""
        path = f'/v1/orders/{order_id}'
        headers = self._sign_request('DELETE', path)
        response = self.session.delete(f'{self.base_url}{path}', headers=headers)
        response.raise_for_status()
        return response.json()
    
    def get_orders(self) -> List[Dict]:
        """Get all open orders."""
        path = '/v1/orders'
        headers = self._sign_request('GET', path)
        response = self.session.get(f'{self.base_url}{path}', headers=headers)
        response.raise_for_status()
        return response.json().get('orders', [])
    
    async def stream_prices(self, tickers: List[str], callback):
        """
        Stream live prices via WebSocket.
        callback(ticker, yes_price, no_price) called on each update.
        """
        try:
            async with websockets.connect(self.ws_url) as ws:
                # Subscribe to market events
                for ticker in tickers:
                    subscribe = {
                        'op': 'subscribe',
                        'args': [f'markets:{ticker}']
                    }
                    await ws.send(json.dumps(subscribe))
                
                # Receive updates
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    
                    if data.get('type') == 'market_update':
                        ticker = data.get('ticker')
                        yes_price = data.get('yes_price')
                        no_price = data.get('no_price')
                        
                        if callback:
                            await callback(ticker, yes_price, no_price)
        
        except Exception as e:
            print(f"WebSocket error: {e}")
