#!/usr/bin/env python3
"""
Main trading bot entry point.
Runs backtests or paper trading on Kalshi prediction markets.
"""

import sys
import json
from datetime import datetime
from model import TennisMarkovModel, BayesianCalibrator
from backtest import PaperTradingLog, StrategyBacktester, Trade


def generate_sample_tennis_data():
    """
    Generate sample historical tennis match data for backtesting.
    Simulates 50 matches across various sports betting markets.
    """
    data = []
    
    # Example match results with pre-match calibration
    matches = [
        # (pre_match_p_a, serve_p_a, serve_p_b, player_a_won)
        (0.77, 0.655, 0.685, True),   # Lehecka scenario
        (0.77, 0.655, 0.685, False),  # Could have gone either way
        (0.63, 0.60, 0.65, True),
        (0.55, 0.58, 0.60, False),
        (0.72, 0.68, 0.61, True),
        (0.81, 0.70, 0.58, True),
        (0.45, 0.55, 0.60, False),
        (0.58, 0.59, 0.62, False),
        (0.68, 0.65, 0.62, True),
        (0.75, 0.67, 0.63, True),
    ]
    
    for i, (pre_p_a, srv_a, srv_b, outcome_a) in enumerate(matches):
        model = TennisMarkovModel(srv_a, srv_b)
        
        # Simulate: we trade when player A is down a set at 79 cents
        # (like the Lehecka trade earlier)
        set_prob = model.set_win_prob(srv_a, srv_b, 5, 3, True)
        match_prob = set_prob + (1 - set_prob) * (pre_p_a * 0.45)  # Rough estimate
        
        entry_price = 0.79
        fair_value = match_prob
        
        data.append({
            'timestamp': f'2026-09-{(i % 28) + 1:02d}T12:00:00Z',
            'market': f'Tennis Match {i+1}',
            'side': 'Player A (Favorite Down a Set)',
            'entry_price': entry_price,
            'fair_value': fair_value,
            'outcome': outcome_a,
        })
    
    return data


def generate_sample_crypto_data():
    """
    Generate sample crypto price data for BTC 15-minute windows.
    50 windows with realistic move patterns.
    """
    data = []
    
    base_price = 80_000
    for i in range(50):
        # Simulate price moves: mostly small, occasional large
        import random
        random.seed(i)
        move_pct = random.gauss(0, 1.2)  # 0-mean, +/- 1.2% typical
        current = base_price * (1 + move_pct / 100)
        
        # Target is slightly higher on avg (uptrend)
        target = base_price * (1 + (i + 1) * 0.02 / 100)
        
        # Price probabilities (rough)
        above_pct = 0.55 + (current - target) / 200
        above_pct = max(0.1, min(0.9, above_pct))
        
        entry_up = above_pct + 0.02  # Market is slightly long
        entry_down = 1 - entry_up
        
        # Outcome is random but biased
        outcome_up = random.random() < above_pct
        
        data.append({
            'timestamp': f'2026-09-18T{(i % 24):02d}:{(i*15) % 60:02d}:00Z',
            'market': f'BTC 15-min {i+1}',
            'side': 'Up' if outcome_up else 'Down',
            'entry_price': entry_up if outcome_up else entry_down,
            'fair_value': above_pct,
            'outcome': outcome_up,
        })
        
        base_price = current
    
    return data


def backtest_tennis_strategy():
    """Run backtest on tennis data with the strategy we discussed."""
    print("=== Tennis Strategy Backtest ===\n")
    
    data = generate_sample_tennis_data()
    
    model = TennisMarkovModel(0.65, 0.68)  # Default serve probs
    backtest = StrategyBacktester(model, initial_balance=10.0)
    
    # Strategy: trade only if edge >= 5%, stake $1 per trade
    log = backtest.backtest_tennis(
        match_data=data,
        min_edge_points=5.0,
        stake_size=1.0,
        position_limit=3.0
    )
    
    print(log.summary())
    
    # Print calibration
    print("\n=== Calibration by Fair Value Bucket ===")
    cal = log.calibration(bucket_size=0.05)
    for (low, high), (wins, total) in sorted(cal.items()):
        actual_wr = wins / total if total > 0 else 0
        print(f"  {low:.0%}-{high:.0%}: {actual_wr:.0%} ({wins}/{total})")
    
    # Export to CSV
    log.to_csv('/home/claude/trading_bot/tennis_backtest.csv')
    print("\nBacktest results saved to tennis_backtest.csv")
    
    return log


def backtest_crypto_strategy():
    """Run backtest on crypto data."""
    print("\n=== Crypto Strategy Backtest ===\n")
    
    data = generate_sample_crypto_data()
    
    model = None  # Not used for crypto, but required by interface
    backtest = StrategyBacktester(model, initial_balance=10.0)
    
    # Strategy: trade late-window (simulated by only those with low edge)
    log = backtest.backtest_tennis(
        match_data=data,
        min_edge_points=3.0,  # Lower threshold for crypto
        stake_size=0.5,
        position_limit=2.0
    )
    
    print(log.summary())
    
    print("\n=== Calibration by Fair Value Bucket ===")
    cal = log.calibration(bucket_size=0.05)
    for (low, high), (wins, total) in sorted(cal.items()):
        actual_wr = wins / total if total > 0 else 0
        print(f"  {low:.0%}-{high:.0%}: {actual_wr:.0%} ({wins}/{total})")
    
    log.to_csv('/home/claude/trading_bot/crypto_backtest.csv')
    print("\nBacktest results saved to crypto_backtest.csv")
    
    return log


def main():
    """Run backtests and print results."""
    print("\n" + "=" * 60)
    print("KALSHI PREDICTION MARKET TRADING BOT")
    print("Paper Trading Backtester")
    print("=" * 60 + "\n")
    
    tennis_log = backtest_tennis_strategy()
    crypto_log = backtest_crypto_strategy()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Tennis trades: {len(tennis_log.trades)}, return: {tennis_log.return_pct():.1f}%")
    print(f"Crypto trades: {len(crypto_log.trades)}, return: {crypto_log.return_pct():.1f}%")
    
    combined_pnl = tennis_log.total_pnl() + crypto_log.total_pnl()
    combined_return = (combined_pnl / 20.0) * 100  # 2x $10 initial
    print(f"Combined: ${combined_pnl:.2f}, return: {combined_return:.1f}%")
    
    print("\n✓ Backtests complete. Check CSV files for full trade logs.")


if __name__ == '__main__':
    main()
