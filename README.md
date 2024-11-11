# Passive Portfolio Rebalancer

Passive Portfolio Rebalancer is a simple command-line tool designed to help you maintain your desired asset allocation in a stock portfolio. Given your current portfolio and a target allocation, it calculates which assets to buy or sell to achieve the specified balance. 

## Features
- **Load Portfolio**: Reads your current stock holdings.
- **Set Target Allocation**: Define your desired allocation by ticker symbol.
- **Rebalance Suggestions**: Generates buy/sell recommendations to meet the target allocation.
- **Simple CLI Interface**: Operate entirely from the command line.
- **Split Core and Satellite Portfolio**: Splits portfolio based on a "core" investing portfolio which will be passively invested vs an actively managed "satellite" portfolio. Rebalancing will only be calculated on the core portfolio.
Note:
The default currency is Canadian Dollars and USD are converted based on the current exchange rate.

## Installation

1. **Clone the Repository**:
    ```bash
    git clone https://github.com/mcavoyst/passive-portfolio.git
    cd passive-portfolio
    ```

2. **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3. **API Keys**
   Two API keys are required from:
   1. http://api.marketstack.com for current stock price
   2. http://api.exchangeratesapi.io for current CAD/USD exachange rate.
   Store the API key in a `.env` in the root directory:
```
PRICE_API_KEY=XXXXYYYYY11111433333
EXCHANGE_API_KEY=XXXXXXXXXYYYYYZZZZZZZZ111223
```
4. Add data into the `/data` folder in the same format as in the `/example` folder. The allocations in the `model_portfolio.csv` are your target asset allocations and must add to 100% while the `portfolio_data.csv` are the total quanity of securities owned without duplicates. The `exchange_rate.txt` file should be placed in the `/data` folder and is only used if the API does not connect.

## Usage

### 1. Prepare Your Files
- **Current Portfolio**: A CSV file with your current portfolio data. `model_portfolio.csv` is an example of how to format the data. Currently there is no way to add in new stock using the app, but this can be changed in the future.
- **Target Allocation**: A csv file with your target allocations.

### 2. Run the Tool
```bash
python3 app/main.py 
```
### 3. Output
```bash
Do you want to update the prices? (y/n)
```
Select y if you want to check for the current price using the market API. The output will be:
```
+--------+----------+---------------+---------------------------+--------------------+----------+
| ticker | quantity | closing_price |        update_date        |    total_value     | currency |
+--------+----------+---------------+---------------------------+--------------------+----------+
|  VFV   |  23940   |    148.07     | 2024-11-08 00:00:00+00:00 |     3544795.8      |   CAD    |
|  ZNQ   |  19068   |     95.12     | 2024-11-08 00:00:00+00:00 | 1813748.1600000001 |   CAD    |
|  XIU   |  26712   |     37.61     | 2024-11-08 00:00:00+00:00 |     1004638.32     |   CAD    |
|  XRE   |  19824   |     16.75     | 2024-08-30 00:00:00+00:00 |      332052.0      |   CAD    |
|  XIN   |   8148   |     36.29     | 2024-11-08 00:00:00+00:00 |     295690.92      |   CAD    |
|  XIT   |   1428   |     62.11     | 2024-11-08 00:00:00+00:00 |      88693.08      |   CAD    |
|  PLTR  |   588    |     58.39     | 2024-11-08 00:00:00+00:00 |      34333.32      |   USD    |
+--------+----------+---------------+---------------------------+--------------------+----------+
```
If you want to update the quantities of any stock in the list, just input the ticker and the new total quantity. Otherwise, type `*`.
```
Which stock do you want to update? If none, type "*"
```
Once * is entered the following table will be displayed showing the number of each asset that would need to be purchased to rebalnce the portfolio if you were to not sell any of the existing stock. Additional functionality can be added to show the number of assets to rebalance with buying and selling in the future.
```
+--------+----------+---------------+-------------------------+----------------------------+--------------------------+---------------------------+
| ticker | quantity | closing_price | target_quantity_no_sell | rebalance_quantity_no_sell | rebalancing_cost_no_sell |        update_date        |
+--------+----------+---------------+-------------------------+----------------------------+--------------------------+---------------------------+
|  XIU   |  26712   |     37.61     |          28936          |            2224            |         83644.64         | 2024-11-08 00:00:00+00:00 |
|  VFV   |  23940   |    148.07     |          24499          |            559             |    82771.12999999999     | 2024-11-08 00:00:00+00:00 |
|  XIN   |   8148   |     36.29     |          9996           |            1848            |         67063.92         | 2024-11-08 00:00:00+00:00 |
|  XRE   |  19824   |     16.75     |          21657          |            1833            |         30702.75         | 2024-08-30 00:00:00+00:00 |
|  ZNQ   |  19068   |     95.12     |          19068          |             0              |           0.0            | 2024-11-08 00:00:00+00:00 |
+--------+----------+---------------+-------------------------+----------------------------+--------------------------+---------------------------+
The cost to rebalance the core portfolio is $264182.44

This would make the total value of the portfolio: $7255107.64
The total value of satellite and core portfolio after rebalancing would be $7378134.04
```

Configuration
You can adjust various settings in config.py to match your preferences, such as transaction limits or minimum cash reserve.

Example
Data in `/example` can be used to start and to check desired formatting.

Contributing
Feel free to submit issues or pull requests to improve the functionality or add new features.

License
This project is licensed under the MIT License.
