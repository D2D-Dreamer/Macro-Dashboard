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
    page_title="Macroeconomic Health Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# API INITIALIZATION & CACHING
# ==========================================
# Paste your 32-character FRED API key inside the quotes below!
fred_api_key = "e1bee046792fa0ac17f3d1c93bdf4a0e"

if fred_api_key == "YOUR_API_KEY_HERE":
    st.error("⚠️ FRED API Key missing. Please paste it into the code on Line 23.")
    st.stop()

fred = Fred(api_key=fred_api_key)

@st.cache_data(ttl=86400) 
def fetch_fred_data(series_id, start_date):
    """Fetches series from FRED, resamples to monthly, and forward fills."""
    try:
        df = fred.get_series(series_id, observation_start=start_date)
        df = pd.DataFrame(df, columns=['Value'])
        df.index.name = 'Date'
        df.index = pd.to_datetime(df.index)
        df = df.resample('ME').last().ffill().dropna()
        return df
    except Exception as e:
        st.warning(f"Could not fetch FRED series {series_id}: {e}")
        return pd.DataFrame(columns=['Value'])

@st.cache_data(ttl=86400)
def fetch_yf_data(ticker, start_date):
    """Fetches data from Yahoo Finance, extracts monthly closes."""
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
        st.warning(f"Could not fetch Yahoo Finance series {ticker}: {e}")
        return pd.DataFrame(columns=['Value'])

