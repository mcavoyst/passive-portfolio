import os
import requests
from dotenv import load_dotenv
import logging
EXCHANGE_API_URL='http://api.exchangeratesapi.io/v1/latest'
import time
from config import ROOT_DIR

logger = logging.getLogger(__name__)
def get_exchange_rate(backup_filepath= 'data/exchange_rate.txt')->float:
    """
    Fetches the current exchange rate from USD to CAD using the Exchange Rates API.
    If the API call fails, it retrieves the exchange rate from a backup file.

    Args:
        backup_filepath (str): The relative path to the backup file containing the exchange rate.

    Returns:
        float: The exchange rate from USD to CAD.

    Raises:
        TimeoutError: If the API request times out.
    """
    load_dotenv()
    abs_backup_filepath = os.path.join(ROOT_DIR, backup_filepath)
    time.sleep(.5)
    params = {
        'access_key': os.getenv('EXCHANGE_API_KEY'),
    }
    try: 
        api_result = requests.get(EXCHANGE_API_URL, params, timeout=20)
        api_response = api_result.json()
        cad = api_response['rates']['CAD']
        usd = api_response['rates']['USD']
        exchange_cad = cad / usd
        str_exc = str(exchange_cad)
        with open(abs_backup_filepath,'w', encoding='utf-8') as f:
            f.write(str_exc)
        return exchange_cad
    except TimeoutError as e:
        logger.error("Error on exchange rate check. Using backup. Error: %s",e)
        with open(abs_backup_filepath,'r', encoding='utf-8') as f:
            exchange_cad = float(f.read())
        return exchange_cad

