from flask import Flask, render_template
import server_methods
import requests
import sqlite3
import pandas as pd
import plotly.express as px
from flask import Flask, render_template, request, make_response
import json
import io
import plotly.io as pio
app = Flask(__name__)

# Specify the URL route to the app homepage
@app.route('/')
def home():
    return render_template('form.html')

# Route to Plotly visualization page
@app.route('/visualization', methods=['GET', 'POST'])
def visualization():
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        stock_symbols = request.form.get('stock_symbols').split(',')

        db_file = "stock_data.db"
        conn = server_methods.create_connection(db_file)
        server_methods.create_table(conn)

        # Fetch data and store it in the database
        for stock_symbol in stock_symbols:
            data = server_methods.get_stock_quote(server_methods.api_key, stock_symbol, start_date, end_date)
            quote_df = server_methods.data_to_dataframe(stock_symbol, data)

            if quote_df is not None:
                stock_data = quote_df[['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'num_transactions', 'vwap']].to_records(index=False)
                server_methods.insert_stock_data(conn, stock_data)

        df = pd.read_sql_query("SELECT * FROM stock_data", conn)

        fig = px.line(df, x='timestamp', y='close', title='Stock Closing Prices')
        fig.update_layout(xaxis_title='Timestamp', yaxis_title='Stock Closing Price')

        fig_json = fig.to_json()

        return render_template('visualizations.html', fig_json=fig_json)

    return render_template('form.html')

if __name__ == '__main__':
    app.run()
