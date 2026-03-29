import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# --- Parameters ---
TICKER = "^GSPC"
HISTORY_YEARS = 3
FORECAST_MONTHS = 12
SMA_SHORT_WEEKS = 20   # 20 weeks ≈ 100 trading days
SMA_LONG_WEEKS = 50    # 50 weeks ≈ 250 trading days
SMA_SHORT_DAYS = SMA_SHORT_WEEKS * 5
SMA_LONG_DAYS = SMA_LONG_WEEKS * 5

# --- Fetch data (extra buffer for SMA warm-up) ---
end_date = datetime(2026, 3, 28)
start_date = end_date - timedelta(days=365 * HISTORY_YEARS + SMA_LONG_DAYS + 30)
print(f"Downloading S&P 500 data from {start_date.date()} to {end_date.date()}...")
data = yf.download(TICKER, start=start_date, end=end_date, auto_adjust=True)
data = data.sort_index()
close = data["Close"].squeeze()

# --- Calculate SMAs ---
sma_20w = close.rolling(window=SMA_SHORT_DAYS).mean()
sma_50w = close.rolling(window=SMA_LONG_DAYS).mean()

# Trim to 3-year display window
display_start = end_date - timedelta(days=365 * HISTORY_YEARS)
close_display = close[close.index >= str(display_start.date())]
sma_20w_display = sma_20w[sma_20w.index >= str(display_start.date())]
sma_50w_display = sma_50w[sma_50w.index >= str(display_start.date())]

# --- Forecast SMAs using linear extrapolation ---
def forecast_sma(sma_series, forecast_days, lookback=60):
    """Extrapolate SMA trend using recent linear regression."""
    recent = sma_series.dropna().tail(lookback)
    x = np.arange(len(recent))
    y = recent.values
    coeffs = np.polyfit(x, y, 1)  # linear fit

    last_date = sma_series.dropna().index[-1]
    future_dates = [last_date + timedelta(days=i) for i in range(1, forecast_days + 1)]
    # Filter to business days (rough approximation)
    future_dates = [d for d in future_dates if d.weekday() < 5]

    future_x = np.arange(len(recent), len(recent) + len(future_dates))
    future_y = np.polyval(coeffs, future_x)

    return future_dates, future_y, coeffs

forecast_trading_days = int(FORECAST_MONTHS * 21)  # ~21 trading days per month
dates_20w, values_20w, _ = forecast_sma(sma_20w, int(forecast_trading_days * 1.5), lookback=60)
dates_50w, values_50w, _ = forecast_sma(sma_50w, int(forecast_trading_days * 1.5), lookback=60)

# --- Find crossover point in forecast ---
# Interpolate both forecasts onto common dates
common_dates = sorted(set(dates_20w) & set(dates_50w))
vals_20w_common = np.interp(
    [d.toordinal() for d in common_dates],
    [d.toordinal() for d in dates_20w],
    values_20w
)
vals_50w_common = np.interp(
    [d.toordinal() for d in common_dates],
    [d.toordinal() for d in dates_50w],
    values_50w
)

diff = vals_20w_common - vals_50w_common
cross_idx = None
for i in range(1, len(diff)):
    if diff[i-1] * diff[i] < 0:  # sign change = crossover
        cross_idx = i
        break

# --- Plot ---
fig, ax = plt.subplots(figsize=(18, 9))

# Historical
ax.plot(close_display.index, close_display.values, color='#333333', linewidth=1, label='S&P 500', alpha=0.7)
ax.plot(sma_20w_display.index, sma_20w_display.values, color='green', linewidth=2, label=f'{SMA_SHORT_WEEKS}-Week SMA')
ax.plot(sma_50w_display.index, sma_50w_display.values, color='red', linewidth=2, label=f'{SMA_LONG_WEEKS}-Week SMA')

# Forecast zone
ax.axvline(x=end_date, color='gray', linestyle='--', linewidth=1, alpha=0.7)
ax.text(end_date + timedelta(days=5), ax.get_ylim()[0] if ax.get_ylim()[0] > 0 else close_display.min() * 0.98,
        'FORECAST →', fontsize=10, color='gray', fontweight='bold', va='bottom')

# Forecast lines (dashed)
ax.plot(dates_20w, values_20w, color='green', linewidth=2, linestyle='--', alpha=0.7)
ax.plot(dates_50w, values_50w, color='red', linewidth=2, linestyle='--', alpha=0.7)

# Mark crossover
if cross_idx is not None:
    cross_date = common_dates[cross_idx]
    cross_val = vals_20w_common[cross_idx]
    ax.scatter([cross_date], [cross_val], color='gold', s=200, zorder=5, edgecolors='black', linewidth=2)
    ax.annotate(f'SMA Crossover\n{cross_date.strftime("%b %d, %Y")}',
                xy=(cross_date, cross_val),
                xytext=(cross_date + timedelta(days=20), cross_val * 1.03),
                fontsize=11, fontweight='bold', color='#333',
                arrowprops=dict(arrowstyle='->', color='black', lw=1.5),
                bbox=dict(boxstyle='round,pad=0.4', facecolor='gold', alpha=0.8))
    print(f"\n★ Projected SMA crossover: {cross_date.strftime('%B %d, %Y')} at ~{cross_val:.0f}")
else:
    print("\n★ No SMA crossover projected within the 12-month forecast window.")

# Formatting
ax.set_title('S&P 500 — Daily Close with 20-Week & 50-Week SMA\n(3-Year History + 12-Month Forecast)',
             fontsize=16, fontweight='bold', pad=15)
ax.set_xlabel('Date', fontsize=12)
ax.set_ylabel('Price (USD)', fontsize=12)
ax.legend(loc='upper left', fontsize=12, framealpha=0.9)
ax.grid(True, alpha=0.3)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
plt.xticks(rotation=45)

# Shade forecast region
ylims = ax.get_ylim()
ax.axvspan(end_date, end_date + timedelta(days=365), alpha=0.05, color='blue')
ax.set_ylim(ylims)

plt.tight_layout()
output_path = "/Users/lachlanhardy/Desktop/Super/sp500_sma_forecast.png"
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"\nChart saved to: {output_path}")
plt.close()
