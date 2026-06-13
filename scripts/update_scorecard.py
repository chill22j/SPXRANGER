"""
update_scorecard.py — runs in the Friday workflow AFTER market.json is written.
Reads data/market.json, grades any pending rows in data/scorecard.csv,
then appends fresh rows for next week's predictions.
"""
import csv
import json
import math
import datetime
from pathlib import Path

REPO_ROOT = Path('.')
MARKET_JSON = REPO_ROOT / 'data' / 'market.json'
SCORECARD_CSV = REPO_ROOT / 'data' / 'scorecard.csv'

CSV_HEADER = [
    'ticker', 'week_label', 'prev_close_date', 'prev_close',
    'vol', 'stretch', 'predicted_low', 'predicted_high',
    'friday_close_date', 'friday_close', 'result', 'distance'
]

SQRT_5_252 = math.sqrt(5 / 252)

def predict_spx(close, vol, stretch):
    is_stressed = vol >= 21
    k_low = 1.55 if is_stressed else 1.45
    k_high = 1.55 if is_stressed else 1.35
    if stretch is not None and stretch > 4:
        k_low *= 1.06  # recalibrated to 4-week trader avg
    wv = (vol / 100) * SQRT_5_252
    return round(close * (1 - k_low * wv)), round(close * (1 + k_high * wv))

def get_vol_multiplier(iv):
    threshold = 20.0
    if iv > threshold:
        return 1 + ((iv - threshold) * 0.0181)
    return 1.0

def predict_ndx(close, vol, stretch):
    k_low, k_high = 1.53, 1.50
    if stretch is not None and stretch < -3:
        k_high *= 1.10

    # Apply Sub-linear Volatility Scaling
    vol_mult = get_vol_multiplier(vol)
    k_low *= vol_mult
    k_high *= vol_mult

    wv = (vol / 100) * SQRT_5_252
    return round(close * (1 - k_low * wv)), round(close * (1 + k_high * wv))

def predict_qqq(qqq_close, ndx_close, ndx_low, ndx_high):
    ratio = qqq_close / ndx_close
    return round(ndx_low * ratio), round(ndx_high * ratio)

def predict_dynamic_range(close, vol, straddle_move):
    wv = (vol / 100) * SQRT_5_252
    vol_move = close * wv
    base_move = max(straddle_move, vol_move)
    
    k_factor = 2.0
    expanded_move = base_move * k_factor
    return round(close - expanded_move), round(close + expanded_move)

def grade_row(row, market, today_str):
    """Grade a row only if friday_close empty AND prev_close_date is before today."""
    if row.get('friday_close'):
        return False
    if row.get('prev_close_date') >= today_str:
        return False
    
    ticker = row['ticker']
    if ticker in ['SPX', 'NDX', 'QQQ']:
        field = {'SPX': 'spx', 'NDX': 'ndx', 'QQQ': 'qqq'}[ticker]
        close = market.get(field)
    else:
        # Pull individual stock close price
        individuals = market.get('individuals', {})
        stock_data = individuals.get(ticker)
        close = stock_data.get('close') if stock_data else None

    if close is None:
        return False

    pred_low = float(row['predicted_low'])
    pred_high = float(row['predicted_high'])
    if pred_low <= close <= pred_high:
        result, distance = 'WIN', 0
    elif close < pred_low:
        result, distance = 'LOSS', round(close - pred_low, 2)
    else:
        result, distance = 'LOSS', round(close - pred_high, 2)
        
    updated = market.get('updated', '')
    row['friday_close_date'] = updated[:10] if updated else ''
    row['friday_close'] = round(close, 2)
    row['result'] = result
    row['distance'] = distance
    return True

def next_week_label(today):
    days_to_monday = (7 - today.weekday()) % 7 or 7
    monday = today + datetime.timedelta(days=days_to_monday)
    friday = monday + datetime.timedelta(days=4)
    return f"{monday.month}/{monday.day}\u2013{friday.month}/{friday.day}"

