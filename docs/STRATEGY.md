# Trading Strategy & Models

## Overview

The bot uses statistical edge-driven trading:

1. **Compute fair value** (what you think the true probability is)
2. **Compare to market price** (what Kalshi is offering)
3. **Calculate edge** = fair_value - market_price
4. **Trade only if edge ≥ threshold** (minimum 5 percentage points)

Example:
- Fair value: 60% (you think 60% chance)
- Market price: 50¢ (Kalshi thinks 50%)
- Edge: 10 percentage points
- Decision: **BUY** (market underpricing the outcome)

## Tennis Model (Markov Chain)

### Approach

Point-by-point simulation given serve-point win probabilities.

### Inputs

- `p_a`: P(Player A wins point when A serves)
- `p_b`: P(Player B wins point when B serves)

Example: Federer vs Nadal on grass
- Federer serves: p = 0.65 (65% win point on own serve)
- Nadal serves: p = 0.62 (62% win point on own serve)

### Computation

#### 1. Game Probability

Given server win probability, compute P(server wins game):

```
P(game) = Σ P(reach deuce) × P(win from deuce)
```

For p_server = 0.65:
- Reach 40-0 or win outright: ~41%
- Reach deuce & win: ~24%
- Total: ~65%

#### 2. Set Probability

Given game probabilities & current score:

```
P(set | 5-3 down, A serving) = Σ outcomes × probabilities
```

Recursive computation:
- If A reaches 6 games with 2+ game lead: A wins set
- If B reaches 6 games with 2+ game lead: B wins set
- Otherwise: continue to next game

#### 3. Match Probability

For best-of-3, blend across sets:

```
P(match) = P(set1) × P(set2) × (different weighting for sets 2+ if needed)
```

### Calibration

**Problem:** Pre-match odds may be outdated. Live serve stats are noisy.

**Solution:** Bayesian blending.

```
P_final = w × P_prior + (1-w) × P_observed
```

Where:
- `P_prior` = pre-match odds (e.g., 60%)
- `P_observed` = current serve stats (e.g., 53%)
- `w` = weight on prior (depends on sample size)

**Sample size calculation:**
- Pre-match odds ≈ 100 pseudo-observations
- Each new serve point ≈ 1 observation
- At 32 serve points, SE ≈ ±8.6% for observed stat
- Weight drops from 100 to ~(100/(100+32)) ≈ 76%

**Example at 32 points:**
```
P_final = 0.76 × 0.60 + 0.24 × 0.53 = 0.588 = 58.8%
```

### When to Trade

**Only if edge ≥ 5%** (configurable).

Example trade:
- Fair value: 58.8% (your model)
- Market: 50¢ = 50% (Kalshi)
- Edge: 8.8 percentage points
- Action: **BUY** "Yes" at 50¢

**Stake sizing:** Half-Kelly
```
f* = edge / (1 - market_price)
stake = 0.5 × f* × bankroll
```

Example:
```
f* = 0.088 / (1 - 0.50) = 0.088 / 0.50 = 0.176 = 17.6%
stake = 0.5 × 0.176 × $12 = $1.06
```

**So: Buy $1 of "Yes" at 50¢, expecting $0.50 edge on $1 stake.**

### Edge Decay

As match progresses, edge shrinks:
- At 0-0: Full model edge if market mis-priced
- At 5-3 down: Smaller edge (outcome more certain)
- At 5-4 down, serving at 30-30: Almost no edge

**Reason:** Market sees same live data. Edge only exists if model sees something market doesn't (or weights it differently).

## Crypto Model (Volatility)

### Approach

Lognormal short-term moves.

### Model

```
log(P_t / P_0) ~ N(0, σ² × √(t/T))
```

Where:
- `P_0` = current price
- `P_t` = price at time t
- `σ` = annualized volatility
- `T` = time window (15 min for Kalshi contracts)
- `t` = remaining time

### Example

BTC at $80,882, 15-min window closes in 9 minutes. Will it end above $81,000?

