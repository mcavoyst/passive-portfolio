#!/usr/bin/env python3

import logging
import warnings
from dotenv import load_dotenv
from portfolio import Portfolio
from tabulate import tabulate
warnings.filterwarnings("ignore")

DATA_FILE = 'data/portfolio_data.csv'

logging.basicConfig(
    level=logging.DEBUG, 
    filename='logs/app.log',
    format='%(asctime)s - %(name)s - %(levelname)s - Line: %(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filemode='w'
)

logger = logging.getLogger(__name__)

def main():
    """
    The main entry point for the application. Handles user interaction, portfolio 
    updates, and data display. Allows the user to choose if they want to update stock 
    prices, update stock quantities, and generate a no-sell report.
    """
    load_dotenv()

    check_file =input("Do you want to update the prices? (y/n) ").lower()
    if check_file == 'y':
        try:
            p = Portfolio(DATA_FILE, update_prices=True)
        except ValueError as e:
            logger.error('Issue with the API. Cannot update. %s', e)
            print("Issue with the API. Cannot update")
    else:
        p = Portfolio(DATA_FILE, update_prices=False)
    print(f"\nUpdated as of {p.portfolio.update_date.max()}")
    
    updating = True
    print(tabulate(p.portfolio.filter(['ticker','quantity','closing_price','update_date','total_value','currency']).sort_values(by='total_value', ascending=False),
                    headers="keys", tablefmt="pretty"))

    while(updating):
        stock = input('\nWhich stock do you want to update? If none, type "*"').upper()
        if stock == "*":
            updating = False
        elif stock in p.portfolio.index.tolist():
            try:
                quantity = int(input('What is the new total?'))
                p.update_quantity(ticker=stock, quantity=quantity)
            except TypeError as e:
                logger.warning('Quantity is not entered as integer %s', e)
                continue
            except KeyError:
                print("Try again. Invalid entry")
                continue
        else:
            print('Invalid entry, that ticker is not currently in the portfolio')

    p.no_sell_report()

    print('\nDo you have money you want to invest?')
    
    running = True
    while running:
        invest = input('If yes, type the amount. If no, type "n" ').lower()
        if invest == 'n':
            running = False
            break
        else:
            try:
                invest = float(invest)
                p.spend_money_scenario(invest)
                running = False
            except ValueError as e:
                logger.warning('Investment amount is not entered as float %s', e)
                print("Invalid entry. Investment amount must be a number")
    
    save_file = input('\nDo you want to save and overwrite? (y/n) ').lower()
    if save_file == 'y':
        p.save_portfolio()

if __name__ == '__main__':
    main()