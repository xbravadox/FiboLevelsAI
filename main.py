import streamlit as st

def main():
    st.set_page_config(
        page_title='FiboLevels AI',
        page_icon='📈',
        layout='wide',
        initial_sidebar_state='expanded'
    )

    st.title('📈 FiboLevels AI')
    st.subheader('Asystent Analizy Technicznej D1 (Long Only)')

    # Sidebar - przygotowanie pod Zadanie 1.2
    with st.sidebar:
        st.header('Ustawienia')
        st.info('Tu pojawi się zarządzanie presetami.')

    st.write('### Status Skanera')
    st.info('Aplikacja zainicjalizowana. Gotowa do konfiguracji filtrów i ML.')

if __name__ == '__main__':
    main()