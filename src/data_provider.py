import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch_ticker_data(ticker, period='5y', interval='1d'):
    '''Pobiera dane dla pojedynczego tickera w izolacji.'''
    try:
        # Dodajemy group_by='ticker' i wątek pobiera tylko JEDEN ticker
        ticker_obj = yf.Ticker(ticker)
        data = ticker_obj.history(period=period, interval=interval)
        
        if data.empty:
            return ticker, None
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