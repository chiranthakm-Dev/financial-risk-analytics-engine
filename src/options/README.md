# Black-Scholes Options Pricing & Greeks Dashboard

A comprehensive options pricing module for the Financial Forecasting & Risk Analytics Engine.

## Features

- **Black-Scholes Analytical Pricing**: Complete implementation with all 5 Greeks
- **Monte Carlo Simulation**: 10,000 path GBM simulation for comparison
- **Implied Volatility Solver**: Newton-Raphson with Brent fallback
- **Interactive Dashboard**: Streamlit app with 3D visualizations

## Installation

```bash
pip install -r src/options/requirements.txt
```

## Usage

### As Standalone Modules

```python
from src.options.black_scholes import bs_price, all_greeks

# Price a call option
price = bs_price(S=100, K=105, r=0.05, sigma=0.20, T=1.0, option_type='call')

# Calculate all Greeks
greeks = all_greeks(S=100, K=105, r=0.05, sigma=0.20, T=1.0, option_type='call')
print(greeks)  # {'delta': 0.54, 'gamma': 0.02, 'theta': -5.2, 'vega': 12.4, 'rho': 8.9}
```

### Monte Carlo Simulation

```python
from src.options.monte_carlo import compare_bs_mc

result = compare_bs_mc(S=100, K=105, r=0.05, sigma=0.20, T=1.0, option_type='call')
print(f"BS: ${result['bs_price']:.4f}, MC: ${result['mc_price']:.4f}, Diff: {result['percent_difference']:.2f}%")
```

### Implied Volatility

```python
from src.options.implied_vol import implied_volatility

result = implied_volatility(market_price=10.50, S=100, K=105, r=0.05, T=1.0, option_type='call')
print(f"IV: {result['iv']:.2%}")
```

## Running the Dashboard

```bash
cd src/options
streamlit run app.py
```

The dashboard will open at `http://localhost:8501` with:

- **Sidebar Controls**: Spot price, strike, rates, volatility, time, option type
- **Pricing Comparison**: BS vs MC prices with difference %
- **Greeks Display**: All 5 Greeks as metric cards
- **3D Surfaces**: Interactive Plotly plots for each Greek vs spot/time
- **IV Solver**: Input market price, get implied volatility with convergence log
- **MC Visualization**: Terminal price distribution histogram with payoff overlay

## Mathematical Formulas

### Black-Scholes Call Price
```
C = S * N(d1) - K * e^(-rT) * N(d2)
```

### Greeks
- **Delta**: ∂C/∂S = N(d1) for calls
- **Gamma**: ∂²C/∂S² = N'(d1)/(Sσ√T)
- **Theta**: ∂C/∂T = -[SσN'(d1)]/(2√T) - rKe^(-rT)N(d2)
- **Vega**: ∂C/∂σ = S√T * N'(d1)
- **Rho**: ∂C/∂r = KT * e^(-rT) * N(d2)

Where:
- d1 = [ln(S/K) + (r + σ²/2)T] / (σ√T)
- d2 = d1 - σ√T
- N(x) = Standard normal CDF
- N'(x) = Standard normal PDF

## Integration with Main App

This module can be integrated into the main FastAPI application as a new route:

```python
from src.options.black_scholes import bs_price, all_greeks

@app.post("/api/v1/options/price")
def price_option(request: OptionsRequest):
    price = bs_price(request.S, request.K, request.r, request.sigma, request.T, request.option_type)
    greeks = all_greeks(request.S, request.K, request.r, request.sigma, request.T, request.option_type)
    return {"price": price, "greeks": greeks}
```

## Files Structure

```
src/options/
├── black_scholes.py    # Core BS engine
├── monte_carlo.py      # MC simulation
├── implied_vol.py      # IV solver
├── app.py             # Streamlit dashboard
├── test_modules.py    # Test script
└── requirements.txt   # Dependencies
```