"""
Black-Scholes Options Pricing Engine

This module implements the complete Black-Scholes model for European options pricing
and Greeks calculation using closed-form analytical formulas.

Mathematical formulas are shown in docstrings for educational purposes.
"""

import numpy as np
from scipy.stats import norm
from typing import Tuple, Dict


def d1(S: float, K: float, r: float, sigma: float, T: float) -> float:
    """
    Calculate d1 parameter for Black-Scholes model.

    d1 = [ln(S/K) + (r + σ²/2)T] / (σ√T)

    Parameters:
    S: Spot price
    K: Strike price
    r: Risk-free rate (annual)
    sigma: Volatility (annual)
    T: Time to expiry (years)

    Returns:
    d1 value
    """
    if T <= 0:
        return np.inf if S > K else -np.inf
    if sigma <= 0:
        return np.inf if S > K else -np.inf

    return (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))


def d2(S: float, K: float, r: float, sigma: float, T: float) -> float:
    """
    Calculate d2 parameter for Black-Scholes model.

    d2 = d1 - σ√T

    Parameters:
    S: Spot price
    K: Strike price
    r: Risk-free rate (annual)
    sigma: Volatility (annual)
    T: Time to expiry (years)

    Returns:
    d2 value
    """
    return d1(S, K, r, sigma, T) - sigma * np.sqrt(T)


def bs_call_price(S: float, K: float, r: float, sigma: float, T: float) -> float:
    """
    Calculate Black-Scholes European call option price.

    C = S * N(d1) - K * e^(-rT) * N(d2)

    Parameters:
    S: Spot price
    K: Strike price
    r: Risk-free rate (annual)
    sigma: Volatility (annual)
    T: Time to expiry (years)

    Returns:
    Call option price
    """
    if T <= 0:
        return max(S - K, 0)

    d1_val = d1(S, K, r, sigma, T)
    d2_val = d2(S, K, r, sigma, T)

    return S * norm.cdf(d1_val) - K * np.exp(-r * T) * norm.cdf(d2_val)


def bs_put_price(S: float, K: float, r: float, sigma: float, T: float) -> float:
    """
    Calculate Black-Scholes European put option price.

    P = K * e^(-rT) * N(-d2) - S * N(-d1)

    Parameters:
    S: Spot price
    K: Strike price
    r: Risk-free rate (annual)
    sigma: Volatility (annual)
    T: Time to expiry (years)

    Returns:
    Put option price
    """
    if T <= 0:
        return max(K - S, 0)

    d1_val = d1(S, K, r, sigma, T)
    d2_val = d2(S, K, r, sigma, T)

    return K * np.exp(-r * T) * norm.cdf(-d2_val) - S * norm.cdf(-d1_val)


def bs_price(S: float, K: float, r: float, sigma: float, T: float, option_type: str = 'call') -> float:
    """
    Calculate Black-Scholes option price for call or put.

    Parameters:
    S: Spot price
    K: Strike price
    r: Risk-free rate (annual)
    sigma: Volatility (annual)
    T: Time to expiry (years)
    option_type: 'call' or 'put'

    Returns:
    Option price
    """
    if option_type.lower() == 'call':
        return bs_call_price(S, K, r, sigma, T)
    elif option_type.lower() == 'put':
        return bs_put_price(S, K, r, sigma, T)
    else:
        raise ValueError("option_type must be 'call' or 'put'")


def delta(S: float, K: float, r: float, sigma: float, T: float, option_type: str = 'call') -> float:
    """
    Calculate option delta (∂C/∂S or ∂P/∂S).

    For call: Δ = N(d1)
    For put: Δ = N(d1) - 1 = -N(-d1)

    Parameters:
    S: Spot price
    K: Strike price
    r: Risk-free rate (annual)
    sigma: Volatility (annual)
    T: Time to expiry (years)
    option_type: 'call' or 'put'

    Returns:
    Delta value
    """
    if T <= 0:
        if option_type.lower() == 'call':
            return 1.0 if S > K else 0.0
        else:
            return -1.0 if S < K else 0.0

    d1_val = d1(S, K, r, sigma, T)

    if option_type.lower() == 'call':
        return norm.cdf(d1_val)
    else:
        return norm.cdf(d1_val) - 1