```
Current: $80,882
Target: $81,000
Gap: $118 (0.15% above current)

Volatility (15 min): ±1.5% = ±$1,213

Time remaining: 9 min = 60% of window
Effective vol: 1.5% × √0.6 = 1.16%

log(81000/80882) = 0.00146
σ_eff = 0.0116 × 80882 = $938
z = 0.00146 / 0.938 = 0.00156
P(above) = N(0.00156) = 50.06%
```

**Interpretation:** At 50% fair value, break-even is 50¢ (no edge).

### Volatility Adjustment

Default: ±1.5% per 15 min (BTC normal regime).

**Elevated volatility** (after spike):
- 1.5x normal: ±2.25%
- 2x normal: ±3.0%

Detected by:
- Recent large moves (>0.5% in last minute)
- High option implied volatility
- Market microstructure changes

**Time decay:**

```
vol(t) = vol_baseline × √(t / 15 min)
```

As time remaining drops, volatility shrinks (fewer moves possible).

### Entry Rules

Only trade if:
1. **Edge ≥ 5%** (fair value minus market price)
2. **≥5 min left** (enough time for model to be valid)
3. **Position not too large** (position limit)
4. **Daily loss not exceeded** (daily stop)

Example trade:
- Fair value: 60% (model)
- Market: 48¢ (Kalshi asks)
- Edge: 12 percentage points
- Time: 7 min left
- Stake: $1
- Action: **BUY** "Yes" at 48¢

## Risk Management

### Daily Loss Limit

Stop trading after losing $2 in a day.

```
daily_loss = sum(pnl for trades today where pnl < 0)
if daily_loss >= $2:
    stop_trading()
```

**Rationale:** Prevent cascade losses. If model is broken, stop quickly.

### Position Limit

Max $5 total open at once.

```
open_value = sum(stake for open_positions)
if open_value >= $5:
    no_new_trades()
```

**Rationale:** Avoid concentration risk. If Kalshi API breaks, limit exposure.

### Stake Sizing (Half-Kelly)

```
optimal_f = edge / (1 - price)
stake = 0.5 × optimal_f × bankroll
```

**Why 0.5?** Full Kelly is too aggressive for uncertain models. Half-Kelly provides:
- Smoother equity curve
- Resilience to model mis-calibration
- Faster recovery from drawdowns

**Example:**
```
Model: 58% fair value
Market: 50¢
Edge: 8%

Optimal f = 0.08 / 0.50 = 0.16 = 16%
Half-Kelly = 0.5 × 16% = 8%
Stake = 8% × $12 = $0.96 ≈ $1

If win: +$0.50 profit, -$0.96 cost of contract = +$0.50 total
If lose: -$0.96
```

## Calibration

### Definition

Model is **calibrated** if:
- P(outcome | fair_value = X%) ≈ X%

Example: Over 100 bets where model says 60%:
- Expect ~60 wins
- Actual ~60 wins → **Calibrated**
- Actual ~45 wins → Model overconfident (under-estimating risk)
- Actual ~75 wins → Model underconfident (over-estimating risk)

### Checking Calibration

1. Bin trades by fair value (e.g., 55–60%, 60–65%)
2. Compute win rate in each bin
3. Compare to expected

```python
bins = {
    (0.55, 0.60): (wins=5, total=9),    # 56% win rate (expected 57%)
    (0.60, 0.65): (wins=12, total=18),  # 67% win rate (expected 62%)
    (0.65, 0.70): (wins=8, total=11),   # 73% win rate (expected 67%)
}

# Plot actual vs expected
for (low, high), (wins, total) in sorted(bins.items()):
    actual = wins / total
    expected = (low + high) / 2
    print(f"{low:.0%}-{high:.0%}: {actual:.0%} actual vs {expected:.0%} expected")
```

### Adjusting for Miscalibration

**If actual > expected** (overconfident):
- Increase prior strength (trust pre-match data more)
- Decrease volatility (reduce uncertainty)
- Add time decay (recent data matters less)

**If actual < expected** (underconfident):
- Decrease prior strength (rely more on live data)
- Increase volatility (account for more uncertainty)
- Give recent data more weight

## Kelly Sizing Deep Dive

### Full Kelly Formula

```
f* = (p × b - (1-p)) / b
```

Where:
- `p` = win probability
- `b` = odds (or payoff ratio)

For Kalshi (binary outcome):
- Bet: $1
- Win: get $1 + payoff
- Lose: lose $1

