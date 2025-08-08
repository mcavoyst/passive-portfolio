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
        spend_money_scenario(money_to_spend): Simulates spending a specified amount of money on the portfolio.

    Private Methods:
        _load_portfolio(data_filepath): Loads the portfolio data from a CSV file.
        _load_model(): Loads and validates the model portfolio data.
        _core_satellite_portfolio_split(portfolio): Splits the portfolio into core and satellite parts.
        _rebalance(core_portfolio): Calculates the rebalancing quantities and costs for the core portfolio.
        _calculate_total_value(portfolio): Calculates the total value of the portfolio in CAD.
        _update_prices(portfolio): Updates the stock prices in the portfolio.
        _rebalance_no_sell(core_portfolio): Calculates rebalancing quantities and costs without selling stocks.
    """
    def __init__(self, data_filepath: str, update_prices: bool) -> None:
        """
        Initializes the Portfolio object with the given data file, loading the 
        portfolio data, and optionally updating prices based on a flag.
        
        Args:
            data_filepath (str): The relative path to the portfolio data CSV file.
            update_prices (bool): Flag to determine whether to update stock prices upon initialization.
        """
        self.portfolio = self._load_portfolio(data_filepath)
        self.exchange_rate = get_exchange_rate()
        if update_prices:
            logger.info("Updating prices as requested on initialization")
            self.portfolio = self._update_prices(portfolio=self.portfolio)
        self.model_portfolio = self._load_model()
        self.portfolio = self._calculate_total_value(portfolio=self.portfolio)
        self.core_portfolio, self.satellite_portfolio = self._core_satellite_portfolio_split(portfolio=self.portfolio)
        self.core_portfolio = self._rebalance(self.core_portfolio)

    def _load_portfolio(self, data_filepath) -> None:
        """
        Loads the portfolio data from a CSV file.

        Args:
            data_filepath (str): The relative path to the portfolio data CSV file.

        Returns:
            DataFrame: The loaded portfolio data.
        """
        data_filepath = os.path.join(ROOT_DIR, data_filepath)
        logger.info("Initializing Portfolio with filepath: %s", data_filepath)
        self.filepath = data_filepath
        portfolio = pd.read_csv(data_filepath, index_col='ticker')
        portfolio.update_date = pd.to_datetime(portfolio.update_date)
        logger.debug("Loaded portfolio data")
        return portfolio

    def _load_model(self) -> None:
        """
        Loads the model portfolio from a predefined CSV file and validates the total 
        target allocation across the stocks.
        
        Raises:
        - ValueError: If the sum of target allocations in the model portfolio does not equal 1.00.
        """
        logger.debug("Loading model portfolio")
        model_path = os.path.join(ROOT_DIR, 'data/model_portfolio.csv')
        model_portfolio = pd.read_csv(model_path, index_col='ticker')
        total = model_portfolio.sum()['target_allocation']
        
        if round(total, 2) != 1.00:
            logger.error("Model portfolio allocations sum to %s, expected 1.00", total)
            raise ValueError("Check allocations in model portfolio")
        else:
            logger.info("Model portfolio allocations validated")
        return model_portfolio

    def save_portfolio(self):
        """
        Saves the current portfolio to the file specified during initialization.
        """
        logger.info("Saving portfolio data to %s", self.filepath)
        self.portfolio.to_csv(self.filepath, index_label='ticker')

    def _core_satellite_portfolio_split(self, portfolio: pd.DataFrame) -> tuple:
        """
        Splits the portfolio into core and satellite segments based on the model portfolio.
        It also calculates the actual allocation of the core portfolio and updates the 
        core and satellite portfolio values.
        """
        logger.debug("Splitting portfolio into core and satellite")
        
        core_portfolio = portfolio.loc[self.model_portfolio.index].copy()
        satellite_portfolio = portfolio.loc[~portfolio.index.isin(self.model_portfolio.index)]
        total_core_portfolio_value = core_portfolio.total_value.sum()
        total_satellite_portfolio_value = satellite_portfolio.total_value.sum()
        core_portfolio['actual_allocation'] = core_portfolio['total_value'] / total_core_portfolio_value
        core_portfolio = pd.merge(core_portfolio, self.model_portfolio, left_index=True, right_index=True)
        return core_portfolio, satellite_portfolio

    def _rebalance(self, core_portfolio: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates the rebalance quantities and costs for the core portfolio. It determines 
        the target quantity of each stock based on the target allocation and calculates 
        the rebalance quantity and cost.
        """
        logger.debug("Calculating rebalancing quantities and costs")

        total_core_portfolio_value = core_portfolio.total_value.sum()
        core_portfolio['target_value'] = core_portfolio['target_allocation']* total_core_portfolio_value
        core_portfolio['target_quantity'] = core_portfolio['target_value'] / core_portfolio['closing_price']
        core_portfolio['target_quantity'] = core_portfolio['target_quantity'].apply(np.ceil)
        core_portfolio['rebalance_quantity'] = core_portfolio['target_quantity'] - core_portfolio['quantity']
        core_portfolio['rebalancing_cost'] = core_portfolio['rebalance_quantity'] * core_portfolio['closing_price']
        core_portfolio.sort_values(by='rebalancing_cost', ascending=False, inplace=True)
        return core_portfolio

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
            self.portfolio = self._calculate_total_value(portfolio=self.portfolio)
            self.core_portfolio, self.satellite_portfolio = self._core_satellite_portfolio_split(portfolio=self.portfolio)
            self.core_portfolio = self._rebalance(self.core_portfolio)
        else:
            logger.warning("Ticker %s not found in current portfolio", ticker)

    def _calculate_total_value(self, portfolio: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates the total value of each stock in the portfolio and updates the 
        total value in both local and CAD currencies.
        """
        logger.debug("Updating CAD values with exchange rate: %s", self.exchange_rate)
        portfolio['total_value'] = portfolio['closing_price'] * portfolio['quantity']
        portfolio.loc[portfolio['currency'] == 'USD', 'total_value_cad'] = portfolio['total_value'] * self.exchange_rate
        portfolio.loc[portfolio['currency'] == 'CAD', 'total_value_cad'] = portfolio['total_value']
        logger.debug("Updated portfolio with CAD values")
        return portfolio

    def _update_prices(self, portfolio: pd.DataFrame) -> pd.DataFrame:
        """
        Updates the stock prices in the portfolio by calling an external stock pricing service.
        It checks if the prices need to be updated and applies changes to the portfolio data.
        """
        logger.info("Updating portfolio prices")
        stock_pricer = StockPricer()
        try:
            portfolio[['closing_price_new', 'update_date_new']] = portfolio.apply(
                    lambda x: stock_pricer.get_price(x.name, x['exchange']), axis=1).apply(pd.Series) 
            portfolio['update_date'] = pd.to_datetime(portfolio['update_date'])
            portfolio['update_date_new'] = pd.to_datetime(portfolio['update_date_new'])
        except ValueError as e:
            logger.error('Failed to update stock prices %s', e)
            print('Failed to update stock prices. API may be at request limit.')
            return portfolio
        
        logger.debug("Price update results:\n%s", portfolio[['closing_price_new', 'update_date_new']])
        
        try:
            portfolio['closing_price'] = np.where(
                portfolio.update_date < portfolio.update_date_new,
                portfolio.closing_price_new,
                portfolio.closing_price)
            
            portfolio['update_date'] = np.where(
                portfolio.update_date < portfolio.update_date_new,
                portfolio.update_date_new,
                portfolio.update_date)
            
            logger.info("Prices updated where applicable")
            # self.portfolio.drop(columns=['closing_price_new', 'update_date_new'], inplace=True)
            return portfolio
        except Exception as e:
            logger.error('Failed to update prices for any ticker error:%s', e)
            return portfolio

    def _rebalance_no_sell(self, core_portfolio: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates the rebalance quantities and costs without selling stocks, 
        and sorts the portfolio by rebalancing cost for better efficiency.

        Args:
            core_portfolio (DataFrame): The core portfolio data.

        Returns:
            DataFrame: The updated core portfolio with no-sell rebalancing information.
        """
        best_stock = core_portfolio[core_portfolio.rebalancing_cost == core_portfolio.rebalancing_cost.min()]
        logger.info("Best performing stock for rebalance is %s", best_stock.index[0])

        max_rebalanced_value = best_stock.total_value.iloc[0] / best_stock.target_allocation.iloc[0]

        core_portfolio['fractional_value_no_sell'] = core_portfolio['target_allocation'] * max_rebalanced_value
        core_portfolio['target_quantity_no_sell'] = core_portfolio['fractional_value_no_sell'] / core_portfolio['closing_price']
        core_portfolio['target_quantity_no_sell'] = core_portfolio['target_quantity_no_sell'].apply(np.ceil).astype(int)
        core_portfolio['rebalance_quantity_no_sell'] = core_portfolio['target_quantity_no_sell'] - core_portfolio['quantity']
        core_portfolio['rebalance_quantity_no_sell'] = core_portfolio['rebalance_quantity_no_sell'].astype(int)
        core_portfolio['rebalancing_cost_no_sell'] = core_portfolio['rebalance_quantity_no_sell'] * core_portfolio['closing_price']
        core_portfolio.sort_values(by='rebalancing_cost_no_sell', ascending=False)
        return core_portfolio

    def no_sell_report(self) -> None:
        """
        Generates and prints a report of the portfolio rebalancing costs without selling 
        any stocks. It includes the new target quantity and rebalancing costs.
        """
        self.core_portfolio = self._rebalance_no_sell(core_portfolio=self.core_portfolio)
        df_report = self.core_portfolio.filter(['quantity', 'closing_price',
        'target_quantity_no_sell', 'rebalance_quantity_no_sell',
       'rebalancing_cost_no_sell','update_date', ]).sort_values(by = 'rebalancing_cost_no_sell', ascending=False)
        
        total_core_portfolio_value = self.core_portfolio.total_value.sum()
        total_satellite_portfolio_value = self.satellite_portfolio.total_value.sum()
        
        total_rebalancing_cost_no_sell = df_report.rebalancing_cost_no_sell.sum()
        total_core_after_rebalancing = total_core_portfolio_value + total_rebalancing_cost_no_sell
        total_after_rebalancing = total_satellite_portfolio_value + total_core_after_rebalancing

        print(tabulate(df_report, headers="keys", tablefmt="pretty"))
        print(f"The cost to rebalance the core portfolio is ${round(total_rebalancing_cost_no_sell, 2)}\n"
            f"\nThis would make the total value of the portfolio: ${round(total_core_after_rebalancing, 2)}")
        print(f"The total value of satellite and core portfolio after rebalancing would be ${round(total_after_rebalancing, 2)}")


    def spend_money_scenario(self, money_to_spend: float) -> None:
        """
        Simulates a scenario where a specified amount of money is spent on the best performing stock.

        Args:
            money_to_spend (float): The amount of money to be spent on the portfolio.
        """
        logger.info("Simulating spend money scenario with %s", money_to_spend)
        original_money_to_spend = money_to_spend
        if money_to_spend <= 0:
            logger.warning("Money to spend must be greater than zero")
            return
        
        scenario_portfolio  = self.core_portfolio.copy()

        storage_dataframe = pd.DataFrame(columns=['quantity', 'purchase_cost'], index=scenario_portfolio.index)
        storage_dataframe['quantity'] = 0
        storage_dataframe['purchase_cost'] = 0.0
        
        while len(scenario_portfolio) > 0:
            logger.info("Start scenario with money to spend: %s", money_to_spend)
            # logger.debug("Current portfolio:\n%s", scenario_portfolio)
            scenario_portfolio = scenario_portfolio[scenario_portfolio['closing_price'] <= money_to_spend]
            # index where rebalncing cost is max
            ticker_to_buy = scenario_portfolio[scenario_portfolio['rebalancing_cost'] == scenario_portfolio['rebalancing_cost'].max()].index[0]
            purchase_cost = scenario_portfolio.loc[ticker_to_buy]['closing_price']
            scenario_portfolio.loc[ticker_to_buy, 'quantity'] += 1
            money_to_spend = money_to_spend - purchase_cost
            scenario_portfolio = self._calculate_total_value(portfolio=scenario_portfolio)
            scenario_portfolio = self._rebalance(scenario_portfolio)
            scenario_portfolio = self._rebalance_no_sell(scenario_portfolio)
            logger.info('Spent %s on %s', purchase_cost, ticker_to_buy)

            storage_dataframe.loc[ticker_to_buy, 'quantity'] += 1
            storage_dataframe.loc[ticker_to_buy, 'purchase_cost'] += purchase_cost

            scenario_portfolio = scenario_portfolio[scenario_portfolio['closing_price'] <= money_to_spend]
        
        storage_dataframe['unit_cost'] = storage_dataframe['purchase_cost'] / storage_dataframe['quantity']
        print('\nThe following can be purchased with %s\n' % original_money_to_spend)
        print(tabulate(storage_dataframe, headers="keys", tablefmt="pretty"))
        print(f"Total spent: {round(storage_dataframe['purchase_cost'].sum(),2)}")

