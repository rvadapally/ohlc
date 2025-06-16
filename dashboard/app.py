import pathlib
import pandas as pd
import streamlit as st

DATA_FILE = pathlib.Path('signals.csv')

st.title('BTC Signal Dashboard')

if DATA_FILE.exists():
    data = pd.read_csv(DATA_FILE, parse_dates=['Date'], index_col='Date')
    latest = data.iloc[-1]
    st.subheader('Latest snapshot')
    st.dataframe(latest.unstack().T.style.background_gradient(axis=0))
else:
    st.warning('No signals.csv found. Run signal_dashboard.py first.')
