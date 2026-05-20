import streamlit as st
import pandas as pd
import plotly.express as px
from fredapi import Fred
import yfinance as yf
import datetime
import os

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Macro Data Explorer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# API INITIALIZATION & CACHING
# ==========================================
try:
    fred_api_key = st.secrets.get("FRED_API_KEY", os.environ.get("FRED_API_KEY"))
except FileNotFoundError:
    fred_api_key = os.environ.get("FRED_API_KEY")

if not fred_api_key:
    # Replace with your actual API key
    fred_api_key = "e1bee046792fa0ac17f3d1c93bdf4a0e"

fred = Fred(api_key=fred_api_key)

@st.cache_data(ttl=86400)
def fetch_fred_data(series_id, start_date):
    try:
        df = fred.get_series(series_id, observation_start=start_date)
        df = pd.DataFrame(df, columns=['Value'])
        df.index.name = 'Date'
        df.index = pd.to_datetime(df.index)
        df = df.resample('ME').last().ffill().dropna()
        return df
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=86400)
def fetch_yf_data(ticker, start_date):
    try:
        start_str = start_date.strftime('%Y-%m-%d')
        df = yf.download(ticker, start=start_str, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df = df['Close']
        else:
            df = df[['Close']]
            
        df = pd.DataFrame(df)
        df.columns = ['Value']
        df.index.name = 'Date'
        df.index = pd.to_datetime(df.index).tz_localize(None)
        df = df.resample('ME').last().ffill().dropna()
        return df
    except Exception as e:
        return pd.DataFrame()

# ==========================================
# DATA DICTIONARY
# ==========================================
MACRO_METRICS = {
    "1. Inflation & Consumer Prices": {
        "Headline CPI": {"id": "CPIAUCSL", "source": "fred", "color": "#1f77b4"},
        "Core CPI": {"id": "CPILFESL", "source": "fred", "color": "#ff7f0e"},
        "Headline PCE Price Index": {"id": "PCEPI", "source": "fred", "color": "#2ca02c"},
        "Core PCE Price Index": {"id": "PCEPILFE", "source": "fred", "color": "#d62728"}
    },
    "2. Upstream Costs & Energy Markets": {
        "PPI Final Demand": {"id": "PPIFIS", "source": "fred", "color": "#17becf"},
        "PPI Goods": {"id": "PPIFGS", "source": "fred", "color": "#bcbd22"},
        "PPI Services": {"id": "PPIFSS", "source": "fred", "color": "#1f77b4"},
        "WTI Crude Oil Price": {"id": "WTISPLC", "source": "fred", "color": "#d62728"}
    },
    "3. Output, Spending & Monetary Policy": {
        "Real GDP": {"id": "GDPC1", "source": "fred", "color": "#1f77b4"},
        "Real Personal Consumption": {"id": "PCEC96", "source": "fred", "color": "#2ca02c"},
        "Total Industrial Production": {"id": "INDPRO", "source": "fred", "color": "#9467bd"},
        "Federal Funds Rate": {"id": "FEDFUNDS", "source": "fred", "color": "#d62728"}
    },
    "4. Labor Market Health": {
        "Total Nonfarm Payrolls": {"id": "PAYEMS", "source": "fred", "color": "#1f77b4"},
        "Unemployment Rate (U-3)": {"id": "UNRATE", "source": "fred", "color": "#ff7f0e"},
        "Manufacturing Payrolls": {"id": "MANEMP", "source": "fred", "color": "#9467bd"}
    },
    "5. Forward-Looking & 10 LEI Components": {
        "Sahm Rule Indicator": {"id": "SAHMREALTIME", "source": "fred", "color": "#d62728"},
        "Initial Jobless Claims": {"id": "ICSA", "source": "fred", "color": "#ff7f0e"},
        "Consumer Sentiment": {"id": "UMCSENT", "source": "fred", "color": "#e377c2"},
        "S&P 500": {"id": "^GSPC", "source": "yfinance", "color": "#17becf"}
    }
}

# ==========================================
# SIDEBAR & GLOBAL CONTROLS
# ==========================================
st.sidebar.header("⚙️ Dashboard Controls")
min_date = datetime.date(2000, 1, 1)
today = datetime.date.today()

selected_dates = st.sidebar.slider(
    "Select Historical Period",
    min_value=min_date, max_value=today, value=(min_date, today), format="MMM YYYY"
)
start_date, end_date = selected_dates

st.title("📊 Macro Data Explorer")
st.divider()

# ==========================================
# MAIN LAYOUT (TABS)
# ==========================================
tab_names = list(MACRO_METRICS.keys())
tabs = st.tabs(tab_names)

for tab, cat_name in zip(tabs, tab_names):
    with tab:
        st.subheader(f"{cat_name.split('. ')[1]}")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            metrics_dict = MACRO_METRICS[cat_name]
            selected_metric = st.selectbox("Select a Metric to View:", options=list(metrics_dict.keys()), key=f"drop_{cat_name}")
        with col2:
            view_type = st.radio("Select Chart View:", ["Absolute Values", "YoY % Change"], key=f"radio_{cat_name}")

        metric_info = metrics_dict[selected_metric]
        m_id = metric_info['id']
        m_src = metric_info['source']
        m_color = metric_info['color']
        
        fetch_start = start_date - datetime.timedelta(days=400) 
        
        if m_src == "fred":
            df = fetch_fred_data(m_id, fetch_start)
        else:
            df = fetch_yf_data(m_id, fetch_start)

        if not df.empty:
            df['MoM %'] = df['Value'].pct_change(periods=1) * 100
            df['YoY %'] = df['Value'].pct_change(periods=12) * 100
            
            df_filtered = df[(df.index.date >= start_date) & (df.index.date <= end_date)]

            if not df_filtered.empty:
                if view_type == "Absolute Values":
                    fig = px.line(df_filtered, x=df_filtered.index, y='Value', template="plotly_white", color_discrete_sequence=[m_color])
                    fig.update_layout(yaxis_title="Index / Rate / Value", xaxis_title="")
                else:
                    fig = px.bar(df_filtered, x=df_filtered.index, y='YoY %', template="plotly_white", color_discrete_sequence=[m_color])
                    fig.update_layout(yaxis_title="YoY Growth (%)", xaxis_title="")
                
                fig.update_traces(marker_line_width=0, opacity=0.8)
                st.plotly_chart(fig, use_container_width=True)

                st.markdown(f"**{selected_metric} - Last 12 Months Summary**")
                summary_df = df_filtered.tail(12).copy()
                summary_df.index = summary_df.index.strftime('%B %Y')
                summary_df.rename_axis('Date', inplace=True)
                summary_df = summary_df[['Value', 'MoM %', 'YoY %']]
                
                summary_formatted = summary_df.style.format({
                    'Value': "{:,.2f}", 'MoM %': "{:+.2f}%", 'YoY %': "{:+.2f}%"
                }).map(
                    lambda val: 'color: green' if pd.notnull(val) and val > 0 else ('color: red' if pd.notnull(val) and val < 0 else 'color: gray'),
                    subset=['MoM %', 'YoY %']
                )
                st.dataframe(summary_formatted, use_container_width=True)
            else:
                st.warning("No data available for the selected date range.")
        else:
            st.error("Data unavailable for this metric.")
