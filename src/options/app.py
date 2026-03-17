"""
Black-Scholes Options Pricing Dashboard

Interactive Streamlit application for options pricing, Greeks calculation,
Monte Carlo simulation, and implied volatility solving.
"""

import streamlit as st
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from options.black_scholes import bs_price, all_greeks
from options.monte_carlo import compare_bs_mc, get_payoff_distribution
from options.implied_vol import implied_volatility


def main():
    st.set_page_config(
        page_title="Black-Scholes Options Dashboard",
        page_icon="📈",
        layout="wide"
    )

    st.title("📈 Black-Scholes Options Pricing & Greeks Dashboard")

    # Sidebar inputs
    st.sidebar.header("Option Parameters")

    S = st.sidebar.number_input("Spot Price (S)", value=100.0, min_value=0.01, step=1.0)
    K = st.sidebar.number_input("Strike Price (K)", value=105.0, min_value=0.01, step=1.0)
    r = st.sidebar.slider("Risk-Free Rate (r)", 0.0, 0.10, 0.05, 0.005)
    sigma = st.sidebar.slider("Volatility (σ)", 0.01, 1.0, 0.20, 0.01)
    T = st.sidebar.slider("Time to Expiry (T)", 0.01, 5.0, 1.0, 0.1)
    option_type = st.sidebar.radio("Option Type", ["Call", "Put"], index=0).lower()

    # Main content
    col1, col2 = st.columns(2)

    # Pricing comparison
    with col1:
        st.subheader("Pricing Comparison")

        # Black-Scholes price
        bs_price_val = bs_price(S, K, r, sigma, T, option_type)

        # Monte Carlo price
        mc_result = compare_bs_mc(S, K, r, sigma, T, option_type)

        col1a, col1b = st.columns(2)
        with col1a:
            st.metric("Black-Scholes Price", f"${bs_price_val:.4f}")
        with col1b:
            st.metric("Monte Carlo Price", f"${mc_result['mc_price']:.4f}",
                     delta=f"{mc_result['percent_difference']:.2f}%")

        st.caption(f"MC Standard Error: ${mc_result['mc_standard_error']:.4f}")

    # Greeks display
    with col2:
        st.subheader("Option Greeks")

        greeks = all_greeks(S, K, r, sigma, T, option_type)

        cols = st.columns(5)
        greek_names = ['Delta', 'Gamma', 'Theta', 'Vega', 'Rho']
        greek_keys = ['delta', 'gamma', 'theta', 'vega', 'rho']

        for i, (name, key) in enumerate(zip(greek_names, greek_keys)):
            with cols[i]:
                st.metric(name, f"{greeks[key]:.4f}")

    # 3D Surface plots
    st.header("3D Greek Surfaces")

    # Create grid for surface plots
    S_range = np.linspace(max(S * 0.5, 1), S * 1.5, 50)
    T_range = np.linspace(0.01, max(T, 1.0), 50)
    S_grid, T_grid = np.meshgrid(S_range, T_range)

    greek_plots = ['delta', 'gamma', 'theta', 'vega', 'rho']
    greek_titles = ['Delta Surface', 'Gamma Surface', 'Theta Surface', 'Vega Surface', 'Rho Surface']

    cols = st.columns(3)
    for i, (greek, title) in enumerate(zip(greek_plots, greek_titles)):
        with cols[i % 3]:
            # Calculate Greek values on grid
            greek_values = np.zeros_like(S_grid)
            for j in range(S_grid.shape[0]):
                for k in range(S_grid.shape[1]):
                    if greek == 'delta':
                        greek_values[j, k] = all_greeks(S_grid[j, k], K, r, sigma, T_grid[j, k], option_type)['delta']
                    elif greek == 'gamma':
                        greek_values[j, k] = all_greeks(S_grid[j, k], K, r, sigma, T_grid[j, k], option_type)['gamma']
                    elif greek == 'theta':
                        greek_values[j, k] = all_greeks(S_grid[j, k], K, r, sigma, T_grid[j, k], option_type)['theta']
                    elif greek == 'vega':
                        greek_values[j, k] = all_greeks(S_grid[j, k], K, r, sigma, T_grid[j, k], option_type)['vega']
                    else:  # rho
                        greek_values[j, k] = all_greeks(S_grid[j, k], K, r, sigma, T_grid[j, k], option_type)['rho']

            # Create 3D surface plot
            fig = go.Figure(data=[go.Surface(
                x=S_range,
                y=T_range,
                z=greek_values,
                colorscale='Viridis'
            )])

            fig.update_layout(
                title=title,
                scene=dict(
                    xaxis_title='Spot Price ($)',
                    yaxis_title='Time to Expiry (Years)',
                    zaxis_title=greek.capitalize()
                ),
                margin=dict(l=0, r=0, t=30, b=0)
            )

            st.plotly_chart(fig, use_container_width=True)

    # Implied Volatility Solver
    st.header("Implied Volatility Solver")

    market_price = st.number_input("Market Option Price", value=float(bs_price_val), min_value=0.0, step=0.01)

    if st.button("Solve for Implied Volatility"):
        with st.spinner("Solving..."):
            iv_result = implied_volatility(market_price, S, K, r, T, option_type)

        if iv_result['converged']:
            st.success(f"Implied Volatility: {iv_result['iv']:.2%}")
            st.caption(f"Method: {iv_result['method'].title()} | Iterations: {iv_result['iterations']}")

            with st.expander("Iteration Log"):
                for log_entry in iv_result['log']:
                    st.text(log_entry)
        else:
            st.error("Failed to converge to implied volatility")

    # Monte Carlo Simulation Visualization
    st.header("Monte Carlo Simulation")

    terminal_prices, payoffs = get_payoff_distribution(S, K, r, sigma, T, option_type)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(terminal_prices, bins=50, alpha=0.7, label='Terminal Stock Prices')
    ax.axvline(K, color='red', linestyle='--', label=f'Strike Price (${K})')

    # Add payoff overlay
    ax2 = ax.twinx()
    sorted_indices = np.argsort(terminal_prices)
    ax2.plot(terminal_prices[sorted_indices], payoffs[sorted_indices],
             color='orange', linewidth=2, label='Option Payoff')

    ax.set_xlabel('Stock Price ($)')
    ax.set_ylabel('Frequency')
    ax2.set_ylabel('Payoff ($)')
    ax.set_title('Terminal Stock Price Distribution & Option Payoff')
    ax.legend(loc='upper left')
    ax2.legend(loc='upper right')

    st.pyplot(fig)

    # Statistics
    col_stats1, col_stats2, col_stats3 = st.columns(3)
    with col_stats1:
        st.metric("Mean Terminal Price", f"${np.mean(terminal_prices):.2f}")
    with col_stats2:
        st.metric("Std Dev Terminal Price", f"${np.std(terminal_prices):.2f}")
    with col_stats3:
        st.metric("MC Option Price", f"${mc_result['mc_price']:.4f}")


if __name__ == "__main__":
    import matplotlib.pyplot as plt
    main()