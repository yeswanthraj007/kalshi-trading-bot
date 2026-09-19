# Development Guide

## Architecture Overview

The bot has 4 main layers:

```
┌─────────────────────────────────────┐
│  Live Trading Bot (live_bot.py)     │ Auto-execute, risk mgmt
├─────────────────────────────────────┤
│  Kalshi API Client (kalshi_client.py)│ REST + WebSocket
├─────────────────────────────────────┤
│  Pricing Models (model.py)           │ Markov chain, volatility
├─────────────────────────────────────┤
│  Paper Trading Engine (backtest.py)  │ Logging, calibration
└─────────────────────────────────────┘
```

## Key Components

### 1. Pricing Models (model.py)

#### TennisMarkovModel
Point-by-point Markov chain for tennis.

```python
model = TennisMarkovModel(p_a=0.65, p_b=0.68)

# P(A wins game) given A serves and has p_a serve win prob
p_game = model.game_win_prob(0.65)

# P(A wins set | current games)
p_set = model.set_win_prob(p_a_srv=0.65, p_b_srv=0.68, games_a=5, games_b=3, a_serving=True)

# P(A wins match)
p_match = model.match_win_prob(p_a_srv=0.65, p_b_srv=0.68, best_of_3=True)
```

**Calibration:**
- Pre-match odds = ~100 pseudo-observations (prior)
- Live serve stats = 32+ point samples (posterior)
- Blends via Bayesian update with SE ≈ ±8.6%

#### CryptoVolatilityModel
Lognormal model for short-term moves.

```python
model = CryptoVolatilityModel(volatility_pct_per_15min=1.5)
p_up = model.prob_above_target(
    current_price=80_882,
    target_price=81_000,
    minutes_left=9
)
```

**Volatility Adjustment:**
- Default: ±1.5% per 15 min
- Elevated: ±2.0–2.5% (after volatility spikes)
- Decay: σ ~ √(t/T)

#### BayesianCalibrator
Blends prior + observed data.

```python
prior = 0.77  # Pre-match odds
observed = 0.655  # Current set prob
blended = BayesianCalibrator.blend_probabilities(
    prior=prior,
    observed=observed,
    points_count=32,
    prior_strength=100  # Prior = 100 pseudo-obs
)
```

### 2. Kalshi API Client (kalshi_client.py)

RESTful + WebSocket client with HMAC-SHA256 signing.

#### REST Methods

```python
client = KalshiClient()

# Account
account = client.get_account()
print(account['balance_cash'])

# Markets
markets = client.get_markets(limit=10)

# Prices
prices = client.get_market_prices('TRUMP-2024')

# Orders
order = client.create_order(
    ticker='TRUMP-2024',
    side='Yes',
    price=0.42,
    quantity=10
)
client.cancel_order(order['order_id'])
orders = client.get_orders()
```

#### WebSocket Stream

```python
async def callback(ticker, yes_price, no_price):
    print(f"{ticker}: Yes={yes_price}, No={no_price}")

await client.stream_prices(['TRUMP-2024', 'BTC-PERP'], callback)
```

### 3. Paper Trading Engine (backtest.py)

Simulates trades and computes metrics.

```python
from backtest import PaperTradingLog, Trade

log = PaperTradingLog(initial_balance=10.0)

trade = Trade(
    timestamp='2026-09-19T12:00:00Z',
    market='TRUMP-2024',
    side='Yes',
    entry_price=0.42,
    stake=1.00,
    fair_value=0.48,
    edge=0.06,
    contracts=2.38,
    outcome=True  # Won
)

log.log_trade(trade)
print(f"Win Rate: {log.win_rate():.0%}")
print(f"Total P&L: ${log.total_pnl():.2f}")
log.to_csv('trades.csv')
```

### 4. Live Trading Bot (live_bot.py)

Auto-executes trades with risk management.

```python
bot = LiveTradingBot(
    kalshi_client=client,
    min_edge_pct=5.0,
    stake_per_trade=1.0,
    daily_loss_limit=2.0,
    position_limit=5.0
)

# Main loop (simplified)
while True:
    # Stream prices
    # Compute fair value
    # Check if edge >= threshold
    # Place order if conditions met
    # Settle positions as markets close
    await asyncio.sleep(60)
```

## Modifying the Bot

### Change Risk Parameters

Edit `src/live_bot.py`:

```python
bot = LiveTradingBot(
    kalshi_client=client,
    min_edge_pct=3.0,        # Lower edge threshold
    stake_per_trade=2.0,     # Larger bets
    daily_loss_limit=5.0,    # Higher daily limit
    position_limit=10.0      # More open positions
)
```

### Add a New Market

1. Identify market ticker (e.g., `ELECTION-2024`)
2. Create a pricing model for it:

