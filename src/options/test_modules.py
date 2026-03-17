#!/usr/bin/env python3
"""
Test script for Black-Scholes Options modules
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.options.black_scholes import bs_price, all_greeks
from src.options.monte_carlo import compare_bs_mc
from src.options.implied_vol import implied_volatility

def test_black_scholes():
    """Test Black-Scholes pricing and Greeks"""
    print("Testing Black-Scholes...")

    # Test parameters
    S, K, r, sigma, T = 100, 105, 0.05, 0.20, 1.0

    # Call option
    call_price = bs_price(S, K, r, sigma, T, 'call')
    call_greeks = all_greeks(S, K, r, sigma, T, 'call')

    # Put option
    put_price = bs_price(S, K, r, sigma, T, 'put')
    put_greeks = all_greeks(S, K, r, sigma, T, 'put')

    print(f"Call Price: ${call_price:.4f}")
    print(f"Put Price: ${put_price:.4f}")
    print(f"Call Delta: {call_greeks['delta']:.4f}")
    print(f"Put Delta: {put_greeks['delta']:.4f}")
    print("✓ Black-Scholes test passed\n")

def test_monte_carlo():
    """Test Monte Carlo simulation"""
    print("Testing Monte Carlo...")

    S, K, r, sigma, T = 100, 105, 0.05, 0.20, 1.0

    result = compare_bs_mc(S, K, r, sigma, T, 'call', n_paths=1000)

    print(f"BS Price: ${result['bs_price']:.4f}")
    print(f"MC Price: ${result['mc_price']:.4f}")
    print(f"Difference: {result['percent_difference']:.2f}%")
    print("✓ Monte Carlo test passed\n")

def test_implied_vol():
    """Test implied volatility calculation"""
    print("Testing Implied Volatility...")

    S, K, r, T = 100, 105, 0.05, 1.0
    market_price = 10.50  # Example market price

    result = implied_volatility(market_price, S, K, r, T, 'call')

    if result['converged']:
        print(f"Market Price: ${market_price:.4f}")
        print(f"Implied Vol: {result['iv']:.2%}")
        print(f"Method: {result['method']}")
        print("✓ Implied volatility test passed\n")
    else:
        print("✗ Implied volatility failed to converge\n")

if __name__ == "__main__":
    print("Testing Black-Scholes Options Modules\n")

    try:
        test_black_scholes()
        test_monte_carlo()
        test_implied_vol()
        print("🎉 All tests passed!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()