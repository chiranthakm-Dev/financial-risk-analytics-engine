"""
Monte Carlo Options Pricing Engine

This module implements Monte Carlo simulation for European options pricing
using Geometric Brownian Motion (GBM) for stock price evolution.

Uses vectorized NumPy operations for efficient simulation of 10,000 paths.
"""

import numpy as np
from typing import Tuple, Dict


def simulate_gbm_paths(S0: float, r: float, sigma: float, T: float, n_paths: int = 10000, n_steps: int = 252) -> np.ndarray:
    """
    Simulate stock price paths using Geometric Brownian Motion.

    dS = r * S * dt + sigma * S * dW

    Parameters:
    S0: Initial stock price
    r: Risk-free rate (annual)
    sigma: Volatility (annual)
    T: Time to expiry (years)
    n_paths: Number of simulation paths (default: 10,000)
    n_steps: Number of time steps per path (default: 252, daily)

    Returns:
    Array of shape (n_paths,) with terminal stock prices at T
    """
    dt = T / n_steps

    # Generate random shocks for all paths and steps at once
    # Shape: (n_paths, n_steps)
    dW = np.random.standard_normal((n_paths, n_steps)) * np.sqrt(dt)

    # Initialize stock prices
    S = np.full((n_paths, n_steps + 1), S0, dtype=np.float64)
    S[:, 0] = S0

    # Simulate path by path using vectorized operations
    for t in range(1, n_steps + 1):
        S[:, t] = S[:, t-1] * np.exp((r - 0.5 * sigma**2) * dt + sigma * dW[:, t-1])

    # Return terminal prices at T
    return S[:, -1]


def mc_option_price(S0: float, K: float, r: float, sigma: float, T: float,
                   option_type: str = 'call', n_paths: int = 10000) -> Tuple[float, float, np.ndarray]:
    """
    Price European option using Monte Carlo simulation.

    Parameters:
    S0: Initial stock price
    K: Strike price
    r: Risk-free rate (annual)
    sigma: Volatility (annual)
    T: Time to expiry (years)
    option_type: 'call' or 'put'
    n_paths: Number of simulation paths

    Returns:
    Tuple of (option_price, standard_error, terminal_prices_array)
    """
    # Simulate terminal stock prices
    terminal_prices = simulate_gbm_paths(S0, r, sigma, T, n_paths)

    # Calculate payoffs
    if option_type.lower() == 'call':
        payoffs = np.maximum(terminal_prices - K, 0)
    elif option_type.lower() == 'put':
        payoffs = np.maximum(K - terminal_prices, 0)
    else:
        raise ValueError("option_type must be 'call' or 'put'")

    # Discount payoffs to present value
    discounted_payoffs = payoffs * np.exp(-r * T)

    # Calculate option price and standard error
    option_price = np.mean(discounted_payoffs)
    standard_error = np.std(discounted_payoffs) / np.sqrt(n_paths)

    return option_price, standard_error, terminal_prices


def compare_bs_mc(S0: float, K: float, r: float, sigma: float, T: float,
                 option_type: str = 'call', n_paths: int = 10000) -> Dict[str, float]:
    """
    Compare Black-Scholes analytical price with Monte Carlo simulation.

    Parameters:
    S0: Initial stock price
    K: Strike price
    r: Risk-free rate (annual)
    sigma: Volatility (annual)
    T: Time to expiry (years)
    option_type: 'call' or 'put'
    n_paths: Number of simulation paths

    Returns:
    Dictionary with BS price, MC price, difference, and % difference
    """
    from .black_scholes import bs_price

    # Get Black-Scholes price
    bs_price_val = bs_price(S0, K, r, sigma, T, option_type)

    # Get Monte Carlo price
    mc_price_val, mc_se, _ = mc_option_price(S0, K, r, sigma, T, option_type, n_paths)

    # Calculate differences
    difference = mc_price_val - bs_price_val
    percent_diff = (difference / bs_price_val) * 100 if bs_price_val != 0 else 0

    return {
        'bs_price': bs_price_val,
        'mc_price': mc_price_val,
        'mc_standard_error': mc_se,
        'difference': difference,
        'percent_difference': percent_diff
    }


def get_payoff_distribution(S0: float, K: float, r: float, sigma: float, T: float,
                          option_type: str = 'call', n_paths: int = 10000) -> Tuple[np.ndarray, np.ndarray]:
    """
    Get terminal stock prices and corresponding payoffs for visualization.

    Parameters:
    S0: Initial stock price
    K: Strike price
    r: Risk-free rate (annual)
    sigma: Volatility (annual)
    T: Time to expiry (years)
    option_type: 'call' or 'put'
    n_paths: Number of simulation paths

    Returns:
    Tuple of (terminal_prices, payoffs)
    """
    terminal_prices = simulate_gbm_paths(S0, r, sigma, T, n_paths)

    if option_type.lower() == 'call':
        payoffs = np.maximum(terminal_prices - K, 0)
    else:
        payoffs = np.maximum(K - terminal_prices, 0)

    return terminal_prices, payoffs