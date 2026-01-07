import streamlit as st
import time
import logging
import yfinance as yf
from src.utils import load_presets, save_preset, delete_preset
from src.data_provider import get_bulk_data

# Uciszanie logów yfinance w terminalu
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

# 1. Konfiguracja strony (Zgodnie z Punktem 1 i 6 specyfikacji)
st.set_page_config(
    page_title='FiboLevels AI',
    page_icon='📈',
    layout='wide',
    initial_sidebar_state='expanded'
)

# Inicjalizacja liczników kosztów (Punkt 6.1)
if 'last_cost' not in st.session_state:
    st.session_state.last_cost = 0.0
if 'total_cost' not in st.session_state:
    st.session_state.total_cost = 0.0

def update_fields():
    '''Funkcja wywoływana przy każdej zmianie selectboxa.'''
    sel = st.session_state.preset_selector
    presets = load_presets()
    
    if sel != 'Własne...':
        st.session_state.input_name = sel
        st.session_state.input_tickers = ', '.join(presets[sel])
    else:
        st.session_state.input_name = ''
        st.session_state.input_tickers = ''

def on_save_clicked():
    '''Callback wywoływany w momencie kliknięcia przycisku Zapisz.'''
    name = st.session_state.input_name
    tickers = st.session_state.input_tickers
    if name and tickers:
        save_preset(name, tickers)
        st.session_state.input_name = ''
        st.session_state.input_tickers = ''
        st.session_state.preset_selector = 'Własne...'
        st.toast(f'Zapisano preset: {name}')
    else:
        st.error('Podaj nazwę i tickery!')

def on_delete_clicked():
    '''Callback wywoływany w momencie kliknięcia przycisku Usuń.'''
    sel = st.session_state.preset_selector
    if sel != 'Własne...':
        delete_preset(sel)
        st.session_state.input_name = ''
        st.session_state.input_tickers = ''
        st.session_state.preset_selector = 'Własne...'
        st.warning(f'Usunięto preset: {sel}')

def main():
    # Inicjalizacja stanów sesji
    if 'input_name' not in st.session_state:
        st.session_state.input_name = ''
    if 'input_tickers' not in st.session_state:
        st.session_state.input_tickers = ''

    st.title('📈 FiboLevels AI')
    st.subheader('Asystent Analizy Technicznej D1 (Long Only)')

    # --- SIDEBAR ---
    with st.sidebar:
        st.header('🔑 Konfiguracja AI')
        st.text_input('OpenAI API Key', type='password', key='api_key')
        
        c_cost1, c_cost2 = st.columns(2)
        c_cost1.metric('Ostatni brief', f'${st.session_state.last_cost:.4f}')
        c_cost2.metric('Suma sesji', f'${st.session_state.total_cost:.4f}')
        
        st.divider()
        
        st.header('📁 Zarządzanie Presetami')
        presets = load_presets()
        # SORTOWANIE PRESETÓW: 'Własne...' zawsze na górze, reszta alfabetycznie
        sorted_preset_names = sorted(list(presets.keys()))
        
        st.selectbox(
            'Wybierz preset', 
            ['Własne...'] + sorted_preset_names,
            key='preset_selector', 
            on_change=update_fields,
            help='Wybierz zestaw spółek z listy (posortowane alfabetycznie).'
        )
        
        st.text_area('Tickery (Yahoo Finance)', key='input_tickers', height=120)
        st.text_input('Nazwa nowego presetu', key='input_name', placeholder='Wpisz nazwę...')
        
        col_s, col_d = st.columns(2)
        with col_s:
            st.button('💾 Zapisz', width='stretch', on_click=on_save_clicked)
        with col_d:
            if st.session_state.preset_selector != 'Własne...':
                st.button('🗑️ Usuń', width='stretch', on_click=on_delete_clicked)

        st.divider()
        
        st.header('⚙️ Parametry Skanera')
        period = st.selectbox('Zakres danych (History)', ['1y', '2y', '5y', 'max'], index=2)
        interval = st.radio('Interwał świecy', ['1d', '1wk'], horizontal=True)
        st.slider('Min. ML Prob (%)', 0, 100, 55, key='min_prob')

        st.divider()
        start_scan = st.button('🚀 URUCHOM SKANER', width='stretch')

    # --- LOGIKA SKANOWANIA ---
    if start_scan:
        if not st.session_state.input_tickers:
            st.error('Lista tickerów jest pusta!')
        else:
            tickers = [t.strip().upper() for t in st.session_state.input_tickers.replace('\n', ',').split(',') if t.strip()]
            
            start_time = time.time()
            
            with st.spinner(f'Skanowanie {len(tickers)} spółek...'):
                raw_data = get_bulk_data(tickers, period=period, interval=interval)
                
                duration = time.time() - start_time
                
                if raw_data:
                    st.success(f'Pobrano {len(raw_data)} z {len(tickers)} tickerów w {duration:.2f}s.')
                    st.divider()
                    
                    # Sortowanie spółek na ekranie (Zadanie 1.3)
                    sorted_tickers = sorted(raw_data.keys())
                    cols = st.columns(4)
                    for i, t in enumerate(sorted_tickers):
                        df = raw_data[t]
                        with cols[i % 4]:
                            try:
                                # Odporne pobieranie ceny
                                last_price = float(df['Close'].tail(1).values[0])
                                st.metric(label=t, value=f'{last_price:.2f}')
                            except (IndexError, TypeError, ValueError, KeyError):
                                st.error(f'Brak danych: {t}')
                else:
                    st.warning('Nie udało się pobrać danych.')

if __name__ == '__main__':
    main()