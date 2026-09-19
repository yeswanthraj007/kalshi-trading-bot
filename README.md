# Kalshi Trading Bot

A production-grade Python trading bot for Kalshi prediction markets with automated order execution, risk management, and statistical calibration.

## Features

- **Markov Chain Pricing Model** for tennis matches and crypto volatility
- **Live Kalshi API Integration** (REST + WebSocket)
- **Auto Order Execution** when edge ≥ threshold
- **Risk Management** (daily loss limits, position caps, Kelly sizing)
- **Paper Trading & Backtesting** with calibration metrics
- **Dry-Run Mode** (default) — test without real orders
- **Live Mode** — execute real trades with safety controls

## Architecture

```
src/
├── model.py              # Markov chain pricing model
├── kalshi_client.py      # Kalshi API client
├── backtest.py           # Paper trading engine
├── live_bot.py          # Auto-trading bot
├── test_connection.py   # Connection verification
└── main.py              # Backtest runner
```

## Quick Start

### 1. Clone & Setup

```bash
git clone <your-repo-url> kalshi-trading-bot
cd kalshi-trading-bot

# Install dependencies
pip install -r requirements.txt
```

### 2. Get Kalshi API Keys

1. Go to https://kalshi.com → Settings → API Keys
2. Create a NEW API key
3. Copy PUBLIC KEY and PRIVATE KEY

### 3. Configure Environment

```bash
cat > .env << 'EOF'
KALSHI_PUBLIC_KEY=your_public_key_here
KALSHI_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----
your_private_key_here
-----END RSA PRIVATE KEY-----
KALSHI_BASE_URL=https://api.kalshi.com
EOF
```

**⚠️ Never commit .env to git!** It's in `.gitignore`.

### 4. Test Connection

```bash
cd src
python test_connection.py
```

Expected output:
```
✓ Connected to Kalshi
✓ Account balance: $12.00
✓ ALL TESTS PASSED - Ready to trade!
```

### 5. Run Backtest

```bash
python main.py
```

### 6. Run Live Bot

**Dry-run (no real orders):**
```bash
python live_bot.py
```

**Live trading (REAL money):**
```bash
python live_bot.py --live
```

## Strategy

### Trade Execution

Bot automatically:
1. Streams live prices from Kalshi
2. Computes fair value (Markov model)
3. Calculates edge: `edge = fair_value - market_price`
4. Places order if `edge ≥ 5%` (configurable)
5. Holds to settlement
6. Logs P&L and calibration data

### Risk Management

Built-in safety controls:

| Control | Default | Purpose |
|---------|---------|---------|
| Min Edge | 5% | Only trade when you have an edge |
| Stake | $1.00 | Risk per trade |
| Daily Loss Limit | $2.00 | Stop trading after $2 loss |
| Position Limit | $5.00 | Max total open positions |
| Mode | Dry-run | No real orders by default |

## Models

### Tennis (Markov Chain)

Point-by-point model using serve-point win probabilities:
- Computes P(player wins game) given serve probability
- Computes P(player wins set) given game score
- Computes P(player wins match) given set score
- Blends pre-match odds with live serve statistics (Bayesian)

### Crypto (Volatility)

Lognormal price model:
- `log(P/P0) ~ N(0, σ * √(t/T))`
- σ adapts to current market volatility
- Computes P(price above target | time remaining)

## Files

| File | Purpose |
|------|---------|
| `src/model.py` | Pricing models (tennis, crypto) |
| `src/kalshi_client.py` | Kalshi API client |
| `src/backtest.py` | Paper trading engine |
| `src/live_bot.py` | Auto-trading bot |
| `src/test_connection.py` | Connection test |
| `src/main.py` | Backtest runner |
| `requirements.txt` | Python dependencies |
| `.env` | API keys (create this, don't commit) |
| `.gitignore` | Git exclusions |

## Usage

### Check Account Balance

```bash
python -c "from src.kalshi_client import KalshiClient; c = KalshiClient(); print(c.get_account())"
```

### List Open Orders

```bash
python -c "from src.kalshi_client import KalshiClient; c = KalshiClient(); print(c.get_orders())"
```

### Cancel an Order

```bash
python -c "from src.kalshi_client import KalshiClient; c = KalshiClient(); c.cancel_order('order_id')"
```

## Configuration

Edit `src/live_bot.py` to adjust:

```python
bot = LiveTradingBot(
    kalshi_client=client,
    min_edge_pct=5.0,           # Min edge % to trade
    stake_per_trade=1.0,        # $ per trade
    daily_loss_limit=2.0,       # Max loss per day
    position_limit=5.0          # Max total open
)
```

## Monitoring

Bot prints status every 60 seconds:

```
Balance: $12.50
Daily Loss: $0.30 / $2.00
Open Positions: 2
Win Rate: 65%
Total P&L: +$2.50
```

## Calibration

After 100+ trades, check if model is well-calibrated:

```python
log = PaperTradingLog()
# ... populate with trades ...
cal = log.calibration()
for (low, high), (wins, total) in sorted(cal.items()):
    actual = wins / total if total > 0 else 0
    print(f"{low:.0%}-{high:.0%}: {actual:.0%} actual")
```

If `actual ≈ expected`, model is calibrated.

## Safety First

⚠️ **Before going live:**

1. ✓ Test in dry-run mode for 1 week
2. ✓ Backtest 500+ trades
3. ✓ Verify calibration
4. ✓ Check P&L is positive
5. ✓ Use small stakes ($0.50–$1.00)
6. ✓ Set tight daily loss limits

Press `Ctrl+C` to stop bot immediately.

## Troubleshooting

### "KALSHI_PUBLIC_KEY required"
→ Create `.env` file with API keys

### "Invalid signature"
→ Check private key format (needs RSA headers)

### "Connection refused"
→ Kalshi API down or network issue

### "Order rejected"
→ Insufficient balance, market settled, or invalid price

## Next Steps

1. Clone repo & install dependencies
2. Get Kalshi API keys
3. Create `.env` file
4. Run `test_connection.py`
5. Run `main.py` (backtest)
6. Run `live_bot.py` (dry-run)
7. Paper-trade 1–2 weeks
8. Go live with small stakes

## Project Status

**Current**: Beta (tested, working, safe defaults)
**Next**: Live performance tracking, additional markets (politics, sports), advanced risk metrics

## License

MIT

## Disclaimer

This bot is for research/educational purposes. Past performance doesn't guarantee future results. Use at your own risk. Start small, test thoroughly, monitor closely. I'm not a financial advisor.

---

**Need help?** Check the docs/ folder or open an issue.