def append_predictions(rows, market, week_label, today_str):
    existing_weeks = {(r['ticker'], r['week_label']) for r in rows}
    new_rows = []

    # --- Index Logic ---
    spx, vix = market.get('spx'), market.get('vix')
    ndx, vxn, qqq = market.get('ndx'), market.get('vxn'), market.get('qqq')
    stretch = market.get('stretch')
    ndx_stretch = market.get('ndxStretch')

    if spx is not None and vix is not None and ('SPX', week_label) not in existing_weeks:
        low, high = predict_spx(spx, vix, stretch)
        new_rows.append({
            'ticker': 'SPX', 'week_label': week_label,
            'prev_close_date': today_str, 'prev_close': spx,
            'vol': vix, 'stretch': stretch if stretch is not None else '',
            'predicted_low': low, 'predicted_high': high,
            'friday_close_date': '', 'friday_close': '', 'result': '', 'distance': '',
        })

    ndx_low = ndx_high = None
    if ndx is not None and vxn is not None and ('NDX', week_label) not in existing_weeks:
        ndx_low, ndx_high = predict_ndx(ndx, vxn, ndx_stretch)
        new_rows.append({
            'ticker': 'NDX', 'week_label': week_label,
            'prev_close_date': today_str, 'prev_close': ndx,
            'vol': vxn, 'stretch': ndx_stretch if ndx_stretch is not None else '',
            'predicted_low': ndx_low, 'predicted_high': ndx_high,
            'friday_close_date': '', 'friday_close': '', 'result': '', 'distance': '',
        })

    if (qqq is not None and ndx is not None and ndx_low is not None
            and ('QQQ', week_label) not in existing_weeks):
        qqq_low, qqq_high = predict_qqq(qqq, ndx, ndx_low, ndx_high)
        new_rows.append({
            'ticker': 'QQQ', 'week_label': week_label,
            'prev_close_date': today_str, 'prev_close': qqq,
            'vol': vxn, 'stretch': ndx_stretch if ndx_stretch is not None else '',
            'predicted_low': qqq_low, 'predicted_high': qqq_high,
            'friday_close_date': '', 'friday_close': '', 'result': '', 'distance': '',
        })

    # --- Individual Stock Logic ---
    individuals = market.get('individuals', {})
    for sym, data in individuals.items():
        if data and (sym, week_label) not in existing_weeks:
            close = data.get('close')
            vol = data.get('atmIV')
            straddle = data.get('straddleMove', 0)

            if close is not None and vol is not None:
                low, high = predict_dynamic_range(close, vol, straddle)
                new_rows.append({
                    'ticker': sym, 'week_label': week_label,
                    'prev_close_date': today_str, 'prev_close': close,
                    'vol': vol, 'stretch': '',
                    'predicted_low': low, 'predicted_high': high,
                    'friday_close_date': '', 'friday_close': '', 'result': '', 'distance': '',
                })

    rows.extend(new_rows)
    return len(new_rows)

def main():
    if not MARKET_JSON.exists():
        print(f"[scorecard] No {MARKET_JSON}, skipping.")
        return
    market = json.loads(MARKET_JSON.read_text())

    rows = []
    if SCORECARD_CSV.exists():
        with SCORECARD_CSV.open() as f:
            rows = list(csv.DictReader(f))

    today = datetime.date.today()
    today_str = today.isoformat()

    graded = sum(1 for r in rows if grade_row(r, market, today_str))
    print(f"[scorecard] Graded {graded} pending row(s)")

    week_label = next_week_label(today)
    appended = append_predictions(rows, market, week_label, today_str)
    print(f"[scorecard] Appended {appended} new row(s) for {week_label}")

    SCORECARD_CSV.parent.mkdir(parents=True, exist_ok=True)
    with SCORECARD_CSV.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, '') for k in CSV_HEADER})
    print(f"[scorecard] Wrote {len(rows)} total rows")

if __name__ == '__main__':
    main()