**Payoff from $1 bet at price P:**
```
Profit if win: $1 / P - $1 = $(1/P - 1)
Loss if lose: $1
```

**Edge:**
```
edge = p × (1/P - 1) - (1-p) × 1 = p/P - 1
```

**Kelly:**
```
f = edge / (1/P - 1) = (p/P - 1) / (1/P - 1)
```

For p=0.60, P=0.50:
```
edge = 0.60/0.50 - 1 = 0.20
f = 0.20 / (1/0.50 - 1) = 0.20 / 1 = 0.20 = 20%
```

**So: Bet 20% of bankroll (full Kelly). With 0.5 Kelly: bet 10%.**

### Why Half-Kelly?

**Full Kelly can:**
- Wipe you out on bad luck
- Require you to take on extra leverage (hard to implement)
- Amplify model errors

**Half-Kelly:**
- 25% of full Kelly's growth rate, 1/4 the drawdown
- Survives model calibration errors
- Easier psychology

## Example Trade Walkthrough

### Setup

- Tennis match: Federer vs Nadal (Wimbledon)
- Pre-match odds: Federer 60%
- Current score: 5-3, Federer down, Nadal serving

### Step 1: Estimate Live Serve Probabilities

```
Federer (on return): won 7/12 points = 58%
Nadal (on serve): won 8/11 points = 73%
```

### Step 2: Run Markov Model

```python
model = TennisMarkovModel(p_a=0.58, p_b=0.73)
p_set = model.set_win_prob(p_a_srv=0.58, p_b_srv=0.73, 
                           games_a=3, games_b=5, a_serving=False)
# p_set ≈ 0.35 (35% chance Federer wins set from here)
```

### Step 3: Blend with Prior

```python
prior = 0.60  # Pre-match Federer
observed = 0.35  # Current set prob
points = 23  # Serve points seen

blended = BayesianCalibrator.blend_probabilities(
    prior=prior,
    observed=observed,
    points_count=points,
    prior_strength=100
)
# weight_prior = 100/(100+23) = 0.813
# blended = 0.813×0.60 + 0.187×0.35 = 0.554 = 55.4%
```

### Step 4: Check Market & Edge

```
Fair value: 55.4%
Market price: 45¢ (Kalshi asks for Federer)
Edge: 55.4% - 45% = 10.4 percentage points
```

### Step 5: Decide & Size

```
Edge >= 5%? Yes (10.4% > 5%)
Daily loss limit exceeded? No ($0.10 loss so far)
Position limit ok? Yes (only $1 open)

Kelly sizing:
f = 0.104 / (1 - 0.45) = 0.104 / 0.55 = 0.189 = 18.9%
Half-Kelly = 9.45%
Stake = 9.45% × $12 = $1.13 ≈ $1.00
```

### Step 6: Execute

```
BUY $1 of "Federer Yes" at 45¢
Order ID: order_12345
```

### Step 7: Settlement

**Scenario A (Federer wins set):**
```
Profit: $1 / 0.45 - $1 = $2.22 - $1 = $1.22
Total: $12 + $1.22 = $13.22
```

**Scenario B (Nadal wins set):**
```
Loss: $1.00
Total: $12 - $1 = $11
```

**Expected value:**
```
EV = 0.554 × $1.22 + 0.446 × (-$1.00) = +$0.233
```

**So: Expected to make $0.23 on this $1 bet.** That's the edge.

---

## Adjusting Strategy

### Lower Edge Threshold

Change in `live_bot.py`:
```python
bot = LiveTradingBot(
    min_edge_pct=3.0  # Lower from 5.0
)
```

Effect: More trades, but lower quality signals. Use if confident in model.

### Larger Stakes

```python
bot = LiveTradingBot(
    stake_per_trade=2.0  # Higher from 1.0
)
```

Effect: Higher P&L swings. Use if bankroll is larger.

### Adjust Volatility

```python
model = CryptoVolatilityModel(volatility_pct_per_15min=2.0)  # Was 1.5
```

Effect: Model assumes bigger moves. Affects all crypto trades.

---

**Good luck! Remember: edges are small, variance is large. Paper-trade for weeks before going live.** 🚀
