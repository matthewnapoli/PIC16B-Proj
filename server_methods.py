import requests
import sqlite3
import pandas as pd
import plotly.express as px
from flask import Flask, render_template, request, make_response
import json
import io
import plotly.io as pio

app = Flask(__name__)

api_key = "s1JHjHGzPmCMF4jErIvd_h0FIS1WXcsy"

def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(f'sqlite3 version: {sqlite3.version}')
        print(f'Successful connection with: {db_file}')
    except sqlite3.Error as e:
        print(e)
    return conn

def create_table(conn):
    try:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS stock_data (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp DATETIME,
                            symbol TEXT,
                            open REAL,
                            high REAL,
                            low REAL,
                            close REAL,
                            volume INTEGER,
                            num_transactions INTEGER,
                            vwap REAL
                        )''')
        conn.commit()
    except sqlite3.Error as e:
        print(e)

def get_stock_quote(api_key, stock_symbol, start_date, end_date):
    url = f"https://api.polygon.io/v2/aggs/ticker/{stock_symbol}/range/1/day/{start_date}/{end_date}?unadjusted=true&sort=asc&limit=5000&apiKey={api_key}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Error fetching data for {stock_symbol}: {response.status_code}")
        return None

def data_to_dataframe(stock_symbol, data):
    if data['resultsCount'] > 0:
        results = data['results']
        df = pd.DataFrame(results)
        df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
        df['symbol'] = stock_symbol
        return df
    else:
        print(f"No data available for {stock_symbol}")
        return None

def insert_stock_data(conn, stock_data):
    try:
        cursor = conn.cursor()
        cursor.executemany('''INSERT INTO stock_data (timestamp, symbol, open, high, low, close, volume, num_transactions, vwap)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', stock_data)
        conn.commit()
    except sqlite3.Error as e:
        print(e)

@app.route('/', methods=['GET', 'POST'])
def form():
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        stock_symbols = request.form.get('stock_symbols').split(',')

        db_file = "stock_data.db"
        conn = create_connection(db_file)
        create_table(conn)

        # Fetch data and store it in the database
        for stock_symbol in stock_symbols:
            data = get_stock_quote(api_key, stock_symbol, start_date, end_date)

            if data is not None:
                quote_df = data_to_dataframe(stock_symbol, data)
                if quote_df is not None:
                    quote_df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'num_transactions', 'vwap', 'symbol']

                    stock_data = quote_df[['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'num_transactions', 'vwap']].to_records(index=False)
                    insert_stock_data(conn, stock_data)
            else:
                print(f"Error fetching data for {stock_symbol}")

        df = pd.read_sql_query("SELECT * FROM stock_data", conn)

        fig = px.line(df, x='timestamp', y='close', title='Stock Closing Prices')
        fig_json = fig.to_json()

        return render_template('visualizations.html', fig_json=fig_json)

    return render_template('form.html')

def plot_vwap_prices(df):
    fig = px.line(df, x='timestamp', y='vwap', title='Stock VWAP Prices')
    fig_json = json.dumps(fig, cls=pio.utils.PlotlyJSONEncoder)
    return fig_json

@app.route('/plot_vwap', methods=['POST'])
def plot_vwap():
    db_file = "stock_data.db"
    conn = create_connection(db_file)
    df = pd.read_sql_query("SELECT * FROM stock_data", conn)
    fig_json = plot_vwap_prices(df)
    return fig_json

@app.route('/plot_vwap_image', methods=['POST'])
def plot_vwap_image():
    db_file = "stock_data.db"
    conn = create_connection(db_file)
    df = pd.read_sql_query("SELECT * FROM stock_data", conn)
    fig_json = plot_vwap_prices(df)
    fig = px.Figure(json.loads(fig_json))
    fig.update_layout(width=800, height=400)
    image_stream = io.BytesIO()
    pio.write_image(fig, image_stream, format='png')
    image_stream.seek(0)
    
    response = make_response(image_stream.getvalue())
    response.headers['Content-Type'] = 'image/png'
    return response

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True)
