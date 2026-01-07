import json
import os

PRESETS_PATH = 'data/presets.json'

def load_presets():
    '''Wczytuje wszystkie presety z pliku JSON.'''
    if not os.path.exists(PRESETS_PATH):
        return {}
    with open(PRESETS_PATH, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_preset(name, tickers_str):
    '''Zapisuje listę tickerów pod daną nazwą.'''
    presets = load_presets()
    # Czyszczenie: zamiana nowych linii na przecinki, podział, usunięcie spacji i duplikatów
    tickers_list = [t.strip().upper() for t in tickers_str.replace('\n', ',').split(',') if t.strip()]
    presets[name] = sorted(list(set(tickers_list)))
    
    os.makedirs(os.path.dirname(PRESETS_PATH), exist_ok=True)
    with open(PRESETS_PATH, 'w', encoding='utf-8') as f:
        json.dump(presets, f, indent=4)

def delete_preset(name):
    '''Usuwa wybrany preset z pliku.'''
    presets = load_presets()
    if name in presets:
        del presets[name]
        with open(PRESETS_PATH, 'w', encoding='utf-8') as f:
            json.dump(presets, f, indent=4)
        return True
    return False