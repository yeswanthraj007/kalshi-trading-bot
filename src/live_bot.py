#!/usr/bin/env python3
"""
Live trading bot for Kalshi.
Auto-executes trades based on model edge.
"""

import asyncio
import json
import sys
from datetime import datetime
from typing import Dict, Optional
from model import TennisMarkovModel, CryptoVolatilityModel, BayesianCalibrator
from kalshi_client import KalshiClient
from backtest import Trade, PaperTradingLog


class LiveTradingBot:
    """Live trading bot with risk management."""
    
    def __init__(self, 
                 kalshi_client: KalshiClient,
                 min_edge_pct: float = 5.0,
                 stake_per_trade: float = 1.0,
                 daily_loss_limit: float = 2.0,
                 position_limit: float = 5.0):
        """
        Initialize bot.
        
        min_edge_pct: minimum edge % to trade (5 = 5 percentage points)
        stake_per_trade: dollars per trade
        daily_loss_limit: max loss per day ($)
        position_limit: max total positions ($)
        """
        self.client = kalshi_client
        self.min_edge_pct = min_edge_pct / 100.0
        self.stake_per_trade = stake_per_trade
        self.daily_loss_limit = daily_loss_limit
        self.position_limit = position_limit
        
        self.log = PaperTradingLog(initial_balance=self.client.account_balance or 10.0)
        self.open_positions = {}  # ticker -> Trade
        self.daily_loss = 0.0
        self.last_reset = datetime.now().date()
        
        # Models
        self.tennis_model = TennisMarkovModel(0.65, 0.68)
        self.crypto_model = CryptoVolatilityModel()
    
    def check_daily_limits(self):
        """Reset daily loss if new day."""
        today = datetime.now().date()
        if today > self.last_reset:
            self.daily_loss = 0.0
            self.last_reset = today
    
    def can_trade(self) -> bool:
        """Check if bot can trade (limits not exceeded)."""
        self.check_daily_limits()
        
        # Check daily loss limit
        if self.daily_loss >= self.daily_loss_limit:
            print(f"⚠️  Daily loss limit reached: ${self.daily_loss:.2f} / ${self.daily_loss_limit:.2f}")
            return False
        
        # Check position limit
        total_position_value = sum(t.stake for t in self.open_positions.values())
        if total_position_value >= self.position_limit:
            print(f"⚠️  Position limit reached: ${total_position_value:.2f} / ${self.position_limit:.2f}")
            return False
        
        return True
    
    def compute_edge(self, fair_value: float, market_price: float) -> float:
        """Compute edge as percentage points."""
        return (fair_value - market_price) * 100
    
    def should_trade(self, edge_pct: float) -> bool:
        """Decide whether to trade based on edge."""
        return edge_pct >= self.min_edge_pct * 100
    
    def place_trade(self, ticker: str, side: str, entry_price: float, fair_value: float, quantity: int):
        """Place a trade on Kalshi."""
        if not self.can_trade():
            print(f"⚠️  Trade blocked: limits exceeded")
            return False
        
        try:
            edge = self.compute_edge(fair_value, entry_price)
            
            if not self.should_trade(edge):
                print(f"⚠️  Trade blocked: edge too small ({edge:.1f}%)")
                return False
            
            # Place order on Kalshi
            order = self.client.create_order(
                ticker=ticker,
                side=side,
                price=entry_price,
                quantity=quantity
            )
            
            # Log trade
            trade = Trade(
                timestamp=datetime.now().isoformat(),
                market=ticker,
                side=side,
                entry_price=entry_price,
                stake=entry_price * quantity,
                fair_value=fair_value,
                edge=edge / 100.0,
                contracts=quantity,
                outcome=None,
                notes=f"Order ID: {order.get('order_id')}"
            )
            
            self.open_positions[ticker] = trade
            
            print(f"✓ Trade placed: {side} {quantity} @ {entry_price:.2f} (edge: {edge:.1f}%)")
            return True
        
        except Exception as e:
            print(f"✗ Trade failed: {e}")
            return False
    
    def settle_position(self, ticker: str, outcome: bool):
        """Settle an open position."""
        if ticker not in self.open_positions:
            return
        
        trade = self.open_positions[ticker]
        trade.outcome = outcome
        
        pnl = trade.stake * (1 / trade.entry_price - 1) if outcome else -trade.stake
        trade.pnl = pnl
        self.daily_loss += pnl if pnl < 0 else 0
        
        self.log.log_trade(trade)
        del self.open_positions[ticker]
        
        status = "WIN" if outcome else "LOSS"
        print(f"{status}: {ticker} {trade.side} | P&L: ${pnl:+.2f}")
    
    def print_status(self):
        """Print current bot status."""
        print("\n" + "="*60)
        print(f"Balance: ${self.log.balance:.2f}")
        print(f"Daily Loss: ${self.daily_loss:.2f} / ${self.daily_loss_limit:.2f}")
        print(f"Open Positions: {len(self.open_positions)}")
        if self.log.trades:
            print(f"Win Rate: {self.log.win_rate():.0%}")
            print(f"Total P&L: ${self.log.total_pnl():+.2f}")
        print("="*60 + "\n")


async def run_bot(dry_run: bool = True):
    """Run the trading bot."""
    try:
        # Initialize client
        client = KalshiClient()
        print("✓ Connected to Kalshi")
        
        # Get account info
        account = client.get_account()
        print(f"✓ Account balance: ${account.get('balance_cash', 0):.2f}")
        
        # Initialize bot
        bot = LiveTradingBot(
            kalshi_client=client,
            min_edge_pct=5.0,
            stake_per_trade=1.0,
            daily_loss_limit=2.0,
            position_limit=5.0
        )
        
        print("\n" + "="*60)
        print("KALSHI LIVE TRADING BOT")
        print(f"Mode: {'DRY RUN (no orders)' if dry_run else 'LIVE'}")
        print("="*60 + "\n")
        
        # Main loop (in real use, this would stream prices and execute)
        print("Bot running. Press Ctrl+C to stop.")
        bot.print_status()
        
        # Keep running
        while True:
            await asyncio.sleep(60)
            bot.print_status()
    
    except KeyboardInterrupt:
        print("\n✓ Bot stopped")
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    # Run in dry-run mode by default (no real orders placed)
    dry_run = '--live' not in sys.argv
    asyncio.run(run_bot(dry_run=dry_run))
