"""
Backtester and paper trading system.
Simulates trading strategy on historical or live data.
Logs all trades and computes calibration metrics.
"""

import json
import csv
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Tuple
from model import TennisMarkovModel, CryptoVolatilityModel, BayesianCalibrator


@dataclass
class Trade:
    """Record of a single trade."""
    timestamp: str
    market: str
    side: str  # 'Yes' or 'No' (or player name)
    entry_price: float  # Cost per contract
    stake: float  # Amount wagered
    fair_value: float  # Model's estimate
    edge: float  # fair_value - entry_price
    contracts: float  # stake / entry_price
    outcome: bool  # True if won
    exit_price: float = None  # For paper trades that close early
    pnl: float = None  # Realized P&L
    notes: str = ""


class PaperTradingLog:
    """Tracks all trades and computes statistics."""
    
    def __init__(self, initial_balance: float = 10.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.trades: List[Trade] = []
        self.max_balance = initial_balance
    
    def log_trade(self, trade: Trade):
        """Record a trade."""
        self.trades.append(trade)
        
        if trade.outcome:
            pnl = trade.stake * (1 / trade.entry_price - 1)
        else:
            pnl = -trade.stake
        
        trade.pnl = pnl
        self.balance += pnl
        self.max_balance = max(self.max_balance, self.balance)
    
    def win_rate(self) -> float:
        """P(trade wins)."""
        if not self.trades:
            return 0.0
        wins = sum(1 for t in self.trades if t.outcome)
        return wins / len(self.trades)
    
    def avg_edge(self) -> float:
        """Average edge per trade."""
        if not self.trades:
            return 0.0
        return sum(t.edge for t in self.trades) / len(self.trades)
    
    def expected_value(self) -> float:
        """Average P&L per trade."""
        if not self.trades:
            return 0.0
        return sum(t.pnl for t in self.trades) / len(self.trades)
    
    def total_pnl(self) -> float:
        """Total profit/loss."""
        return self.balance - self.initial_balance
    
    def return_pct(self) -> float:
        """Return as percentage."""
        if self.initial_balance == 0:
            return 0.0
        return (self.balance - self.initial_balance) / self.initial_balance * 100
    
    def calibration(self, bucket_size: float = 0.05) -> Dict[Tuple[float, float], Tuple[int, int]]:
        """
        Calibration: group trades by fair_value, compute actual win rate.
        
        Returns: {(bucket_low, bucket_high): (wins, total)}
        """
        buckets = {}
        for trade in self.trades:
            # Round down to nearest bucket
            low = int(trade.fair_value / bucket_size) * bucket_size
            high = low + bucket_size
            key = (round(low, 3), round(high, 3))
            
            if key not in buckets:
                buckets[key] = [0, 0]
            
            buckets[key][1] += 1
            if trade.outcome:
                buckets[key][0] += 1
        
        return buckets
    
    def to_csv(self, filepath: str):
        """Export trades to CSV."""
        if not self.trades:
            return
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'market', 'side', 'entry_price', 'stake', 
                'fair_value', 'edge', 'contracts', 'outcome', 'pnl', 'notes'
            ])
            for t in self.trades:
                writer.writerow([
                    t.timestamp, t.market, t.side, t.entry_price, t.stake,
                    t.fair_value, t.edge, t.contracts, t.outcome, t.pnl, t.notes
                ])
    
    def summary(self) -> str:
        """Pretty-print summary statistics."""
        return f"""
=== Paper Trading Summary ===
Trades: {len(self.trades)}
Win Rate: {self.win_rate():.1%}
Avg Edge: {self.avg_edge():.3f}
Avg P&L per Trade: ${self.expected_value():.3f}
Total P&L: ${self.total_pnl():.2f}
Return: {self.return_pct():.1f}%
Balance: ${self.balance:.2f} (was ${self.initial_balance:.2f})
Max Balance: ${self.max_balance:.2f}
"""


class StrategyBacktester:
    """Runs a trading strategy on historical data."""
    
    def __init__(self, model, initial_balance: float = 10.0):
        self.model = model
        self.log = PaperTradingLog(initial_balance)
    
    def backtest_tennis(self, 
                       match_data: List[Dict],
                       min_edge_points: float = 5.0,
                       stake_size: float = 1.0,
                       position_limit: float = 1.0) -> PaperTradingLog:
        """
        Backtest tennis strategy.
        
        match_data: list of dicts with keys:
          - timestamp, market, side, entry_price, fair_value, outcome
        
        Strategy:
          - Only trade if edge >= min_edge_points
          - Risk up to stake_size per trade
          - Don't risk more than position_limit per day/market
        """
        daily_risk = {}  # Track daily risk by market
        
        for data in match_data:
            market = data['market']
            day = data['timestamp'][:10]  # YYYY-MM-DD
            
            edge = data['fair_value'] - data['entry_price']
            
            # Skip if edge too small
            if edge < min_edge_points / 100:
                continue
            
            # Skip if position limit exceeded
            key = (day, market)
            daily_risk[key] = daily_risk.get(key, 0) + stake_size
            if daily_risk[key] > position_limit:
                continue
            
            # Size by Kelly (simplified: half-Kelly)
            kelly_fraction = edge / (1.0 - data['entry_price'])
            size = min(stake_size, self.log.balance * kelly_fraction * 0.5)
            
            trade = Trade(
                timestamp=data['timestamp'],
                market=market,
                side=data['side'],
                entry_price=data['entry_price'],
                stake=size,
                fair_value=data['fair_value'],
                edge=edge,
                contracts=size / data['entry_price'],
                outcome=data['outcome'],
                notes=f"Edge: {edge:.1%}"
            )
            
            self.log.log_trade(trade)
        
        return self.log


class LiveTradeSimulator:
    """Simulates live trading from a stream of prices."""
    
    def __init__(self, model, initial_balance: float = 10.0):
        self.model = model
        self.log = PaperTradingLog(initial_balance)
        self.open_positions = {}  # market -> Trade (unsettled)
    
    def on_price_update(self, market: str, current_price: float, target_price: float,
                       minutes_left: float, entry_prices: Dict[str, float]):
        """
        Called on each price update.
        
        entry_prices: {'Yes': 0.65, 'No': 0.35}
        """
        if minutes_left < 5:
            return  # Wait for late-window setup
        
        # Compute fair value
        vol_model = CryptoVolatilityModel()
        p_above = vol_model.prob_above_target(current_price, target_price, minutes_left)
        
        yes_fair = p_above
        no_fair = 1 - p_above
        
        yes_edge = yes_fair - entry_prices['Yes']
        no_edge = no_fair - entry_prices['No']
        
        # Trade the better side
        if yes_edge > 0.05 and yes_edge > no_edge:
            self._propose_trade(market, 'Yes', entry_prices['Yes'], yes_fair)
        elif no_edge > 0.05 and no_edge > yes_edge:
            self._propose_trade(market, 'No', entry_prices['No'], no_fair)
    
    def _propose_trade(self, market: str, side: str, price: float, fair_value: float):
        """Internal: propose a trade (doesn't execute without confirmation)."""
        edge = fair_value - price
        print(f"Proposed: {market} {side} @ {price:.2f} (fair {fair_value:.2f}, edge {edge:.1%})")
    
    def settle_position(self, market: str, outcome: bool):
        """Settle an open position."""
        if market in self.open_positions:
            trade = self.open_positions[market]
            trade.outcome = outcome
            self.log.log_trade(trade)
            del self.open_positions[market]
