import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
import yfinance as yf
import plotly.graph_objects as go

# ------------------ CONFIG ------------------
st.set_page_config(layout="wide", page_title="TradeWhisper Dashboard", page_icon="📊")
API_BASE = "https://trade-wishper-0uyh.onrender.com"  # Adjust if your FastAPI server is remote

# ------------------ COUNTRY → SUFFIX MAPPING ------------------
market_suffix = {
    "United States": "",
    "India": ".NS",
    "United Kingdom": ".L",
    "Germany": ".DE",
    "Japan": ".T",
    "Hong Kong": ".HK",
    "Canada": ".TO",
    "Australia": ".AX",
    "France": ".PA",
    "South Korea": ".KS",
    "Brazil": ".SA",
    "Taiwan": ".TW",
    "China": ".SS"
}

# ------------------ SYMBOL RESOLUTION FUNCTION ------------------
def resolve_symbol_from_company(company_name: str, country: str, suffix_map: dict) -> str:
    suffix = suffix_map.get(country, "")
    yahoo_search_url = "https://query2.finance.yahoo.com/v1/finance/search"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    try:
        response = requests.get(yahoo_search_url, params={"q": company_name}, headers=headers)
        response.raise_for_status()
        search_results = response.json()

        # 1. Try exact suffix match
        for item in search_results.get("quotes", []):
            symbol = item.get("symbol", "")
            if symbol.endswith(suffix):
                return symbol

        # 2. Try matching by exchange (fallback logic)
        for item in search_results.get("quotes", []):
            symbol = item.get("symbol", "")
            exchange = item.get("exchange", "").lower()
            if country.lower() in exchange:
                return symbol

        # 3. Final fallback: ask user to pick manually
        st.warning("🔍 Could not auto-detect symbol. Choose from suggestions below:")
        suggestions = [item.get("symbol") for item in search_results.get("quotes", []) if item.get("symbol")]
        if suggestions:
            selected = st.selectbox("Select Matching Symbol", suggestions)
            return selected

        st.error("❌ No matching symbols found.")
        return None

    except Exception as e:
        st.error(f"⚠️ Symbol lookup failed: {e}")
        return None

# ------------------ INPUT FORM ------------------
with st.form("trade_form"):
    col1, col2 = st.columns([2, 2])
    with col1:
        current_idea = st.text_input("💬 Describe Your Trade Idea", placeholder="E.g., Buy Adani after budget news")
    with col2:
        company_query = st.text_input("🏢 Company Name (not ticker)", placeholder="E.g., Adani, TCS, Apple").strip()

    country = st.selectbox("🌐 Country / Market", list(market_suffix.keys()), index=0)

    submitted = st.form_submit_button("Analyze")

if not submitted:
    st.info("Enter a trade idea and company name to continue.")
    st.stop()

# ------------------ SYMBOL LOOKUP ------------------
current_symbol = resolve_symbol_from_company(company_query, country, market_suffix)
if not current_symbol:
    st.stop()

# ------------------ VALIDATE SYMBOL ------------------
try:
    ticker_data = yf.Ticker(current_symbol)
    stock_info = ticker_data.info
    if stock_info.get("currentPrice") is None:
        st.error(f"❌ Symbol '{current_symbol}' not found on {country}'s main exchange.")
        st.stop()
except Exception as e:
    st.error(f"Error checking symbol: {e}")
    st.stop()

# ------------------ TOP 3 BOXES ------------------
box1, box2, box3 = st.columns(3)

# 🧠 Trade Analysis
with box1:
    st.markdown("### 🧠 Trade Analysis")

    try:
        response = requests.post(f"{API_BASE}/analyze", json={"idea": current_idea})
        if response.status_code == 200:
            analysis = response.json().get("analysis", {})

            # 🎯 Strategy & Risk
            st.markdown(f"**🎯 Strategy:** {analysis.get('strategy', '-')}")
            st.markdown(f"**⚖️ Risk Level:** {analysis.get('risk_level', '-')}")

            # 📊 Indicators
            indicators = analysis.get("indicators_to_watch", [])
            st.markdown("**📊 Technical Indicators to Monitor:**")
            if indicators:
                for ind in indicators:
                    st.markdown(f"- {ind}")
            else:
                st.markdown("_No indicators provided._")

            # 📝 Summary
            st.markdown("**📝 Summary:**")
            st.info(analysis.get("summary", "-"))

        else:
            st.error("❌ Failed to get analysis.")

    except Exception as e:
        st.error(f"Analysis error: {e}")

# 📊 Stock Info
with box2:
    st.markdown("### 📊 Stock Info")
    try:
        response = requests.get(f"{API_BASE}/stock_info", params={"symbol": current_symbol})
        if response.status_code == 200:
            data = response.json()
            st.metric("💵 Current Price", data.get("current_price"))
            st.metric("📈 52W High", data.get("52_week_high"))
            st.metric("📉 52W Low", data.get("52_week_low"))
            st.metric("📊 Volume", data.get("volume"))
            st.success(data.get("breakout_hint", ""))

            st.markdown("---")
            st.markdown("**📂 Key Financials**")
            colA, colB = st.columns(2)
            with colA:
                st.markdown(f"**PE Ratio:** {stock_info.get('trailingPE', '—')}")
                st.markdown(f"**EPS:** {stock_info.get('trailingEps', '—')}")
                st.markdown(f"**Beta:** {stock_info.get('beta', '—')}")
                st.markdown(f"**Market Cap:** {stock_info.get('marketCap', '—')}")
            with colB:
                st.markdown(f"**Dividend Yield:** {stock_info.get('dividendYield', '—')}")
                st.markdown(f"**Forward PE:** {stock_info.get('forwardPE', '—')}")
                st.markdown(f"**Analyst Rating:** {stock_info.get('recommendationKey', '—').capitalize()}")
                st.markdown(f"**Sector:** {stock_info.get('sector', '—')}")
        else:
            st.error("❌ Could not load stock info.")
    except Exception as e:
        st.error(f"Stock info error: {e}")

# 📰 News
with box3:
    st.markdown("### 📰 News")
    try:
        latest_news = requests.get(f"{API_BASE}/news", params={"symbol": current_symbol, "type": "latest"}).json()
        impactful_news = requests.get(f"{API_BASE}/news", params={"symbol": current_symbol, "type": "impactful"}).json()

        st.markdown("**🟢 Latest Headlines:**")
        for item in latest_news.get("articles", []):
            st.markdown(f"- {item}")

        st.markdown("**🔴 Impactful News:**")
        for item in impactful_news.get("articles", []):
            st.markdown(f"- {item}")
    except Exception as e:
        st.error(f"News fetch error: {e}")

# ------------------ CANDLESTICK CHART ------------------
st.markdown("### 📈 Live Candlestick Chart")
autorefresh = st_autorefresh(interval=60000, limit=None, key="chart_refresh")

try:
    chart_data = ticker_data.history(interval="5m", period="1d")  # 1 day of 5-minute candles

    fig = go.Figure(data=[
        go.Candlestick(
            x=chart_data.index,
            open=chart_data['Open'],
            high=chart_data['High'],
            low=chart_data['Low'],
            close=chart_data['Close'],
            increasing_line_color='green',
            decreasing_line_color='red'
        )
    ])

    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Chart error: {e}")
