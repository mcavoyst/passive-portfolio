import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
from dotenv import load_dotenv
import logging

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
APP_PASSWORD = os.environ.get('APP_PASSWORD', 'changeme')
DATA_FILE = 'data/portfolio_data.csv'

os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    filename='logs/app.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def load_portfolio(update_prices=False):
    from portfolio import Portfolio
    return Portfolio(DATA_FILE, update_prices=update_prices)


@app.route('/')
def index():
    if session.get('authenticated'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password', '') == APP_PASSWORD:
            session['authenticated'] = True
            return redirect(url_for('dashboard'))
        flash('Invalid password. Please try again.', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    try:
        p = load_portfolio()
        report_data = p.get_no_sell_report_data()

        portfolio_df = p.portfolio.filter(
            ['quantity', 'closing_price', 'update_date', 'total_value', 'currency']
        ).sort_values(by='total_value', ascending=False).copy()
        portfolio_df['update_date'] = portfolio_df['update_date'].apply(
            lambda x: str(x)[:10] if x is not None else ''
        )

        rebalance_df = report_data['report'].copy()
        rebalance_df['update_date'] = rebalance_df['update_date'].apply(
            lambda x: str(x)[:10] if x is not None else ''
        )

        return render_template('dashboard.html',
            portfolio=portfolio_df.reset_index().to_dict('records'),
            rebalance=rebalance_df.reset_index().to_dict('records'),
            total_core=report_data['total_core'],
            total_satellite=report_data['total_satellite'],
            total_portfolio=round(report_data['total_core'] + report_data['total_satellite'], 2),
            total_rebalancing_cost=report_data['total_rebalancing_cost'],
            total_after_rebalancing=report_data['total_after_rebalancing'],
            exchange_rate=round(p.exchange_rate, 4),
            last_update=str(p.portfolio.update_date.max())[:10],
        )
    except Exception as e:
        logger.error('Dashboard error: %s', e, exc_info=True)
        flash(f'Error loading portfolio: {e}', 'danger')
        return render_template('dashboard.html', error=str(e))


@app.route('/update-prices', methods=['POST'])
@login_required
def update_prices():
    try:
        p = load_portfolio(update_prices=True)
        p.save_portfolio()
        flash('Prices updated successfully.', 'success')
    except Exception as e:
        logger.error('Price update error: %s', e, exc_info=True)
        flash(f'Error updating prices: {e}', 'danger')
    return redirect(url_for('dashboard'))


@app.route('/update-quantity', methods=['POST'])
@login_required
def update_quantity():
    ticker = request.form.get('ticker', '').upper().strip()
    try:
        quantity = int(request.form.get('quantity', -1))
        if quantity < 0:
            raise ValueError('Quantity must be zero or greater.')
        p = load_portfolio()
        p.update_quantity(ticker, quantity)
        p.save_portfolio()
        flash(f'Updated {ticker} to {quantity:,} shares.', 'success')
    except ValueError as e:
        flash(f'Invalid quantity: {e}', 'danger')
    except Exception as e:
        logger.error('Update quantity error: %s', e, exc_info=True)
        flash(f'Error updating {ticker}: {e}', 'danger')
    return redirect(url_for('dashboard'))


@app.route('/invest', methods=['POST'])
@login_required
def invest():
    try:
        amount = float(request.form.get('amount', 0))
        if amount <= 0:
            flash('Investment amount must be greater than zero.', 'danger')
            return redirect(url_for('dashboard'))
        p = load_portfolio()
        result = p.spend_money_scenario_data(amount)
        return render_template('invest.html', result=result, amount=amount)
    except ValueError:
        flash('Invalid amount entered.', 'danger')
        return redirect(url_for('dashboard'))
    except Exception as e:
        logger.error('Invest scenario error: %s', e, exc_info=True)
        flash(f'Error running investment scenario: {e}', 'danger')
        return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8080)
