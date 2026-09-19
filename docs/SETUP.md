# Setup Guide

## Prerequisites

- Python 3.9+
- pip
- Kalshi account with funds
- GitHub account (to clone repo)

## Step 1: Clone Repository

```bash
git clone <your-repo-url> kalshi-trading-bot
cd kalshi-trading-bot
```

## Step 2: Create Virtual Environment (Recommended)

```bash
# Create venv
python3 -m venv venv

# Activate it
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows
```

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 4: Get Kalshi API Keys

1. Go to **https://kalshi.com**
2. Log in to your account
3. Click **Settings** (gear icon)
4. Click **API Keys** or **Developer**
5. Click **Create New API Key**
   - If you have an exposed key, delete it first!
   - Create a fresh one
6. Copy the **PUBLIC KEY** (short ID like `396cb110-...`)
7. Copy the **PRIVATE KEY** (long RSA key)

**⚠️ Keep private key SECRET. Never commit to git.**

## Step 5: Create .env File

In the repo root, create `.env`:

```bash
cat > .env << 'EOF'
KALSHI_PUBLIC_KEY=paste_your_public_key_here
KALSHI_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----
paste_your_private_key_here
-----END RSA PRIVATE KEY-----
KALSHI_BASE_URL=https://api.kalshi.com
EOF
```

Replace the placeholders with your actual keys.

**Verify .env is in .gitignore:**
```bash
grep "^\.env" .gitignore  # Should output: .env
```

## Step 6: Test Connection

```bash
cd src
python test_connection.py
```

Expected output:
```
============================================================
KALSHI API CONNECTION TEST
============================================================

1. Initializing client...
   ✓ Client created

2. Fetching account info...
   ✓ Connected to Kalshi
   ✓ Account ID: ...
   ✓ Balance: $12.00

3. Fetching markets...
   ✓ Found XXX markets (showing first 3):
      - TRUMP-2024: Donald Trump wins 2024...
      - BTC-PERP-SUN: Bitcoin above 150000...
      - ...

============================================================
✓ ALL TESTS PASSED - Ready to trade!
============================================================

Next step: python live_bot.py
```

If this fails:
- Check .env is in repo root
- Verify API keys are correct
- Check internet connection
- Try again (Kalshi API might be temporarily down)

## Step 7: Run Backtest

```bash
python main.py
```

Output:
```
============================================================
KALSHI PREDICTION MARKET TRADING BOT
Paper Trading Backtester
============================================================

=== Tennis Strategy Backtest ===
Trades: 10
Win Rate: 60.0%
...
Total P&L: $-2.41
Return: -24.1%
```

This uses sample data, so P&L varies. Real data will differ.

## Step 8: Run Live Bot - Dry Run

**Default: no real orders placed**

```bash
python live_bot.py
```

Output:
```
✓ Connected to Kalshi
✓ Account balance: $12.00

============================================================
KALSHI LIVE TRADING BOT
Mode: DRY RUN (no orders)
============================================================

Balance: $12.00
Daily Loss: $0.00 / $2.00
Open Positions: 0

============================================================

Bot running. Press Ctrl+C to stop.
```

Press `Ctrl+C` to stop.

## Step 9: Run Live Bot - Live Trading

**⚠️ WARNING: This places REAL orders with real money**

Once confident, run:

```bash
python live_bot.py --live
```

This will:
- Stream live prices
- Auto-execute trades when edge ≥ 5%
- Update every 60 seconds
- Stop on daily loss limit

**Start with small stakes ($0.50–$1.00).**

## Troubleshooting

### "No module named 'kalshi_client'"
→ Make sure you're in the repo root and running from `src/`:
```bash
cd src
python test_connection.py
```

### ".env not found"
→ Create it in repo root:
```bash
cat > .env << 'EOF'
KALSHI_PUBLIC_KEY=your_key
KALSHI_PRIVATE_KEY=your_private_key
KALSHI_BASE_URL=https://api.kalshi.com
EOF
```

### "Invalid signature"
→ Your private key format is wrong. Make sure it has:
```
-----BEGIN RSA PRIVATE KEY-----
[key content]
-----END RSA PRIVATE KEY-----
```

### "Connection refused"
→ Kalshi API might be down. Try again in a few minutes.

### "Order rejected"
→ Possible causes:
- Insufficient balance (need $1+ per order)
- Market already settled
- Invalid price (must be 0.0–1.0)
- Daily loss limit reached

## File Structure

```
kalshi-trading-bot/
├── src/
│   ├── model.py              # Pricing models
│   ├── kalshi_client.py      # API client
│   ├── backtest.py           # Paper trading
│   ├── live_bot.py           # Live trading bot
│   ├── test_connection.py    # Connection test
│   └── main.py               # Backtest runner
├── docs/
│   ├── SETUP.md              # This file
│   ├── DEVELOPMENT.md        # Development guide
│   └── STRATEGY.md           # Strategy details
├── README.md                  # Main readme
├── requirements.txt          # Python dependencies
├── .env                      # API keys (don't commit!)
├── .env.example              # Example .env
└── .gitignore                # Git exclusions
```

## Next Steps

1. ✓ Clone repo
2. ✓ Create venv
3. ✓ Install dependencies
4. ✓ Create .env with API keys
5. ✓ Run test_connection.py
6. ✓ Run main.py (backtest)
7. ✓ Run live_bot.py (dry-run)
8. → Paper-trade 1–2 weeks
9. → Go live with small stakes

## Questions?

- Check README.md for overview
- Check docs/STRATEGY.md for model details
- Check docs/DEVELOPMENT.md for modifying the bot
- Open an issue on GitHub

Good luck! 🚀
