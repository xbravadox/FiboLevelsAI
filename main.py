import streamlit as st
import time
import logging
import yfinance as yf
from src.utils import load_presets, save_preset, delete_preset
from src.data_provider import get_bulk_data
from src.components_html import get_card_styles, render_ticker_card

logging.getLogger('yfinance').setLevel(logging.CRITICAL)

st.set_page_config(
    page_title='FiboLevels AI',
    page_icon='📈',
    layout='wide',
    initial_sidebar_state='expanded'
)

st.markdown(get_card_styles(), unsafe_allow_html=True)

if 'last_cost' not in st.session_state: st.session_state.last_cost = 0.0
if 'total_cost' not in st.session_state: st.session_state.total_cost = 0.0

def update_fields():
    sel = st.session_state.preset_selector
    presets = load_presets()
    if sel != 'Własne...':
        st.session_state.input_name = sel
        st.session_state.input_tickers = ', '.join(presets[sel])
    else:
        st.session_state.input_name = ''
        st.session_state.input_tickers = ''

def on_save_clicked():
    name = st.session_state.input_name
    tickers = st.session_state.input_tickers
    if name and tickers:
        save_preset(name, tickers)
        st.session_state.input_name = ''
        st.session_state.input_tickers = ''
        st.session_state.preset_selector = 'Własne...'
        st.toast(f'Zapisano preset: {name}')
    else: st.error('Podaj nazwę i tickery!')

def on_delete_clicked():
    sel = st.session_state.preset_selector
    if sel != 'Własne...':
        delete_preset(sel)
        st.session_state.input_name = ''
        st.session_state.input_tickers = ''
        st.session_state.preset_selector = 'Własne...'
        st.warning(f'Usunięto preset: {sel}')

def main():
    if 'input_name' not in st.session_state: st.session_state.input_name = ''
    if 'input_tickers' not in st.session_state: st.session_state.input_tickers = ''

    st.title('📈 FiboLevels AI')
    st.subheader('Asystent Analizy Technicznej D1 (Long Only)')

    with st.sidebar:
        st.markdown('### 🔑 Konfiguracja i Koszty')
        st.text_input('OpenAI API Key', type='password', key='api_key', help='Klucz API OpenAI (GPT-4o).')
        
        c_cost1, c_cost2 = st.columns(2)
        c_cost1.metric('Ostatni', f'${st.session_state.last_cost:.4f}')
        c_cost2.metric('Suma', f'${st.session_state.total_cost:.4f}')
        
        st.divider()

        tab_presets, tab_params = st.tabs(['📁 Presety', '⚙️ Ustawienia skanera'])

        with tab_presets:
            presets = load_presets()
            sorted_preset_names = sorted(list(presets.keys()))
            
            st.selectbox(
                'Wybierz preset', 
                ['Własne...'] + sorted_preset_names,
                key='preset_selector', 
                on_change=update_fields,
                help='Wybierz zestaw spółek.'
            )
            
            st.text_area('Tickery', key='input_tickers', height=100, help='Symbole oddzielone przecinkami.')
            st.text_input('Nazwa nowego', key='input_name', placeholder='Wpisz nazwę...', help='Zapisz aktualną listę.')
            
            col_s, col_d = st.columns(2)
            with col_s: st.button('💾 Zapisz', width='stretch', on_click=on_save_clicked)
            with col_d:
                if st.session_state.preset_selector != 'Własne...':
                    st.button('🗑️ Usuń', width='stretch', on_click=on_delete_clicked)

        with tab_params:
            period = st.selectbox('Zakres danych', ['1y', '2y', '5y', 'max'], index=2, help='Głębokość historii.')
            interval = st.radio('Interwał', ['1d', '1wk'], horizontal=True)
            st.slider('Min. ML Prob (%)', 0, 100, 55, key='min_prob')

        st.divider()
        start_scan = st.button('🚀 URUCHOM SKANER', width='stretch')

    if start_scan:
        if not st.session_state.input_tickers:
            st.error('Lista tickerów jest pusta!')
        else:
            tickers = [t.strip().upper() for t in st.session_state.input_tickers.replace('\n', ',').split(',') if t.strip()]
            start_time = time.time()
            with st.spinner(f'Skanowanie {len(tickers)}...'):
                raw_data = get_bulk_data(tickers, period=period, interval=interval)
                duration = time.time() - start_time
                
                if raw_data:
                    bullish_results = {t: df for t, df in raw_data.items() if df.attrs.get('is_bullish')}
                    skipped_count = len(raw_data) - len(bullish_results)
                    
                    st.success(f'Skanowanie ukończone w {duration:.2f}s.')
                    if skipped_count > 0:
                        st.warning(f'Pominięto {skipped_count} spółek z trendem spadkowym (poniżej SMA200).')
                    
                    st.divider()
                    
                    if not bullish_results:
                        st.info('Brak spółek spełniających kryteria trendu wzrostowego.')
                    else:
                        sorted_tickers = sorted(bullish_results.keys())
                        cols = st.columns(2)
                        for i, t in enumerate(sorted_tickers):
                            df = bullish_results[t]
                            with cols[i % 2]:
                                try:
                                    last_price = float(df['Close'].iloc[-1])
                                    sma200_val = df.attrs.get('sma200_val')
                                    sma_str = f'{sma200_val:.2f}' if sma200_val else 'N/A'
                                    
                                    card_data = {
                                        'ticker': t, 
                                        'timestamp': time.strftime('%H:%M:%S'),
                                        'prob': 75,
                                        'price': last_price, 
                                        'trend': 'Wzrostowy',
                                        'interval_short': interval, 
                                        'n_samples': len(df),
                                        'fibo': '0.618',
                                        'label_low': 'SL', 
                                        'fibo_low': last_price * 0.98,
                                        'label_high': 'TP', 
                                        'fibo_high': last_price * 1.05,
                                        'ai_desc': [
                                            f'Cena powyżej SMA200 ({sma_str})',
                                            'Trend wzrostowy potwierdzony.'
                                        ]
                                    }
                                    st.markdown(render_ticker_card(card_data), unsafe_allow_html=True)
                                except Exception as e: st.error(f'Błąd renderowania {t}: {e}')
                else: st.warning('Brak danych.')
    else:
        st.info('Wprowadź tickery w panelu bocznym i uruchom skaner, aby zobaczyć wyniki analizy trendu wzrostowego.')

if __name__ == '__main__':
    main()