def gamma(S: float, K: float, r: float, sigma: float, T: float) -> float:
    """
    Calculate option gamma (∂²C/∂S² = ∂²P/∂S²).

    Γ = N'(d1) / (S * σ * √T)

    Where N'(x) is the standard normal PDF.

    Parameters:
    S: Spot price
    K: Strike price
    r: Risk-free rate (annual)
    sigma: Volatility (annual)
    T: Time to expiry (years)

    Returns:
    Gamma value (same for call and put)
    """
    if T <= 0 or sigma <= 0:
        return 0.0

    d1_val = d1(S, K, r, sigma, T)
    return norm.pdf(d1_val) / (S * sigma * np.sqrt(T))


def theta(S: float, K: float, r: float, sigma: float, T: float, option_type: str = 'call') -> float:
    """
    Calculate option theta (∂C/∂T or ∂P/∂T).

    For call: Θ = -[S * σ * N'(d1)] / (2√T) - r * K * e^(-rT) * N(d2)
    For put: Θ = -[S * σ * N'(d1)] / (2√T) + r * K * e^(-rT) * N(-d2)

    Parameters:
    S: Spot price
    K: Strike price
    r: Risk-free rate (annual)
    sigma: Volatility (annual)
    T: Time to expiry (years)
    option_type: 'call' or 'put'

    Returns:
    Theta value (annualized, per year)
    """
    if T <= 0:
        return 0.0

    d1_val = d1(S, K, r, sigma, T)
    d2_val = d2(S, K, r, sigma, T)

    term1 = - (S * sigma * norm.pdf(d1_val)) / (2 * np.sqrt(T))

    if option_type.lower() == 'call':
        term2 = - r * K * np.exp(-r * T) * norm.cdf(d2_val)
    else:
        term2 = r * K * np.exp(-r * T) * norm.cdf(-d2_val)

    return term1 + term2


def vega(S: float, K: float, r: float, sigma: float, T: float) -> float:
    """
    Calculate option vega (∂C/∂σ = ∂P/∂σ).

    ν = S * √T * N'(d1)

    Parameters:
    S: Spot price
    K: Strike price
    r: Risk-free rate (annual)
    sigma: Volatility (annual)
    T: Time to expiry (years)

    Returns:
    Vega value (same for call and put, per 1% change in volatility)
    """
    if T <= 0 or sigma <= 0:
        return 0.0

    d1_val = d1(S, K, r, sigma, T)
    return S * np.sqrt(T) * norm.pdf(d1_val)


def rho(S: float, K: float, r: float, sigma: float, T: float, option_type: str = 'call') -> float:
    """
    Calculate option rho (∂C/∂r or ∂P/∂r).

    For call: ρ = K * T * e^(-rT) * N(d2)
    For put: ρ = -K * T * e^(-rT) * N(-d2)

    Parameters:
    S: Spot price
    K: Strike price
    r: Risk-free rate (annual)
    sigma: Volatility (annual)
    T: Time to expiry (years)
    option_type: 'call' or 'put'

    Returns:
    Rho value (per 1% change in risk-free rate)
    """
    if T <= 0:
        return 0.0

    d2_val = d2(S, K, r, sigma, T)

    if option_type.lower() == 'call':
        return K * T * np.exp(-r * T) * norm.cdf(d2_val)
    else:
        return -K * T * np.exp(-r * T) * norm.cdf(-d2_val)


def all_greeks(S: float, K: float, r: float, sigma: float, T: float, option_type: str = 'call') -> Dict[str, float]:
    """
    Calculate all five Greeks for an option.

    Parameters:
    S: Spot price
    K: Strike price
    r: Risk-free rate (annual)
    sigma: Volatility (annual)
    T: Time to expiry (years)
    option_type: 'call' or 'put'

    Returns:
    Dictionary with all Greeks: {'delta': val, 'gamma': val, 'theta': val, 'vega': val, 'rho': val}
    """
    return {
        'delta': delta(S, K, r, sigma, T, option_type),
        'gamma': gamma(S, K, r, sigma, T),
        'theta': theta(S, K, r, sigma, T, option_type),
        'vega': vega(S, K, r, sigma, T),
        'rho': rho(S, K, r, sigma, T, option_type)
    }


def option_price_and_greeks(S: float, K: float, r: float, sigma: float, T: float, option_type: str = 'call') -> Tuple[float, Dict[str, float]]:
    """
    Calculate option price and all Greeks in one call.

    Parameters:
    S: Spot price
    K: Strike price
    r: Risk-free rate (annual)
    sigma: Volatility (annual)
    T: Time to expiry (years)
    option_type: 'call' or 'put'

    Returns:
    Tuple of (option_price, greeks_dict)
    """
    price = bs_price(S, K, r, sigma, T, option_type)
    greeks = all_greeks(S, K, r, sigma, T, option_type)
    return price, greeks