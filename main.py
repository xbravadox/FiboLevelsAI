import streamlit as st
from src.utils import load_presets, save_preset, delete_preset

# 1. Konfiguracja strony
st.set_page_config(
    page_title='FiboLevels AI',
    page_icon='📈',
    layout='wide',
    initial_sidebar_state='expanded'
)

def update_fields():
    '''Funkcja wywoływana przy zmianie selectboxa.'''
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
        # Czyścimy stan ZANIM widgety zostaną ponownie wyrenderowane
        st.session_state.input_name = ''
        st.session_state.input_tickers = ''
        st.session_state.preset_selector = 'Własne...'
        st.toast(f'Zapisano preset: {name}') # Toast jest subtelniejszy niż success przy rerun
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

def main():
    # Inicjalizacja stanów sesji
    if 'input_name' not in st.session_state:
        st.session_state.input_name = ''
    if 'input_tickers' not in st.session_state:
        st.session_state.input_tickers = ''

    st.title('📈 FiboLevels AI')
    st.subheader('Asystent Analizy Technicznej D1 (Long Only)')

    # --- SIDEBAR: ZARZĄDZANIE PRESETAMI ---
    with st.sidebar:
        st.header('Zarządzanie Presetami')
        
        presets = load_presets()
        
        st.selectbox(
            'Wybierz preset', 
            ['Własne...'] + list(presets.keys()),
            key='preset_selector',
            on_change=update_fields,
            help='Wybierz istniejący zestaw spółek lub "Własne...", aby dodać nowy.'
        )
        
        # Widgety powiązane bezpośrednio ze stanem sesji
        st.text_input('Nazwa presetu', key='input_name', placeholder='Wpisz nazwę, aby zapisać...')
        st.text_area(
            'Tickery', 
            key='input_tickers',
            height=150,
            help='Wprowadź symbole oddzielone przecinkami (Yahoo Finance).',
            placeholder='AAPL, MSFT, TSLA...'
        )
        
        col1, col2 = st.columns(2)
        with col1:
            # Używamy parametru on_click zamiast if st.button
            st.button('Zapisz', width='stretch', on_click=on_save_clicked)
        
        with col2:
            if st.session_state.preset_selector != 'Własne...':
                st.button('Usuń', width='stretch', on_click=on_delete_clicked)

    # --- WIDOK GŁÓWNY ---
    st.divider()
    current_sel = st.session_state.preset_selector
    if current_sel != 'Własne...':
        st.write(f'### Aktywny preset: **{current_sel}**')
        st.info(f'**Symbole do skanowania:** {st.session_state.input_tickers}')
    else:
        st.write('### Tryb własnej listy')
        if st.session_state.input_tickers:
            st.success(f'**Gotowy do skanowania:** {st.session_state.input_tickers}')
        else:
            st.info('Skonfiguruj listę tickerów w panelu bocznym.')

if __name__ == '__main__':
    main()