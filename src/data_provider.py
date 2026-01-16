import yfinance as yf
import pandas as pd
import numpy as np

# =============================================================================
# SEKCHJA 1: LOGIKA FIBONACCIEGO I KLASTRÓW (EPIC 1)
# =============================================================================

def get_fib_levels(start_price, end_price, start_date):
    '''Wylicza poziomy Fibo dla konkretnego impulsu z wagami.'''
    diff = end_price - start_price
    return {
        '38.2%': {'price': end_price - diff * 0.382, 'date': start_date, 'weight': 1.0},
        '50.0%': {'price': end_price - diff * 0.500, 'date': start_date, 'weight': 1.2},
        '61.8%': {'price': end_price - diff * 0.618, 'date': start_date, 'weight': 1.5},
        '78.6%': {'price': end_price - diff * 0.786, 'date': start_date, 'weight': 1.5}
    }

def find_clusters(structure):
    '''Szuka klastrów i agreguje poziomy w strefy.'''
    all_levels = []
    hh_price = structure['hh']['price']
    
    for hl in structure['hls']:
        levels_dict = get_fib_levels(hl['price'], hh_price, hl['date'])
        for name, data in levels_dict.items():
            level_score = hl.get('score', 1.0) * data['weight']
            all_levels.append({
                'price': data['price'], 
                'from_hl': hl['price'], 
                'date': data['date'],
                'type': name,
                'score': level_score
            })
    
    all_levels.sort(key=lambda x: x['price'])
    
    clusters = []
    i = 0
    while i < len(all_levels):
        current_cluster = [all_levels[i]]
        j = i + 1
        while j < len(all_levels) and (all_levels[j]['price'] - all_levels[i]['price']) / all_levels[i]['price'] < 0.0050:
            current_cluster.append(all_levels[j])
            j += 1
        
        if len(current_cluster) >= 2:
            avg_price = sum(c['price'] for c in current_cluster) / len(current_cluster)
            total_score = sum(c['score'] for c in current_cluster)
            clusters.append({
                'avg_price': avg_price,
                'min_price': min(c['price'] for c in current_cluster),
                'max_price': max(c['price'] for c in current_cluster),
                'count': len(current_cluster),
                'total_score': total_score,
                'levels': sorted(current_cluster, key=lambda x: x['date'])
            })
        i = j

    if not clusters: return []
    
    zones = []
    clusters.sort(key=lambda x: x['avg_price'])
    i = 0
    while i < len(clusters):
        current_zone = [clusters[i]]
        j = i + 1
        while j < len(clusters) and (clusters[j]['avg_price'] - clusters[i]['avg_price']) / clusters[i]['avg_price'] < 0.012:
            current_zone.append(clusters[j])
            j += 1
        
        z_min = min(c['min_price'] for c in current_zone)
        z_max = max(c['max_price'] for c in current_zone)
        zones.append({
            'avg_price': (z_min + z_max) / 2,
            'min_price': z_min,
            'max_price': z_max,
            'total_score': sum(c['total_score'] for c in current_zone),
            'total_count': sum(c['count'] for c in current_zone),
            'levels': sorted([lvl for c in current_zone for lvl in c['levels']], key=lambda x: x['price'])
        })
        i = j
    return sorted(zones, key=lambda x: x['total_score'], reverse=True)

# =============================================================================
# SEKCHJA 2: ANALIZA STRUKTURY I WYCKOFF EFFORT
# =============================================================================

def find_all_significant_lows(df):
    '''Szukanie dołków z analizą Wyckoffa i resetem struktury.'''
    if df is None or len(df) < 252: return None
    
    df = df.copy()
    df['Vol_MA20'] = df['Volume'].rolling(20).mean()
    df['Price_Range'] = df['High'] - df['Low']
    df['Effort_Ratio'] = df['Volume'] / df['Price_Range'].replace(0, np.nan)
    df['Eff_MA20'] = df['Effort_Ratio'].rolling(20).mean()
    
    yearly_df = df.tail(252)
    hh_val = float(yearly_df['High'].max())
    hh_idx = yearly_df['High'].idxmax()
    hh_pos = df.index.get_loc(hh_idx)
    
    search_start = max(0, hh_pos - 252)
    candidates = []

    for i in range(search_start + 8, hh_pos - 5):
        low_val = float(df['Low'].iloc[i])
        if low_val == df['Low'].iloc[i-8:i+9].min():
            v_score = 1.0
            if df['Volume'].iloc[i] > df['Vol_MA20'].iloc[i] * 1.5: v_score += 1.0
            if df['Effort_Ratio'].iloc[i] > df['Eff_MA20'].iloc[i] * 2.0: v_score += 1.0
            
            recent_high = df['High'].iloc[i-15:i].max()
            future_window = df.iloc[i:min(i+35, hh_pos)]
            if not future_window.empty:
                if future_window['High'].max() > recent_high or (future_window['High'].max() - low_val) / low_val > 0.09:
                    candidates.append({'date': df.index[i], 'price': low_val, 'score': v_score})

    if not candidates: return None

    final_hls = []
    for c in sorted(candidates, key=lambda x: x['date']):
        final_hls = [h for h in final_hls if h['price'] < c['price']]
        if not final_hls or (c['date'] - final_hls[-1]['date']).days > 20:
            final_hls.append(c)
        else:
            if c['price'] < final_hls[-1]['price']: final_hls[-1] = c

    significant_lows = [l for l in final_hls if (hh_val - l['price']) / l['price'] >= 0.10]
    return {'hh': {'date': hh_idx, 'price': hh_val}, 'hls': significant_lows}