```python
class PoliticsMarkovModel:
    def __init__(self, p_candidate_a):
        self.p_a = p_candidate_a
    
    def prob_wins_election(self, polls_current, days_left):
        # Model probability of candidate A winning
        pass
```

3. In `live_bot.py`, add to strategy:

```python
if 'ELECTION' in ticker:
    model = PoliticsMarkovModel(0.55)
    fair_value = model.prob_wins_election(polls, days)
    edge = fair_value - market_price
```

### Improve Calibration

1. Paper-trade 500+ markets
2. Extract trades to CSV
3. Analyze by probability bucket:

```python
def calibration_by_bucket(trades):
    buckets = {}
    for trade in trades:
        low = int(trade.fair_value * 10) / 10
        high = low + 0.1
        key = (low, high)
        if key not in buckets:
            buckets[key] = {'wins': 0, 'total': 0}
        buckets[key]['total'] += 1
        if trade.outcome:
            buckets[key]['wins'] += 1
    
    for (low, high), counts in sorted(buckets.items()):
        actual = counts['wins'] / counts['total']
        expected = (low + high) / 2
        print(f"{low:.0%}-{high:.0%}: {actual:.0%} (exp {expected:.0%})")
```

If actual deviates from expected by >2%, adjust:
- Increase prior strength (trust pre-match odds more)
- Adjust volatility model
- Add time decay to recent data

### Add Custom Order Types

Currently only Limit orders. To add Market orders:

```python
def create_market_order(self, ticker, side, quantity):
    # Get current best price
    prices = self.get_market_prices(ticker)
    best_price = prices['no_price'] if side == 'Yes' else prices['yes_price']
    
    # Place at best price
    return self.create_order(
        ticker=ticker,
        side=side,
        price=best_price,
        quantity=quantity
    )
```

## Testing

### Unit Tests

Create `tests/test_model.py`:

```python
import sys
sys.path.insert(0, '../src')

from model import TennisMarkovModel

def test_game_prob():
    model = TennisMarkovModel(p_a=0.65, p_b=0.68)
    p = model.game_win_prob(0.65)
    assert 0.4 < p < 0.8, "Probability should be in (0, 1)"

def test_set_prob():
    model = TennisMarkovModel(p_a=0.65, p_b=0.68)
    p = model.set_win_prob(0.65, 0.68, 0, 0, True)
    assert 0.0 < p < 1.0

if __name__ == '__main__':
    test_game_prob()
    test_set_prob()
    print("✓ All tests passed")
```

Run:
```bash
python test_model.py
```

### Integration Tests

Test Kalshi connection:

```bash
cd src
python test_connection.py
```

### Dry-Run Testing

Test bot without real orders:

```bash
cd src
python live_bot.py  # Default: dry-run mode
```

## Deployment

### Local Development
```bash
python src/live_bot.py
```

### Production (VPS/EC2)

```bash
# SSH into server
ssh ubuntu@your_server

# Clone repo
git clone <repo-url>
cd kalshi-trading-bot

# Install
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env
cat > .env << 'EOF'
KALSHI_PUBLIC_KEY=...
KALSHI_PRIVATE_KEY=...
KALSHI_BASE_URL=https://api.kalshi.com
EOF

# Run with nohup (survives disconnect)
nohup python src/live_bot.py --live > bot.log 2>&1 &

# Monitor
tail -f bot.log
```

### Docker (Optional)

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "src/live_bot.py"]
```

Build & run:

```bash
docker build -t kalshi-bot .
docker run --env-file .env kalshi-bot
```

## Contributing

1. Fork the repo
2. Create feature branch: `git checkout -b feature/my-feature`
3. Make changes
4. Test: `python src/test_connection.py`
5. Commit: `git commit -m "Add my feature"`
6. Push: `git push origin feature/my-feature`
7. Open PR

## Performance

### Backtest Performance

- 10 tennis trades: ~50ms
- 100 crypto windows: ~100ms
- Full calibration: <1s

### Live Performance

- WebSocket latency: ~50ms (Kalshi)
- Order placement: ~200ms
- Full cycle (price → decision → order): ~300ms

## Debugging

### Enable Verbose Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Inspect Live Prices

```python
client = KalshiClient()
prices = client.get_market_prices('TRUMP-2024')
print(prices)
```

### Check Calibration

```python
from backtest import PaperTradingLog

log = PaperTradingLog()
# ... load trades ...
print(f"Win rate: {log.win_rate():.0%}")
print(f"Avg P&L: ${log.log.total_pnl() / len(log.trades):.2f}")
```

## Next Steps

- [ ] Add more sports markets
- [ ] Implement order book slippage model
- [ ] Add position tracking across sessions
- [ ] Build web dashboard for monitoring
- [ ] Add email/Discord alerts
- [ ] Implement position averaging
- [ ] Add volatility-based sizing

---

Happy hacking! 🚀
