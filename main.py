import streamlit as st
import time
import logging
import yfinance as yf
from src.utils import load_presets, save_preset, delete_preset
from src.data_provider import fetch_ticker_data
from src.components_html import get_card_styles, render_ticker_card

# =============================================================================
# SEKCHJA 1: KONFIGURACJA I STYLE
# =============================================================================

logging.getLogger('yfinance').setLevel(logging.CRITICAL)

st.set_page_config(
    page_title='FiboLevels AI',
    page_icon='📈',
    layout='wide',
    initial_sidebar_state='expanded'
)

st.markdown(get_card_styles(), unsafe_allow_html=True)

st.markdown('''
<style>
    .block-container {
        max-width: 100% !important;
        padding-left: 5rem !important;
        padding-right: 5rem !important;
    }
    [data-testid="stMarkdownContainer"] > div {
        display: flex !important;
        justify-content: center !important;
        width: 100% !important;
    }
</style>
''', unsafe_allow_html=True)

if 'last_cost' not in st.session_state: st.session_state.last_cost = 0.0
if 'total_cost' not in st.session_state: st.session_state.total_cost = 0.0

# =============================================================================
# SEKCHJA 2: LOGIKA POMOCNICZA UI
# =============================================================================

def update_fields():
    sel = st.session_state.preset_selector
    presets = load_presets()
    if sel != 'Własne...':
        st.session_state.input_name = sel
        st.session_state.input_tickers = ', '.join(presets[sel])
    else:
        st.session_state.input_name = ''
        st.session_state.input_tickers = ''

# =============================================================================
# SEKCHJA 3: GŁÓWNA APLIKACJA
# =============================================================================

def main():
    if 'input_name' not in st.session_state: st.session_state.input_name = ''
    if 'input_tickers' not in st.session_state: st.session_state.input_tickers = ''

    st.title('📈 FiboLevels AI')
    st.subheader('Asystent Analizy Technicznej D1 (Long Only)')

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown('### 🔑 Konfiguracja i Koszty')
        st.text_input('OpenAI API Key', type='password', key='api_key')
        
        c_cost1, c_cost2 = st.columns(2)
        c_cost1.metric('Ostatni', f'${st.session_state.last_cost:.4f}')
        c_cost2.metric('Suma', f'${st.session_state.total_cost:.4f}')
        
        st.divider()
        tab_presets, tab_params = st.tabs(['📁 Presety', '⚙️ Parametry'])

        with tab_presets:
            presets = load_presets()
            st.selectbox('Wybierz preset', ['Własne...'] + sorted(list(presets.keys())), key='preset_selector', on_change=update_fields)
            st.text_area('Tickery', key='input_tickers', height=100)
            st.text_input('Nazwa nowego', key='input_name')
            col_s, col_d = st.columns(2)
            with col_s: st.button('💾 Zapisz', width='stretch', on_click=lambda: save_preset(st.session_state.input_name, st.session_state.input_tickers))
            with col_d:
                if st.session_state.preset_selector != 'Własne...':
                    st.button('🗑️ Usuń', width='stretch', on_click=lambda: delete_preset(st.session_state.preset_selector))

        with tab_params:
            period = st.selectbox('Zakres danych', ['1y', '2y', '5y', 'max'], index=2)
            interval = st.radio('Interwał', ['1d', '1wk'], horizontal=True)
            st.slider('Min. Prob (%)', 0.0, 1.0, 0.55, step=0.01, key='min_prob')

        st.divider()
        start_scan = st.button('🚀 URUCHOM SKANER', width='stretch')

    # --- LOGIKA SKANERA ---
    if start_scan:
        tickers = [t.strip().upper() for t in st.session_state.input_tickers.replace('\n', ',').split(',') if t.strip()]
        if not tickers:
            st.error('Podaj symbole!')
            return

        with st.spinner('Skanowanie i weryfikacja trendu...'):
            results = {t: fetch_ticker_data(t, period=period, interval=interval) for t in tickers}
            
        st.divider()

        no_zones = [] # Listy na potrzeby precyzyjnego raportowania pod kartami
        low_prob = []

        # 1. NAJPIERW: Wyświetlanie kart dla zaakceptowanych spółek
        for t, (symbol, df) in results.items():
            if df is not None:
                struct = df.attrs.get('structure')
                if struct:
                    try:
                        last_price = float(df['Close'].iloc[-1])
                        clusters = struct.get('clusters', [])
                        active_zones = [z for z in clusters if z['avg_price'] < last_price]
                        main_zone = active_zones[0] if active_zones else None
                        
                        if main_zone:
                            prob_pct = main_zone['total_score'] * 10
                            
                            if (prob_pct / 100.0) >= st.session_state.min_prob:
                                card_data = {
                                    'ticker': t,
                                    'timestamp': time.strftime('%H:%M:%S'),
                                    'prob': prob_pct, 
                                    'strength': main_zone['total_score'],
                                    'price': last_price,
                                    'interval_short': interval,
                                    'n_samples': len(df),
                                    'fibo': main_zone['avg_price'],
                                    'label_low': 'Dół Strefy',
                                    'fibo_low': main_zone['min_price'],
                                    'label_high': 'Góra Strefy',
                                    'fibo_high': main_zone['max_price'],
                                    'ai_desc': struct.get('signals', [])
                                }
                                st.markdown(render_ticker_card(card_data), unsafe_allow_html=True)
                            else:
                                low_prob.append(f"{t} ({prob_pct:.0f}%)")
                        else:
                            no_zones.append(t)
                            
                    except Exception as e:
                        st.error(f"Błąd renderowania {t}: {e}")

        # 2. NA KONIEC: Zbiorcze raporty pod kartami
        st.divider()
        
        # Trend spadkowy (to co odrzucił fetch_ticker_data)
        rejected = [t for t, res in results.items() if res[1] is None]
        if rejected:
            st.warning(f"📉 **Trend spadkowy (SMA200 D1/W1):** {', '.join(rejected)}")
        
        # Brak stref pod ceną
        if no_zones:
            st.info(f"🔍 **Brak stref Fibo poniżej ceny:** {', '.join(no_zones)}")
            
        # Zbyt niskie prawdopodobieństwo względem suwaka
        if low_prob:
            st.info(f"⚖️ **Zbyt niskie prawdopodobieństwo:** {', '.join(low_prob)}")
            
    else:
        st.info('Wybierz spółki i uruchom skaner.')

if __name__ == '__main__':
    main()