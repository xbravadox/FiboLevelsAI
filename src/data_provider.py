import yfinance as yf
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_fib_levels(start_price, end_price, start_date):
    '''
    Wylicza poziomy Fibo dla konkretnego impulsu.
    Dodajemy wagę (weight) do każdego poziomu, aby zróżnicować ich znaczenie.
    '''
    diff = end_price - start_price
    return {
        '38.2%': {'price': end_price - diff * 0.382, 'date': start_date, 'weight': 1.0},
        '50.0%': {'price': end_price - diff * 0.500, 'date': start_date, 'weight': 1.2},
        '61.8%': {'price': end_price - diff * 0.618, 'date': start_date, 'weight': 1.5}, # Złote cięcie
        '78.6%': {'price': end_price - diff * 0.786, 'date': start_date, 'weight': 1.5}  # Głębokie zniesienie
    }

def find_clusters(structure):
    '''
    Szuka klastrów, agreguje bliskie poziomy w strefy i nadaje im wagę.
    Poprawiona precyzja: agresywniejsze filtrowanie szerokości stref.
    '''
    all_levels = []
    hh_price = structure['hh']['price']
    
    for hl in structure['hls']:
        levels_dict = get_fib_levels(hl['price'], hh_price, hl['date'])
        for name, data in levels_dict.items():
            # Wynik poziomu to bazowy score dołka * waga poziomu Fibo
            level_score = hl.get('score', 1.0) * data['weight']
            all_levels.append({
                'price': data['price'], 
                'from_hl': hl['price'], 
                'date': data['date'],
                'type': name,
                'score': level_score
            })
    
    all_levels.sort(key=lambda x: x['price'])
    
    # 1. Tworzenie bazowych klastrów (bardzo ciasne skupiska < 0.5%)
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
            min_p = min(c['price'] for c in current_cluster)
            max_p = max(c['price'] for c in current_cluster)
            
            clusters.append({
                'avg_price': avg_price,
                'min_price': min_p,
                'max_price': max_p,
                'count': len(current_cluster),
                'total_score': total_score,
                'levels': sorted(current_cluster, key=lambda x: x['date'])
            })
        i = j

    if not clusters: return []
    
    # 2. AGREGACJA W STREFY (zredukowano z 2% do 1.2% dla lepszej precyzji)
    zones = []
    clusters.sort(key=lambda x: x['avg_price'])
    
    i = 0
    while i < len(clusters):
        current_zone = [clusters[i]]
        j = i + 1
        # 1.2% to kompromis między precyzją a łączeniem istotnych punktów
        while j < len(clusters) and (clusters[j]['avg_price'] - clusters[i]['avg_price']) / clusters[i]['avg_price'] < 0.012:
            current_zone.append(clusters[j])
            j += 1
        
        z_min = min(c['min_price'] for c in current_zone)
        z_max = max(c['max_price'] for c in current_zone)
        z_avg = (z_min + z_max) / 2
        z_score = sum(c['total_score'] for c in current_zone)
        z_count = sum(c['count'] for c in current_zone)
        
        z_levels = []
        for c in current_zone:
            z_levels.extend(c['levels'])
        
        zones.append({
            'avg_price': z_avg,
            'min_price': z_min,
            'max_price': z_max,
            'total_score': z_score,
            'total_count': z_count,
            'levels': sorted(z_levels, key=lambda x: x['price'])
        })
        i = j
        
    return sorted(zones, key=lambda x: x['total_score'], reverse=True)

def find_all_significant_lows(df):
    '''Szukanie dołków z analizą Wyckoffa i resetem struktury.'''
    if df is None or len(df) < 252: return None
    
    df = df.copy()
    df['Vol_MA20'] = df['Volume'].rolling(20).mean()
    df['Price_Range'] = df['High'] - df['Low']
    df['Effort_Ratio'] = df['Volume'] / df['Price_Range'].replace(0, np.nan)
    df['Eff_MA20'] = df['Effort_Ratio'].rolling(20).mean()
    
    yearly_df = df.tail(252)
    hh_val = yearly_df['High'].max()
    hh_idx = yearly_df['High'].idxmax()
    hh_pos = df.index.get_loc(hh_idx)
    
    search_start = max(0, hh_pos - 252)
    candidates = []

    for i in range(search_start + 8, hh_pos - 5):
        low_val = df['Low'].iloc[i]
        if low_val == df['Low'].iloc[i-8:i+9].min():
            v_score = 1.0
            # Premia za wolumen (Wyckoff Effort)
            if df['Volume'].iloc[i] > df['Vol_MA20'].iloc[i] * 1.5:
                v_score += 1.0
            if df['Effort_Ratio'].iloc[i] > df['Eff_MA20'].iloc[i] * 2.0:
                v_score += 1.0
            
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
            if c['price'] < final_hls[-1]['price']:
                final_hls[-1] = c

    significant_lows = [l for l in final_hls if (hh_val - l['price']) / l['price'] >= 0.10]
    return {'hh': {'date': hh_idx, 'price': hh_val}, 'hls': significant_lows}

def fetch_ticker_data(ticker, period='2y', interval='1d'):
    try:
        data = yf.Ticker(ticker).history(period=period, interval=interval)
        if data.empty: return ticker, None
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        struct = find_all_significant_lows(data)
        if struct:
            struct['clusters'] = find_clusters(struct)
            
            # --- WYZNACZANIE TRENDU I SYGNAŁÓW ---
            last_close = float(data['Close'].iloc[-1])
            sma200 = data['Close'].rolling(window=200).mean().iloc[-1]
            
            # 1. Trend (tylko dla informacji, skanujemy i tak wszystko pod kątem stref)
            struct['trend'] = 'Wzrostowy' if last_close > sma200 else 'Spadkowy'
            
            # 2. Sygnały
            signals = []
            active_zones = [z for z in struct['clusters'] if z['avg_price'] < last_close]
            
            if active_zones:
                main_z = active_zones[0]
                dist = (last_close - main_z['avg_price']) / last_close * 100
                
                # Dynamiczna ocena jakości strefy
                if main_z['total_score'] >= 8: status = "EKSTREMALNA (BETON)"
                elif main_z['total_score'] >= 5: status = "BARDZO SILNA"
                else: status = "STANDARDOWA"
                
                signals.append(f"Najbliższa strefa: {main_z['avg_price']:.2f} ({status})")
                signals.append(f"Dystans do wsparcia: {dist:.1f}%")
                
                # Szczegóły techniczne
                fibo_names = [l['type'] for l in main_z['levels'][:3]]
                signals.append(f"Główne poziomy: {', '.join(set(fibo_names))}")
            else:
                signals.append("Brak aktywnych stref wsparcia poniżej ceny.")
            
            struct['signals'] = signals
            
        data.attrs['structure'] = struct
        return ticker, data
    except Exception as e:
        return ticker, None