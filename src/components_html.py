def get_status_class(prob):
    if prob >= 70: return 'status-high'
    elif prob >= 60: return 'status-mid'
    return 'status-low'

def format_pl(value, precision=2):
    try:
        if value is None: return '0,00'
        if isinstance(value, str):
            value = float(value.replace(' ', '').replace(',', '.'))
        final_precision = 4 if 0 < abs(value) < 1 else precision
        formatted = f'{value:,.{final_precision}f}'
        return formatted.replace(',', ' ').replace('.', ',').replace(' ', '.')
    except: return value

def get_card_styles():
    return '''<style>
/* Optymalizacja Sidebaru - zagęszczenie treści */
[data-testid="stSidebar"] > div:first-child { padding-top: 2rem; }
[data-testid="stSidebar"] .stMarkdown h1, 
[data-testid="stSidebar"] .stMarkdown h2, 
[data-testid="stSidebar"] .stMarkdown h3 { margin-bottom: 0.5rem; padding-top: 0.5rem; }
[data-testid="stSidebar"] .stVerticalBlock { gap: 0.5rem; }
.stDivider { margin-top: 1rem !important; margin-bottom: 1rem !important; }

/* Style kart wyników */
.fibo-container { width: 100%; padding: 5px; box-sizing: border-box; }
.fibo-card { background-color: #1e1e1e; border-radius: 12px; padding: 20px; color: #ffffff; border-left: 10px solid; box-shadow: 0 6px 15px rgba(0,0,0,0.5); width: 100%; position: relative; margin-bottom: 20px; }
.status-high { border-color: #28a745; }
.status-mid { border-color: #ffc107; }
.status-low { border-color: #6c757d; }
.card-header { display: flex; justify-content: space-between; margin-bottom: 15px; }
.ticker-name { font-size: 1.8rem; font-weight: bold; color: #00d4ff; margin: 0; }
.prob-value { font-size: 2.5rem; font-weight: 900; line-height: 1; }
.grid-top { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; background: #2d2d2d; padding: 15px; border-radius: 10px 10px 0 0; border-bottom: 1px solid #3d3d3d; }
.grid-bottom { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; background: #2d2d2d; padding: 15px; border-radius: 0 0 10px 10px; margin-bottom: 15px; }
.stat-item { text-align: center; }
.stat-label { font-size: 0.7rem; color: #999; text-transform: uppercase; margin-bottom: 3px; display: block; }
.stat-value { font-size: 1.1rem; font-weight: bold; color: #fff; }
.trend-dot { height: 8px; width: 8px; border-radius: 50%; display: inline-block; margin-left: 5px; }
.dot-up { background-color: #28a745; box-shadow: 0 0 5px #28a745; }
.dot-down { background-color: #dc3545; box-shadow: 0 0 5px #dc3545; }
.ai-section { background: #252525; border-left: 5px solid #007bff; padding: 15px; border-radius: 0 6px 6px 0; }
.ai-header { color: #007bff; text-transform: uppercase; font-weight: bold; font-size: 0.9rem; }
.ai-content { font-size: 0.95rem; color: #f0f0f0; margin-top: 8px; list-style-type: disc; margin-left: 20px; padding-left: 0; }
</style>'''

def render_ticker_card(data):
    status_class = get_status_class(data.get('prob', 0))
    trend = data.get('trend', 'Brak')
    dot_class = 'dot-up' if trend == 'Wzrostowy' else 'dot-down'
    items = data.get('ai_desc', [])
    list_items = ''.join(f'<li>{item}</li>' for item in items)
    
    return f'''<div class='fibo-container'><div class='fibo-card {status_class}'><div class='card-header'><div><div class='ticker-name'>{data.get('ticker', 'N/A')}</div><div style='color: #888; font-size: 0.8rem;'>Analiza: {data.get('timestamp')}</div></div><div style='text-align: right;'><span style='color: #aaa; font-size: 0.7rem; text-transform: uppercase;'>Prawdopodobieństwo</span><br><span class='prob-value'>{data.get('prob', 0)}%</span></div></div><div class='grid-top'><div class='stat-item'><span class='stat-label'>Cena Akt.</span><span class='stat-value'>{format_pl(data.get('price'))}</span></div><div class='stat-item'><span class='stat-label'>Trend</span><span class='stat-value'>{trend}<span class='trend-dot {dot_class}'></span></span></div><div class='stat-item'><span class='stat-label'>Interwał</span><span class='stat-value'>{data.get('interval_short')}</span></div><div class='stat-item'><span class='stat-label'>Liczba Testów</span><span class='stat-value'>{data.get('n_samples')}</span></div></div><div class='grid-bottom'><div class='stat-item'><span class='stat-label'>Poziom Fibo</span><span class='stat-value'>{data.get('fibo')}</span></div><div class='stat-item'><span class='stat-label'>{data.get('label_low')}</span><span class='stat-value'>{format_pl(data.get('fibo_low'))}</span></div><div class='stat-item'><span class='stat-label'>{data.get('label_high')}</span><span class='stat-value'>{format_pl(data.get('fibo_high'))}</span></div></div><div class='ai-section'><strong class='ai-header'>Analiza AI / Ostrzeżenia</strong><ul class='ai-content'>{list_items}</ul></div></div></div>'''