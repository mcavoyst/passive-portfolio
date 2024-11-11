import pandas as pd
import numpy as np
from stock_pricing import StockPricer
from exchange_rate import get_exchange_rate
import logging
from tabulate import tabulate
from config import ROOT_DIR
import os

logger = logging.getLogger(__name__)

class Portfolio():
    """
    A class to manage and analyze a financial portfolio.

    Attributes:
        filepath (str): The file path to the portfolio data.
        portfolio (DataFrame): The portfolio data loaded from a CSV file.
        exchange_rate (float): The current exchange rate for currency conversion.
        model_portfolio (DataFrame): The model portfolio data for comparison.
        core_portfolio (DataFrame): The core part of the portfolio.
        satellite_portfolio (DataFrame): The satellite part of the portfolio.
        total_core_portfolio_value (float): Total value of the core portfolio.
        total_satellite_portfolio_value (float): Total value of the satellite portfolio.
        best_stock (DataFrame): The best performing stock for rebalancing.

    Methods:
        save_portfolio(): Saves the current portfolio data to a CSV file.
        update_quantity(ticker, quantity): Updates the quantity of a specific stock in the portfolio.
        update_prices(): Updates the prices of stocks in the portfolio.
        no_sell_report(): Generates a report for rebalancing without selling stocks.

    Private Methods:
        _load_model(): Loads and validates the model portfolio data.
        _core_satellite_portfolio_split(): Splits the portfolio into core and satellite parts.
        _rebalance_calculation(): Calculates the rebalancing quantities and costs.
        _calculate_total_value(): Calculates the total value of the portfolio in CAD.
        _rebalance_no_sell(): Calculates rebalancing without selling stocks.
    """
    def __init__(self, data_filepath: str, update_prices: bool) -> None:
        """
        Initializes the Portfolio object with the given data file, loading the 
        portfolio data, and optionally updating prices based on a flag.
        
        Args:
        - data_filepath (str): The relative path to the portfolio data CSV file.
        - update_prices (bool): Flag to determine whether to update stock prices upon initialization.
        """
        data_filepath = os.path.join(ROOT_DIR, data_filepath)
        logger.info("Initializing Portfolio with filepath: %s", data_filepath)
        self.filepath = data_filepath
        self.portfolio = pd.read_csv(data_filepath, index_col='ticker')
        logger.debug("Loaded portfolio data")
        self.exchange_rate = get_exchange_rate()
        if update_prices:
            logger.info("Updating prices as requested on initialization")
            self.update_prices()
        self._load_model()
        self._calculate_total_value()
        self._core_satellite_portfolio_split()
        self._rebalance_calculation()

    def _load_model(self) -> None:
        """
        Loads the model portfolio from a predefined CSV file and validates the total 
        target allocation across the stocks.
        
        Raises:
        - ValueError: If the sum of target allocations in the model portfolio does not equal 1.00.
        """
        logger.debug("Loading model portfolio")
        model_path = os.path.join(ROOT_DIR, 'data/model_portfolio.csv')
        self.model_portfolio = pd.read_csv(model_path, index_col='ticker')
        total = self.model_portfolio.sum()['target_allocation']
        
        if round(total, 2) != 1.00:
            logger.error("Model portfolio allocations sum to %s, expected 1.00", total)
            raise ValueError("Check allocations in model portfolio")
        else:
            logger.info("Model portfolio allocations validated")

    def save_portfolio(self):
        """
        Saves the current portfolio to the file specified during initialization.
        """
        logger.info("Saving portfolio data to %s", self.filepath)
        self.portfolio.to_csv(self.filepath, index_label='ticker')

    def _core_satellite_portfolio_split(self):
        """
        Splits the portfolio into core and satellite segments based on the model portfolio.
        It also calculates the actual allocation of the core portfolio and updates the 
        core and satellite portfolio values.
        """
        logger.debug("Splitting portfolio into core and satellite")
        self.core_portfolio = self.portfolio.loc[self.model_portfolio.index].copy()
        self.satellite_portfolio = self.portfolio.loc[~self.portfolio.index.isin(self.model_portfolio.index)]
        self.total_core_portfolio_value = self.core_portfolio.total_value.sum()
        self.total_satellite_portfolio_value = self.satellite_portfolio.total_value.sum()
        self.core_portfolio['actual_allocation'] = self.core_portfolio['total_value'] / self.total_core_portfolio_value
        self.core_portfolio = pd.merge(self.core_portfolio, self.model_portfolio, left_index=True, right_index=True)
        
    def _rebalance_calculation(self):
        """
        Calculates the rebalance quantities and costs for the core portfolio. It determines 
        the target quantity of each stock based on the target allocation and calculates 
        the rebalance quantity and cost.
        """
        self.core_portfolio['target_value'] = self.core_portfolio['target_allocation'] * self.total_core_portfolio_value 
        self.core_portfolio['target_quantity'] = self.core_portfolio['target_value']  / self.core_portfolio['closing_price']
        self.core_portfolio['target_quantity']= self.core_portfolio['target_quantity'].apply(np.ceil)
        self.core_portfolio['rebalance_quantity'] = self.core_portfolio['target_quantity'] - self.core_portfolio['quantity']
        self.core_portfolio['rebalancing_cost'] = self.core_portfolio['rebalance_quantity'] * self.core_portfolio['closing_price']

        self.best_stock = self.core_portfolio[self.core_portfolio.rebalancing_cost == self.core_portfolio.rebalancing_cost.min()]

    def update_quantity(self, ticker: str, quantity: int) -> None:
        """
        Updates the quantity of a specific stock in the portfolio by its ticker symbol.
        
        Args:
        - ticker (str): The stock ticker symbol to update.
        - quantity (int): The new quantity to set for the stock.
        """
        logger.debug('Trying to update ticker %s with quantity %s', ticker, quantity)
        if ticker in self.portfolio.index.values:
            logger.info("Updating quantity for ticker %s to %d", ticker, quantity)
            self.portfolio.loc[self.portfolio.index == ticker, 'quantity'] = quantity
            self._calculate_total_value()
            self._core_satellite_portfolio_split()
            self._rebalance_calculation()
        else:
            logger.warning("Ticker %s not found in current portfolio", ticker)

    def _calculate_total_value(self):
        """
        Calculates the total value of each stock in the portfolio and updates the 
        total value in both local and CAD currencies.
        """
        logger.debug("Updating CAD values with exchange rate: %s", self.exchange_rate)
        self.portfolio['total_value'] = self.portfolio['closing_price'] * self.portfolio['quantity']
        self.portfolio.loc[self.portfolio['currency'] == 'USD', 'total_value_cad'] = self.portfolio['total_value'] * self.exchange_rate
        self.portfolio.loc[self.portfolio['currency'] == 'CAD', 'total_value_cad'] = self.portfolio['total_value']
        logger.debug("Updated portfolio with CAD values")
        return self.portfolio

    def update_prices(self):
        """
        Updates the stock prices in the portfolio by calling an external stock pricing service.
        It checks if the prices need to be updated and applies changes to the portfolio data.
        """
        logger.info("Updating portfolio prices")
        stock_pricer = StockPricer()
        self.portfolio[['closing_price_new', 'update_date_new']] = self.portfolio.apply(
            lambda x: stock_pricer.get_price(x.name, x['exchange']), axis=1).apply(pd.Series)
        
        logger.debug("Price update results:\n%s", self.portfolio[['closing_price_new', 'update_date_new']])
        
        self.portfolio['closing_price'] = np.where(
            self.portfolio.update_date < self.portfolio.update_date_new,
            self.portfolio.closing_price_new,
            self.portfolio.closing_price)
        
        logger.info("Prices updated where applicable")
        self.portfolio.drop(columns=['closing_price_new', 'update_date_new'], inplace=True)
        return self.portfolio

    def _rebalance_no_sell(self) -> None:
        """
        Calculates the rebalance quantities and costs without selling stocks, 
        and sorts the portfolio by rebalancing cost for better efficiency.
        """
        logger.info("Best performing stock for rebalance is %s", self.best_stock.index[0])

        max_rebalanced_value = self.best_stock.total_value.iloc[0] / self.best_stock.target_allocation.iloc[0]

        self.core_portfolio['fractional_value_no_sell'] = self.core_portfolio['target_allocation'] * max_rebalanced_value
        self.core_portfolio['target_quantity_no_sell'] = self.core_portfolio['fractional_value_no_sell'] / self.core_portfolio['closing_price']
        self.core_portfolio['target_quantity_no_sell'] = self.core_portfolio['target_quantity_no_sell'].apply(np.ceil).astype(int)
        self.core_portfolio['rebalance_quantity_no_sell'] = self.core_portfolio['target_quantity_no_sell'] - self.core_portfolio['quantity']
        self.core_portfolio['rebalance_quantity_no_sell'] = self.core_portfolio['rebalance_quantity_no_sell'].astype(int)
        self.core_portfolio['rebalancing_cost_no_sell'] = self.core_portfolio['rebalance_quantity_no_sell'] * self.core_portfolio['closing_price']
        self.core_portfolio.sort_values(by='rebalancing_cost_no_sell', ascending=False)


    def no_sell_report(self) -> None:
        """
        Generates and prints a report of the portfolio rebalancing costs without selling 
        any stocks. It includes the new target quantity and rebalancing costs.
        """
        self._rebalance_no_sell()
        df_report = self.core_portfolio.filter(['quantity', 'closing_price',
        'target_quantity_no_sell', 'rebalance_quantity_no_sell',
       'rebalancing_cost_no_sell','update_date', ]).sort_values(by = 'rebalancing_cost_no_sell', ascending=False)
        
        total_rebalancing_cost_no_sell = df_report.rebalancing_cost_no_sell.sum()
        total_core_after_rebalancing = self.total_core_portfolio_value + total_rebalancing_cost_no_sell
        total_after_rebalancing = self.total_satellite_portfolio_value + total_core_after_rebalancing

        print(tabulate(df_report, headers="keys", tablefmt="pretty"))
        print(f"The cost to rebalance the core portfolio is ${round(total_rebalancing_cost_no_sell, 2)}\n"
            f"\nThis would make the total value of the portfolio: ${round(total_core_after_rebalancing, 2)}")
        print(f"The total value of satellite and core portfolio after rebalancing would be ${round(total_after_rebalancing, 2)}")
