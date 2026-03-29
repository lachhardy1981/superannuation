#!/usr/bin/env python3
"""
Fetch S&P 500 OHLCV data via yfinance and write full JSON (bars + indicators) to stdout.
Used both by server.js (local dev) and GitHub Actions (static site data files).
"""
import sys, json, warnings
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

warnings.filterwarnings('ignore')
import yfinance as yf

RANGE_DAYS = {'1mo': 35, '3mo': 100, '6mo': 200, '1y': 375, '2y': 750, '5y': 1850}

range_arg    = sys.argv[1] if len(sys.argv) > 1 else '1y'
interval_arg = sys.argv[2] if len(sys.argv) > 2 else '1d'

days  = RANGE_DAYS.get(range_arg, 375)
end   = datetime.now()
start = end - timedelta(days=days)

df = yf.download(
    '^GSPC',
    start=start.strftime('%Y-%m-%d'),
    end=end.strftime('%Y-%m-%d'),
    interval=interval_arg,
    auto_adjust=True,
    progress=False,
    multi_level_index=False,
)

if df.empty:
    print(json.dumps({'error': 'No data returned from yfinance'}))
    sys.exit(1)

close = df['Close'].astype(float)

# ── Indicators ────────────────────────────────────────────────────────────
def to_list(series):
    return [None if pd.isna(v) else round(float(v), 2) for v in series]

def sma(series, period):
    return to_list(series.rolling(period).mean())

def rsi(series, period=14):
    delta = series.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    avg_g = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_l = loss.ewm(com=period - 1, min_periods=period).mean()
    rs    = avg_g / avg_l
    return to_list(100 - 100 / (1 + rs))

def macd_calc(series, fast=12, slow=26, signal=9):
    ema_f  = series.ewm(span=fast,   adjust=False).mean()
    ema_s  = series.ewm(span=slow,   adjust=False).mean()
    m_line = ema_f - ema_s
    s_line = m_line.ewm(span=signal, adjust=False).mean()
    hist   = m_line - s_line
    result = []
    for m, s, h in zip(m_line, s_line, hist):
        if any(pd.isna(v) for v in [m, s, h]):
            result.append(None)
        else:
            result.append({'MACD': round(float(m), 2), 'signal': round(float(s), 2), 'histogram': round(float(h), 2)})
    return result

def bollinger(series, period=20, std_dev=2):
    mid = series.rolling(period).mean()
    std = series.rolling(period).std()
    result = []
    for m, u, l in zip(mid, mid + std_dev * std, mid - std_dev * std):
        if pd.isna(m):
            result.append(None)
        else:
            result.append({'upper': round(float(u), 2), 'middle': round(float(m), 2), 'lower': round(float(l), 2)})
    return result

# ── Build bars ────────────────────────────────────────────────────────────
bars = []
for idx, row in df.iterrows():
    bars.append({
        'time':   int(idx.timestamp()),
        'open':   round(float(row['Open']),  2),
        'high':   round(float(row['High']),  2),
        'low':    round(float(row['Low']),   2),
        'close':  round(float(row['Close']), 2),
        'volume': int(row['Volume']) if not pd.isna(row['Volume']) else 0,
    })

year_ago  = int((end - timedelta(days=365)).timestamp())
year_bars = [b for b in bars if b['time'] >= year_ago]
last_bar  = bars[-1]
prev_bar  = bars[-2] if len(bars) >= 2 else last_bar

print(json.dumps({
    'generatedAt': int(datetime.now().timestamp()),
    'meta': {
        'regularMarketPrice': last_bar['close'],
        'previousClose':      prev_bar['close'],
        'fiftyTwoWeekHigh':   max((b['high'] for b in year_bars), default=0),
        'fiftyTwoWeekLow':    min((b['low']  for b in year_bars), default=0),
        'regularMarketTime':  last_bar['time'],
    },
    'bars': bars,
    'indicators': {
        'sma20':  sma(close, 20),
        'sma50':  sma(close, 50),
        'sma100': sma(close, 100),
        'sma200': sma(close, 200),
        'rsi14':  rsi(close, 14),
        'macd':   macd_calc(close),
        'bb20':   bollinger(close, 20, 2),
    },
}))
