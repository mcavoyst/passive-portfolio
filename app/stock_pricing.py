import os
import logging
import requests
from dotenv import load_dotenv

PRICE_API_URL='http://api.marketstack.com/v1/tickers'

logger = logging.getLogger(__name__)
class StockPricer():
    def __init__(self) -> None:
        pass

    def get_price(self, ticker:str, exchange:str) -> str:
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

            close = api_response['close']
            updated = api_response['date']
            return close, updated
        except TimeoutError as e:
            logger.error("Timeout error for %s with error: %s", ticker, e)
            return
        
        except KeyError as e:
            logger.error('Failed to get price for %s with error: %s', ticker, e)
            return