# =============================================================================
# SEKCHJA 3: POBIERANIE DANYCH I FILTRY (FA-42: FA-43 do FA-49)
# =============================================================================

def fetch_ticker_data(ticker, period='2y', interval='1d'):
    try:
        # FA-44: Walidacja trendu na interwale tygodniowym
        if interval == '1d':
            w_data = yf.download(ticker, period='5y', interval='1wk', progress=False)
            if not w_data.empty and len(w_data) >= 200:
                if isinstance(w_data.columns, pd.MultiIndex):
                    w_data.columns = w_data.columns.get_level_values(0)
                
                w_sma200 = w_data['Close'].rolling(window=200).mean().iloc[-1]
                if float(w_data['Close'].iloc[-1]) < float(w_sma200):
                    return ticker, None

        # Pobieranie danych głównych
        data = yf.download(ticker, period=period, interval=interval, progress=False)
        if data.empty: return ticker, None
        
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        struct = find_all_significant_lows(data)
        if struct:
            struct['clusters'] = find_clusters(struct)
            last_close = float(data['Close'].iloc[-1])
            
            # FA-21/FA-43: SMA 200
            sma200_series = data['Close'].rolling(window=200).mean()
            if sma200_series.isna().iloc[-1]: return ticker, None
            sma200 = float(sma200_series.iloc[-1])
            
            if last_close < sma200:
                return ticker, None
            
            # --- FEATURE ENGINEERING (FA-42) ---
            
            # FA-45: ATR 14
            high_low = data['High'] - data['Low']
            high_pc = abs(data['High'] - data['Close'].shift())
            low_pc = abs(data['Low'] - data['Close'].shift())
            tr = pd.concat([high_low, high_pc, low_pc], axis=1).max(axis=1)
            atr_val = float(tr.rolling(window=14).mean().iloc[-1])

            # FA-46: RSI 14
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi_val = float(100 - (100 / (1 + rs)).iloc[-1])

            # FA-47: Odległość od SMA 200 (%)
            dist_val = float((last_close - sma200) / sma200 * 100)

            # FA-48: Nachylenie SMA 200
            slope_val = 0.0
            if len(sma200_series) >= 6:
                prev_sma200 = float(sma200_series.iloc[-6])
                slope_val = float((sma200 - prev_sma200) / prev_sma200 * 100)

            # FA-49: Budowa wektora danych (Dataset Builder) - Zoptymalizowana precyzja
            struct['data_vector'] = {
                'ticker': ticker,
                'last_price': round(last_close, 2),
                'sma200': round(sma200, 2),
                'sma200_dist_pct': round(dist_val, 2),
                'sma200_slope_pct': round(slope_val, 4),
                'rsi_14': round(rsi_val, 2),
                'atr_14': round(atr_val, 2),
                'n_hls': len(struct['hls']),
                'max_cluster_score': round(struct['clusters'][0]['total_score'], 1) if struct['clusters'] else 0
            }
            
            struct['trend'] = 'Wzrostowy'

            # Generowanie sygnałów do UI
            signals = []
            active_zones = [z for z in struct['clusters'] if z['avg_price'] < last_close]
            
            if active_zones:
                main_z = active_zones[0]
                dist_to_fibo = (last_close - main_z['avg_price']) / last_close * 100
                status = 'EKSTREMALNA' if main_z['total_score'] >= 8 else 'SILNA' if main_z['total_score'] >= 5 else 'STANDARDOWA'
                signals.append(f"Najbliższa strefa: {main_z['avg_price']:.2f} ({status})")
                signals.append(f"Dystans: {dist_to_fibo:.1f}%")
                fibo_names = {l['type'] for l in main_z['levels']}
                signals.append(f"Poziomy: {', '.join(fibo_names)}")
            else:
                signals.append('Brak aktywnych stref wsparcia.')
            
            struct['signals'] = signals
            data.attrs['structure'] = struct
            
        return ticker, data
    except Exception as e:
        return ticker, None