# ==========================================
# DATA DICTIONARY
# ==========================================
MACRO_METRICS = {
    "1. Inflation & Consumer Prices": {
        "Headline CPI": {"id": "CPIAUCSL", "source": "fred", "color": "#1f77b4"},
        "Core CPI": {"id": "CPILFESL", "source": "fred", "color": "#ff7f0e"},
        "Headline PCE Price Index": {"id": "PCEPI", "source": "fred", "color": "#2ca02c"},
        "Core PCE Price Index": {"id": "PCEPILFE", "source": "fred", "color": "#d62728"},
        "CPI: Energy": {"id": "CPIENGSL", "source": "fred", "color": "#9467bd"},
        "CPI: Housing/Shelter": {"id": "CUSR0000SAH1", "source": "fred", "color": "#8c564b"},
        "CPI: Food": {"id": "CPIFABSL", "source": "fred", "color": "#e377c2"},
        "CPI: Medical Care": {"id": "CPIMEDSL", "source": "fred", "color": "#7f7f7f"}
    },
    "2. Upstream Costs & Energy Markets": {
        "PPI Final Demand": {"id": "PPIFIS", "source": "fred", "color": "#17becf"},
        "PPI Goods": {"id": "PPIFGS", "source": "fred", "color": "#bcbd22"},
        "PPI Services": {"id": "PPIFSS", "source": "fred", "color": "#1f77b4"},
        "PPI Health Care Services": {"id": "WPU51", "source": "fred", "color": "#ff7f0e"},
        "WTI Crude Oil Price": {"id": "WTISPLC", "source": "fred", "color": "#d62728"},
        "Brent Crude Oil Price": {"id": "POILBREUSDM", "source": "fred", "color": "#2ca02c"}
    },
    "3. Output, Spending & Monetary Policy": {
        "Real GDP": {"id": "GDPC1", "source": "fred", "color": "#1f77b4"},
        "Monthly GDP Proxy": {"id": "BBKMGDP", "source": "fred", "color": "#ff7f0e"},
        "Real Personal Consumption": {"id": "PCEC96", "source": "fred", "color": "#2ca02c"},
        "Total Industrial Production": {"id": "INDPRO", "source": "fred", "color": "#9467bd"},
        "Manufacturing Production": {"id": "IPMAN", "source": "fred", "color": "#8c564b"},
        "Capacity Utilization": {"id": "CAPB00004S", "source": "fred", "color": "#e377c2"},
        "Federal Funds Rate": {"id": "FEDFUNDS", "source": "fred", "color": "#d62728"}
    },
    "4. Labor Market Health": {
        "Total Nonfarm Payrolls": {"id": "PAYEMS", "source": "fred", "color": "#1f77b4"},
        "Unemployment Rate (U-3)": {"id": "UNRATE", "source": "fred", "color": "#ff7f0e"},
        "Underutilization Rate (U-6)": {"id": "U6RATE", "source": "fred", "color": "#d62728"},
        "Manufacturing Payrolls": {"id": "MANEMP", "source": "fred", "color": "#9467bd"},
        "Goods-Producing Payrolls": {"id": "USGOOD", "source": "fred", "color": "#8c564b"},
        "Mining & Oil/Gas Payrolls": {"id": "CES1021100001", "source": "fred", "color": "#7f7f7f"},
        "Health Care Payrolls": {"id": "CES6562000101", "source": "fred", "color": "#17becf"}
    },
    "5. Forward-Looking & 10 LEI Components": {
        "Sahm Rule Indicator": {"id": "SAHMREALTIME", "source": "fred", "color": "#d62728"},
        "Avg Weekly Hours (Mfg)": {"id": "AWHAEMAN", "source": "fred", "color": "#1f77b4"},
        "Initial Jobless Claims": {"id": "ICSA", "source": "fred", "color": "#ff7f0e"},
        "New Orders, Consumer Goods": {"id": "AMTMNO", "source": "fred", "color": "#2ca02c"},
        "New Orders, Capital Goods": {"id": "NEWORDER", "source": "fred", "color": "#9467bd"},
        "Building Permits": {"id": "PERMIT", "source": "fred", "color": "#8c564b"},
        "Consumer Sentiment": {"id": "UMCSENT", "source": "fred", "color": "#e377c2"},
        "S&P 500": {"id": "^GSPC", "source": "yfinance", "color": "#17becf"},
        "10Y minus Fed Funds Spread": {"id": "T10YFF", "source": "fred", "color": "#bcbd22"},
        "High Yield Corporate Bond Spread": {"id": "BAMLH0A0HYM2", "source": "fred", "color": "#7f7f7f"}
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
    min_value=min_date,
    max_value=today,
    value=(min_date, today),
    format="MMM YYYY"
)

start_date, end_date = selected_dates

st.title("📊 US Macroeconomic Tracking Dashboard")
st.markdown("Track the health of the US economy using dynamic data pulled from the Federal Reserve (FRED) and Yahoo Finance. Designed for executive tracking and presentations.")
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
            selected_metric = st.selectbox(
                "Select a Metric to View:", 
                options=list(metrics_dict.keys()), 
                key=f"drop_{cat_name}"
            )
        with col2:
            view_type = st.radio(
                "Select Chart View:", 
                ["Absolute Values", "YoY % Change"], 
                key=f"radio_{cat_name}"
            )

        metric_info = metrics_dict[selected_metric]
        m_id = metric_info['id']
        m_src = metric_info['source']
        m_color = metric_info['color']
        
        fetch_start = start_date - datetime.timedelta(days=400) 
        
        with st.spinner(f"Loading {selected_metric}..."):
            if m_src == "fred":
                df = fetch_fred_data(m_id, fetch_start)
            else:
                df = fetch_yf_data(m_id, fetch_start)

        if df.empty:
            st.error("Data unavailable for this metric.")
            continue

        df['MoM %'] = df['Value'].pct_change(periods=1) * 100
        df['YoY %'] = df['Value'].pct_change(periods=12) * 100
        
        df_filtered = df[(df.index.date >= start_date) & (df.index.date <= end_date)]

        if df_filtered.empty:
            st.warning("No data available for the selected date range.")
            continue

        if view_type == "Absolute Values":
            fig = px.line(
                df_filtered, 
                x=df_filtered.index, 
                y='Value', 
                title=f"{selected_metric} (Absolute)",
                template="plotly_white",
                color_discrete_sequence=[m_color]
            )
            fig.update_layout(yaxis_title="Index / Rate / Value", xaxis_title="")
        else:
            fig = px.bar(
                df_filtered, 
                x=df_filtered.index, 
                y='YoY %', 
                title=f"{selected_metric} (Year-over-Year % Change)",
                template="plotly_white",
                color_discrete_sequence=[m_color]
            )
            fig.update_layout(yaxis_title="YoY Growth (%)", xaxis_title="")
        
        fig.update_traces(marker_line_width=0, opacity=0.8)
        fig.update_layout(hovermode="x unified", margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(f"**{selected_metric} - Last 12 Months Summary**")
        
        summary_df = df_filtered.tail(12).copy()
        
        summary_df.index = summary_df.index.strftime('%B %Y')
        summary_df.rename_axis('Date', inplace=True)
        summary_df = summary_df[['Value', 'MoM %', 'YoY %']]
        
        summary_formatted = summary_df.style.format({
            'Value': "{:,.2f}",
            'MoM %': "{:+.2f}%",
            'YoY %': "{:+.2f}%"
        }).map(
            lambda val: 'color: green' if pd.notnull(val) and val > 0 else ('color: red' if pd.notnull(val) and val < 0 else 'color: gray'),
            subset=['MoM %', 'YoY %']
        )
        
        st.dataframe(summary_formatted, use_container_width=True)
