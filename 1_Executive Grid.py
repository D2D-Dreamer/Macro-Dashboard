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
    page_title="Executive Macro Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# API INITIALIZATION & CACHING
# ==========================================
try:
    fred_api_key = st.secrets["FRED_API_KEY"]
except KeyError:
    st.error("⚠️ FRED API Key missing from the Streamlit vault.")
    st.stop()
if not fred_api_key:
    # Replace with your actual FRED API key inside the quotes
    fred_api_key = "HIDDEN_IN_SECRETS"

fred = Fred(api_key=fred_api_key)

@st.cache_data(ttl=86400)
def fetch_fred_data(series_id):
    try:
        df = fred.get_series(series_id, observation_start='2000-01-01')
        df = pd.DataFrame(df, columns=['Value'])
        df.index.name = 'Date'
        df.index = pd.to_datetime(df.index)
        df = df.resample('ME').last().ffill().dropna()
        
        df['MoM %'] = df['Value'].pct_change(periods=1) * 100
        df['YoY %'] = df['Value'].pct_change(periods=12) * 100
        return df
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=86400)
def fetch_yf_data(ticker):
    try:
        df = yf.download(ticker, start='2000-01-01', progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df = df['Close']
        else:
            df = df[['Close']]
        df = pd.DataFrame(df)
        df.columns = ['Value']
        df.index.name = 'Date'
        df.index = pd.to_datetime(df.index).tz_localize(None)
        df = df.resample('ME').last().ffill().dropna()
        
        df['MoM %'] = df['Value'].pct_change(periods=1) * 100
        df['YoY %'] = df['Value'].pct_change(periods=12) * 100
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
# SIDEBAR COMMAND CENTER 
# ==========================================
st.sidebar.markdown("### 🏛️ Command Center")
selected_category = st.sidebar.radio(
    "Navigation Menu",
    list(MACRO_METRICS.keys()),
    label_visibility="collapsed"
)

st.sidebar.divider()
st.sidebar.caption("Data sources: FRED & Yahoo Finance.")

# ==========================================
# MAIN DASHBOARD AREA
# ==========================================
col_title, col_filters = st.columns([2, 1])

with col_title:
    clean_title = selected_category.split(". ")[1]
    st.title(clean_title)

with col_filters:
    time_map = {"3M": 3, "6M": 6, "12M": 12, "18M": 18, "24M": 24, "3Y": 36}
    selected_time_label = st.pills("Lookback Period", options=list(time_map.keys()), default="12M")
    
    if selected_time_label:
        months_to_look_back = time_map[selected_time_label]
    else:
        months_to_look_back = 12 
    
    start_date = pd.Timestamp.today() - pd.DateOffset(months=months_to_look_back)

st.divider()

# ==========================================
# METRICS GRID DISPLAY
# ==========================================
metrics_list = list(MACRO_METRICS[selected_category].items())

for i in range(0, len(metrics_list), 2):
    cols = st.columns(2)
    
    for j in range(2):
        if i + j < len(metrics_list):
            metric_name, metric_info = metrics_list[i + j]
            m_id = metric_info['id']
            m_src = metric_info['source']
            m_color = metric_info['color']
            
            with cols[j]:
                with st.container(border=True):
                    card_col1, card_col2 = st.columns([2, 1])
                    with card_col1:
                        st.subheader(metric_name)
                    with card_col2:
                        view_type = st.selectbox(
                            "View",
                            ["Absolute Values", "YoY % Change"],
                            key=f"view_{m_id}",
                            label_visibility="collapsed"
                        )
                    
                    if m_src == "fred":
                        df = fetch_fred_data(m_id)
                    else:
                        df = fetch_yf_data(m_id)
                        
                    if not df.empty:
                        df_filtered = df[df.index >= start_date]
                        
                        if not df_filtered.empty:
                            if view_type == "Absolute Values":
                                fig = px.line(
                                    df_filtered, x=df_filtered.index, y='Value', 
                                    template="plotly_white", color_discrete_sequence=[m_color]
                                )
                                fig.update_layout(yaxis_title="Raw Index / Value", xaxis_title="", height=250, margin=dict(l=0, r=0, t=10, b=0))
                            else:
                                fig = px.bar(
                                    df_filtered, x=df_filtered.index, y='YoY %', 
                                    template="plotly_white", color_discrete_sequence=[m_color]
                                )
                                fig.update_layout(yaxis_title="YoY Growth (%)", xaxis_title="", height=250, margin=dict(l=0, r=0, t=10, b=0))
                            
                            fig.update_traces(marker_line_width=0, opacity=0.85)
                            st.plotly_chart(fig, use_container_width=True)
                            
                            latest_val = df_filtered['Value'].iloc[-1]
                            latest_yoy = df_filtered['YoY %'].iloc[-1]
                            st.caption(f"**Latest:** {latest_val:,.2f} | **YoY Change:** {latest_yoy:+.2f}%")
                        else:
                            st.warning("No data available for this specific timeframe.")
                    else:
                        st.warning("Data currently unavailable.")
