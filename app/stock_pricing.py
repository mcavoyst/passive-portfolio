import os
import logging
import requests
import json
from config import ROOT_DIR
from dotenv import load_dotenv

PRICE_API_URL='http://api.marketstack.com/v1/tickers'

logger = logging.getLogger(__name__)
class StockPricer():
    """
    A class to retrieve the latest stock prices using the MarketStack API.

    Methods:
    --------
    get_price(ticker: str, exchange: str) -> str:
        Fetches the latest closing price and update date for a given stock ticker 
        and exchange. Handles different exchange formats and logs the process.

    Usage:
    ------
    1. Ensure the `PRICE_API_KEY` environment variable is set with a valid API key.
    2. Call `get_price` with the stock ticker and exchange as arguments.
    3. Returns the closing price and the last updated date if successful, or logs 
       an error if the request fails.
    """

    def __init__(self) -> None:
        pass

    def get_price(self, ticker:str, exchange:str) -> tuple:
        logger.debug('Getting price for %s on %s', ticker, exchange)
        load_dotenv()
        params = {
            'access_key': os.environ.get('PRICE_API_KEY')
        }
        if exchange.upper() == "ARCX":
            ticker_exchange = ticker
        elif exchange.upper() == 'XNYS':
            ticker_exchange = ticker
        else:
            ticker_exchange = f"{ticker.upper()}.{exchange.upper()}"
        try:
            logger.debug('Getting price for %s on %s', ticker, exchange)
            api_result = requests.get(f'{PRICE_API_URL}/{ticker_exchange}/eod/latest',params, timeout=30)
            logger.info('Received %s response for  %s', api_result.status_code, ticker_exchange)
            api_response = api_result.json()

            with open(os.path.join(ROOT_DIR,'tmp', f'{ticker}.json'), "w") as f:
                json.dump(api_response, f, indent=4)

            close = api_response['close']
            updated = api_response['date']
            return close, updated
        except TimeoutError as e:
            logger.error("Timeout error for %s with error: %s", ticker, e)
            return
        
        except KeyError as e:
            logger.error('Failed to get price for %s with error: %s', ticker, e)
            return