import io
import requests
import sqlite3
from flask import Flask, make_response, render_template, request
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import kaleido
from sqlite3 import Error
import server_boot
import server_methods


api_key = "s1JHjHGzPmCMF4jErIvd_h0FIS1WXcsy"

def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by the db_file
    :param db_file: database file
    :return: Connection object or None
    """
    conn = None;
    try:
        conn = sqlite3.connect(db_file)
        print(f'sqlite3 version: {sqlite3.version}')
        print(f'Successful Connection with: {db_file}')
    except Error as e:
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
    except Error as e:
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
    if data:
        df = pd.DataFrame(data['results'])
        df['t'] = pd.to_datetime(df['t'], unit='ms')
        df['symbol'] = stock_symbol
        df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'num_transactions', 'vwap', 'symbol']
        return df
    else:
        print(f"No data to convert to DataFrame for {stock_symbol}.")
        return None
    
def insert_stock_data(conn, stock_data):
    try:
        cursor = conn.cursor()
        cursor.executemany('''INSERT INTO stock_data (timestamp, symbol, open, high, low, close, volume, num_transactions, vwap) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', stock_data)
        conn.commit()
    except Error as e:
        print(e)


#==========================================================================================================================================================


from flask import Flask
app = Flask(__name__)

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
            url = f"https://api.polygon.io/v2/aggs/ticker/{stock_symbol}/range/1/day/{start_date}/{end_date}?unadjusted=true&sort=asc&limit=5000&apiKey={api_key}"
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()
                print(data)
                quote_df = pd.DataFrame(data['results'])
                quote_df['t'] = pd.to_datetime(quote_df['t'], unit='ms')
                quote_df['symbol'] = stock_symbol
                quote_df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'num_transactions', 'vwap', 'symbol']

                if quote_df is not None:
                    stock_data = quote_df[['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'num_transactions', 'vwap']].to_records(index=False)
                    insert_stock_data(conn, stock_data)
            else:
                print(f"Error fetching data for {stock_symbol}: {response.status_code}")

        df = pd.read_sql_query("SELECT * FROM stock_data", conn)

        fig = px.line(df, x='timestamp', y='close', title='VWAP Prices')
        fig.update_layout(xaxis_title='Timestamp', yaxis_title='VWAP Price')

        image_stream = io.BytesIO()
        pio.write_image(fig, image_stream, format='png')
        image_stream.seek(0)

        response = make_response(image_stream.getvalue())
        response.headers['Content-Type'] = 'image/png'
        return response

    return render_template('form.html')


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True)