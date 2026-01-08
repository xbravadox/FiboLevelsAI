import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch_ticker_data(ticker, period='5y', interval='1d'):
    '''Pobiera dane dla pojedynczego tickera i oblicza wskaźniki.'''
    try:
        ticker_obj = yf.Ticker(ticker)
        data = ticker_obj.history(period=period, interval=interval)
        
        if data.empty:
            return ticker, None
        
        # OBLICZENIE SMA 200 (na czystym DataFrame)
        data['SMA200'] = data['Close'].rolling(window=200).mean()
        
        # Weryfikacja trendu
        if len(data) >= 200:
            last_close = data['Close'].iloc[-1]
            last_sma200 = data['SMA200'].iloc[-1]
            
            # Przypisanie atrybutów trendu
            data.attrs['is_bullish'] = last_close > last_sma200 if pd.notna(last_sma200) else False
            data.attrs['sma200_val'] = last_sma200
        else:
            data.attrs['is_bullish'] = False
            data.attrs['sma200_val'] = None

        return ticker, data
    except Exception:
        return ticker, None

def get_bulk_data(tickers, period='5y', interval='1d', max_workers=10):
    '''Pobiera dane dla listy tickerów równolegle (ThreadPoolExecutor).'''
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(fetch_ticker_data, t, period, interval): t 
            for t in tickers
        }
        for future in as_completed(future_to_ticker):
            ticker, data = future.result()
            if data is not None:
                results[ticker] = data
    return results