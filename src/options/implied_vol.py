"""
Implied Volatility Solver

This module implements numerical methods to solve for implied volatility
from market option prices using the Black-Scholes model.

Uses Newton-Raphson method with Brent's method as fallback.
"""

import numpy as np
from scipy.optimize import brentq
from typing import Tuple, Dict, Optional
from .black_scholes import bs_price, vega


def implied_vol_newton_raphson(market_price: float, S: float, K: float, r: float, T: float,
                              option_type: str = 'call', tol: float = 1e-6, max_iter: int = 100) -> Tuple[float, bool, int, list]:
    """
    Solve for implied volatility using Newton-Raphson method.

    f(σ) = BS_price(σ) - market_price = 0
    f'(σ) = vega

    σ_{n+1} = σ_n - f(σ_n) / f'(σ_n)

    Parameters:
    market_price: Observed market option price
    S: Spot price
    K: Strike price
    r: Risk-free rate (annual)
    T: Time to expiry (years)
    option_type: 'call' or 'put'
    tol: Convergence tolerance
    max_iter: Maximum iterations

    Returns:
    Tuple of (implied_vol, converged, iterations, iteration_log)
    """
    # Initial guess for volatility (20%)
    sigma = 0.20
    iteration_log = []

    for i in range(max_iter):
        # Calculate BS price and vega at current sigma
        bs_price_val = bs_price(S, K, r, sigma, T, option_type)
        vega_val = vega(S, K, r, sigma, T)

        # Avoid division by zero
        if abs(vega_val) < 1e-8:
            iteration_log.append(f"Iter {i+1}: Vega too small ({vega_val:.6f}), switching to Brent")
            break

        # Newton-Raphson update
        f = bs_price_val - market_price
        sigma_new = sigma - f / vega_val

        # Log iteration
        iteration_log.append(f"Iter {i+1}: σ={sigma:.6f}, BS=${bs_price_val:.4f}, f={f:.6f}, vega={vega_val:.4f}, σ_new={sigma_new:.6f}")

        # Check convergence
        if abs(sigma_new - sigma) < tol and abs(f) < tol:
            return sigma_new, True, i + 1, iteration_log

        # Update sigma
        sigma = sigma_new

        # Prevent negative or unrealistic volatility
        if sigma < 0 or sigma > 5.0:
            iteration_log.append(f"Iter {i+1}: σ out of bounds ({sigma:.6f}), switching to Brent")
            break

    # If Newton-Raphson failed, use Brent's method
    return implied_vol_brent(market_price, S, K, r, T, option_type, iteration_log)


def implied_vol_brent(market_price: float, S: float, K: float, r: float, T: float,
                     option_type: str = 'call', iteration_log: Optional[list] = None) -> Tuple[float, bool, int, list]:
    """
    Solve for implied volatility using Brent's method (fallback).

    Parameters:
    market_price: Observed market option price
    S: Spot price
    K: Strike price
    r: Risk-free rate (annual)
    T: Time to expiry (years)
    option_type: 'call' or 'put'
    iteration_log: Previous iteration log (optional)

    Returns:
    Tuple of (implied_vol, converged, iterations, iteration_log)
    """
    if iteration_log is None:
        iteration_log = []

    iteration_log.append("Using Brent's method as fallback")

    def objective(sigma):
        return bs_price(S, K, r, sigma, T, option_type) - market_price

    try:
        # Search between 0.001 and 5.0
        sigma = brentq(objective, 0.001, 5.0, xtol=1e-6, rtol=1e-6, maxiter=100)
        iteration_log.append(f"Brent converged: σ={sigma:.6f}")
        return sigma, True, 1, iteration_log
    except ValueError:
        iteration_log.append("Brent failed to converge")
        return 0.0, False, 0, iteration_log


def implied_volatility(market_price: float, S: float, K: float, r: float, T: float,
                      option_type: str = 'call', method: str = 'auto') -> Dict[str, any]:
    """
    Calculate implied volatility from market option price.

    Parameters:
    market_price: Observed market option price
    S: Spot price
    K: Strike price
    r: Risk-free rate (annual)
    T: Time to expiry (years)
    option_type: 'call' or 'put'
    method: 'newton', 'brent', or 'auto' (default: Newton with Brent fallback)

    Returns:
    Dictionary with results: {'iv': float, 'converged': bool, 'method': str, 'iterations': int, 'log': list}
    """
    if method == 'brent':
        iv, converged, iters, log = implied_vol_brent(market_price, S, K, r, T, option_type)
        method_used = 'brent'
    elif method == 'newton':
        iv, converged, iters, log = implied_vol_newton_raphson(market_price, S, K, r, T, option_type)
        method_used = 'newton'
    else:  # auto
        iv, converged, iters, log = implied_vol_newton_raphson(market_price, S, K, r, T, option_type)
        method_used = 'newton' if converged else 'brent'

    return {
        'iv': iv,
        'converged': converged,
        'method': method_used,
        'iterations': iters,
        'log': log
    }


def validate_iv_calculation(market_price: float, S: float, K: float, r: float, T: float,
                          option_type: str = 'call') -> Dict[str, any]:
    """
    Validate implied volatility calculation by checking if BS price matches market price.

    Parameters:
    market_price: Observed market option price
    S: Spot price
    K: Strike price
    r: Risk-free rate (annual)
    T: Time to expiry (years)
    option_type: 'call' or 'put'

    Returns:
    Dictionary with validation results
    """
    result = implied_volatility(market_price, S, K, r, T, option_type)

    if result['converged']:
        # Check if BS price with calculated IV matches market price
        bs_check = bs_price(S, K, r, result['iv'], T, option_type)
        error = abs(bs_check - market_price)
        percent_error = (error / market_price) * 100 if market_price != 0 else 0

        result.update({
            'bs_check_price': bs_check,
            'pricing_error': error,
            'pricing_error_percent': percent_error
        })

    return result