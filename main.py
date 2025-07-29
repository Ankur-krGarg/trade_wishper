from fastapi import FastAPI, Query
from pydantic import BaseModel
import cohere
import os
from dotenv import load_dotenv
import json
import yfinance as yf

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="TradeWhisper API", description="AI + Stock data microservice", version="1.0")

# Initialize Cohere client using the API key
co = cohere.Client(os.getenv("COHERE_API_KEY"))

# ---------- Endpoint 1: Trade Analysis (LLM) ----------

class TradeRequest(BaseModel):
    idea: str

@app.post("/analyze", summary="Analyze trade idea using LLM", response_description="Structured trade analysis")
async def analyze_trade(trade: TradeRequest):
    """
    Input a trade idea in plain English (e.g., 'Buy AAPL after earnings drop').
    Returns AI-generated insights: strategy, risk, indicators, and summary.
    """
    prompt = f"""
You are a AI based professional Equity and Trade research assistant who helps retail traders understand trade ideas. Your tone is factual, ethical, and concise.

Analyze the following trade idea and respond ONLY in JSON format. Do NOT include markdown, headings, or text outside the JSON.

Required JSON structure:
{{
  "strategy": "Describe the trading strategy type (e.g., momentum, breakout, swing)",
  "risk_level": "Low | Moderate | High (based on volatility, timing, leverage)",
  "indicators_to_watch": ["List relevant technical indicators"],
  "summary": "Short, ethical explanation for the trade idea in plain English (no hype, no financial advice)"
}}

Trade idea: "{trade.idea}"
"""

    # Send prompt to Cohere Chat API
    response = co.chat(
        model="command-r-plus-04-2024",
        message=prompt,
        temperature=0.6
    )

    # Clean markdown-style output if present
    raw_text = response.text.strip()
    if raw_text.startswith("```json"):
        raw_text = raw_text.strip("```json").strip("```").strip()

    # Try parsing the LLM output as JSON
    try:
        parsed_json = json.loads(raw_text)
    except Exception:
        return {"error": "LLM response is not valid JSON", "raw_output": raw_text}

    return {"analysis": parsed_json}

# ---------- Endpoint 2: Stock Info ----------

@app.get("/stock_info", summary="Get basic stock info", response_description="Stock price range and breakout hint")
async def get_stock_info(symbol: str = Query(..., description="Stock ticker symbol, e.g. AAPL or TSLA")):
    """
    Returns min/max price, 52-week high/low, volume, and breakout condition.
    """
    try:
        stock = yf.Ticker(symbol)
        info = stock.info

        return {
            "symbol": symbol.upper(),
            "current_price": info.get("currentPrice"),
            "52_week_high": info.get("fiftyTwoWeekHigh"),
            "52_week_low": info.get("fiftyTwoWeekLow"),
            "volume": info.get("volume"),
            "breakout_hint": "Near breakout zone" if info.get("currentPrice", 0) >= info.get("fiftyTwoWeekHigh", 0) * 0.98 else "Not in breakout zone"
        }

    except Exception as e:
        return {"error": f"Could not fetch info for {symbol}", "details": str(e)}

# ---------- Endpoint 3: Chart Data ----------

@app.get("/chart_data", summary="Get stock chart data", response_description="6-month daily close prices")
async def get_chart_data(symbol: str = Query(..., description="Stock ticker symbol, e.g. AAPL")):
    """
    Returns 6-month closing prices (daily) for use in charting.
    """
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period="6mo")

        return {
            "symbol": symbol.upper(),
            "dates": hist.index.strftime('%Y-%m-%d').tolist(),
            "prices": hist["Close"].round(2).tolist()
        }

    except Exception as e:
        return {"error": f"Could not fetch chart data for {symbol}", "details": str(e)}

# ---------- Endpoint 4: Simulated News ----------

@app.get("/news", summary="Get latest or impactful news", response_description="Dummy news headlines")
async def get_news(
    symbol: str = Query(..., description="Stock ticker symbol, e.g. TSLA"),
    type: str = Query("latest", enum=["latest", "impactful"], description="Type of news: 'latest' or 'impactful'")
):
    """
    Simulated news feed for demo/testing. Replace with real News API later.
    """
    dummy_news = {
        "latest": [
            f"{symbol.upper()} jumped 3.2% after strong earnings report.",
            f"{symbol.upper()} trading volume increased significantly this week."
        ],
        "impactful": [
            f"{symbol.upper()} dropped 10% after executive resignation.",
            f"{symbol.upper()} under SEC investigation over disclosures."
        ]
    }

    return {
        "symbol": symbol.upper(),
        "type": type,
        "articles": dummy_news.get(type, [])
    }
