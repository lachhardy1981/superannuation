#!/usr/bin/env python3
"""Fetch Claude AI analysis of SMA20/SMA50 crossover for S&P 500."""

import json
import sys
import os
from datetime import datetime, timezone
import anthropic


def get_sma_context():
    """Read current SMA values and recent cross info from the 1y data file."""
    try:
        with open('data/sp500_1y_1d.json', 'r') as f:
            data = json.load(f)

        bars = data.get('bars', [])
        indicators = data.get('indicators', {})

        if not bars:
            return None

        sma20_all = indicators.get('sma20', [])
        sma50_all = indicators.get('sma50', [])

        # Latest non-null values
        sma20_vals = [(bars[i]['time'], v) for i, v in enumerate(sma20_all) if v is not None]
        sma50_vals = [(bars[i]['time'], v) for i, v in enumerate(sma50_all) if v is not None]

        if not sma20_vals or not sma50_vals:
            return None

        last_sma20 = sma20_vals[-1][1]
        last_sma50 = sma50_vals[-1][1]
        last_price = bars[-1]['close']
        as_of = bars[-1]['time']

        # Find the most recent cross (sign change in sma20 - sma50)
        last_cross_date = None
        cross_direction = None
        for i in range(len(bars) - 1, 0, -1):
            a, b = sma20_all[i], sma50_all[i]
            pa, pb = sma20_all[i - 1], sma50_all[i - 1]
            if None in (a, b, pa, pb):
                continue
            if (a - b) * (pa - pb) < 0:
                last_cross_date = bars[i]['time']
                cross_direction = "above" if (a - b) > 0 else "below"
                break

        return {
            'last_price': last_price,
            'sma20': last_sma20,
            'sma50': last_sma50,
            'last_cross_date': last_cross_date,
            'cross_direction': cross_direction,
            'as_of': as_of,
        }
    except Exception as e:
        print(f"Warning: could not read SMA context: {e}", file=sys.stderr)
        return None


def main():
    ctx = get_sma_context()

    if ctx:
        cross_info = ""
        if ctx.get('last_cross_date') and ctx.get('cross_direction'):
            cross_info = (
                f"The most recent cross occurred on {ctx['last_cross_date']}, "
                f"where SMA20 crossed {ctx['cross_direction']} SMA50. "
            )
        prompt = (
            f"The S&P 500 is currently at {ctx['last_price']:.2f} (as of {ctx['as_of']}). "
            f"The SMA20 is at {ctx['sma20']:.2f} and the SMA50 is at {ctx['sma50']:.2f}. "
            f"{cross_info}"
            "The SMA20 and SMA50 on the S&P recently crossed — when do you forecast they will "
            "cross again? Please provide a concise analysis with your forecast."
        )
    else:
        prompt = (
            "The SMA20 and SMA50 on the S&P 500 recently crossed. "
            "When do you forecast they will cross again? "
            "Please provide a concise analysis with your forecast."
        )

    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    text = next(b.text for b in response.content if b.type == "text")

    result = {
        "analysis": text,
        "context": ctx,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": "claude-sonnet-4-6",
    }

    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
