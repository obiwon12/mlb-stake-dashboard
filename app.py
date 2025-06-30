import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import matplotlib.pyplot as plt
import json
import os

# Mapping from API names to dashboard names
TEAM_NAME_MAP = {
    'St. Louis Cardinals': 'St. Louis', 'Pittsburgh Pirates': 'Pittsburgh',
    'New York Yankees': 'NY Yankees', 'Toronto Blue Jays': 'Toronto',
    'Cincinnati Reds': 'Cincinnati', 'Boston Red Sox': 'Boston',
    'Tampa Bay Rays': 'Tampa Bay', 'Baltimore Orioles': 'Baltimore',
    'Texas Rangers': 'Texas', 'Kansas City Royals': 'Kansas City',
    'Seattle Mariners': 'Seattle', 'San Francisco Giants': 'SF Giants',
    'Arizona Diamondbacks': 'Arizona'
}

# Fetch MLB team stats from public API with error handling and fallback
def get_live_run_projections():
    teams = {v: k for k, v in TEAM_NAME_MAP.items()}
    base_url = "https://statsapi.mlb.com/api/v1/teams/stats"
    params = {"season": "2024", "group": "hitting", "stats": "season"}
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        with open("cached_team_stats.json", "w") as f:
            json.dump(data, f)
    except Exception:
        st.warning("⚠️ Using cached data due to API issue.")
        if os.path.exists("cached_team_stats.json"):
            with open("cached_team_stats.json", "r") as f:
                data = json.load(f)
        else:
            st.error("❌ No cached data available. Displaying fallback averages.")
            return pd.DataFrame()

    team_runs = {}
    for team_stat in data['stats'][0]['splits']:
        name = team_stat['team']['name']
        avg_runs = float(team_stat['stat'].get('runsPerGame', 4.5))
        abbr = TEAM_NAME_MAP.get(name)
        if abbr:
            team_runs[abbr] = avg_runs

    return pd.DataFrame({
        'Date': ['2025-06-30']*7,
        'Away Team': ['St. Louis', 'NY Yankees', 'Cincinnati', 'Baltimore', 'Kansas City', 'SF Giants', 'Toronto'],
        'Home Team': ['Pittsburgh', 'Toronto', 'Boston', 'Texas', 'Seattle', 'Arizona', 'NY Yankees'],
        'Away SP': ['Erick Fedde', 'Carlos Rodon', 'Chase Burns', 'Trevor Rogers', 'Michael Wacha', 'Logan Webb', 'Chris Bassitt'],
        'Home SP': ['Andrew Heaney', 'Max Scherzer', 'Garrett Crochet', 'Patrick Corbin', 'George Kirby', 'Ryne Nelson', 'Nestor Cortes'],
        'Away Runs': [team_runs.get(t, 4.5) for t in ['St. Louis', 'NY Yankees', 'Cincinnati', 'Baltimore', 'Kansas City', 'SF Giants', 'Toronto']],
        'Home Runs': [team_runs.get(t, 4.5) for t in ['Pittsburgh', 'Toronto', 'Boston', 'Texas', 'Seattle', 'Arizona', 'NY Yankees']]
    })

# Fetch live odds from TheOddsAPI
def get_stake_odds():
    api_key = "81e55af3da11ceef34cc2920b94ba415"
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/?regions=us&markets=totals,h2h&oddsFormat=american&apiKey={api_key}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        games = response.json()
    except Exception:
        st.error("❌ Failed to fetch live odds from TheOddsAPI.")
        return {}

    odds_data = {}
    for game in games:
        try:
            home_full = game["home_team"]
            teams = game["teams"]
            away_full = [t for t in teams if t != home_full][0]

            away = TEAM_NAME_MAP.get(away_full)
            home = TEAM_NAME_MAP.get(home_full)
            if not away or not home:
                continue

            key = (away, home)

            total = next((m for m in game["bookmakers"][0]["markets"] if m["key"] == "totals"), None)
            total_line = total["outcomes"][0]["point"] if total else None

            h2h = next((m for m in game["bookmakers"][0]["markets"] if m["key"] == "h2h"), None)
            moneyline = {TEAM_NAME_MAP.get(o["name"], o["name"]): o["price"] for o in h2h["outcomes"]} if h2h else {}

            odds_data[key] = {
                "total_line": total_line,
                "moneyline": moneyline
            }
        except:
            continue

    return odds_data

# Display top 3 bets
@st.cache_data
def get_top_confidence_plays(df):
    if "Confidence" not in df.columns:
        st.error("Missing 'Confidence' column in data.")
        return pd.DataFrame()
    confidence_map = {'🟩 2U': 3, '⬜️ 1U': 2, '🟥 0.5U': 1}
    df['Score'] = df['Confidence'].map(confidence_map)
    return df.sort_values(by='Score', ascending=False).head(3)

# Inject top picks into Streamlit view
st.subheader("🏆 Top 3 Picks by Confidence")
df = get_live_run_projections()
odds_data = get_stake_odds()

if df.empty or not odds_data:
    st.warning("⚠️ No data available from the MLB API or odds source. Top picks cannot be displayed.")
else:
    def calculate_values(row):
        teams = (row['Away Team'], row['Home Team'])
        total_proj = row['Away Runs'] + row['Home Runs']
        odds = odds_data.get(teams, {})
        total_line = odds.get('total_line', np.nan)
        total_play = 'Over' if total_proj > total_line else 'Under'

        away_odds = odds.get('moneyline', {}).get(row['Away Team'])
        if away_odds is None:
            moneyline_value = 'NEUTRAL'
        elif away_odds > 130:
            moneyline_value = 'GOOD'
        elif away_odds < -170:
            moneyline_value = 'BAD'
        else:
            moneyline_value = 'NEUTRAL'

        diff = abs(total_proj - total_line)
        if diff >= 1.0:
            confidence = '🟩 2U'
        elif diff >= 0.5:
            confidence = '⬜️ 1U'
        else:
            confidence = '🟥 0.5U'

        return pd.Series([total_proj, total_line, total_play, away_odds, moneyline_value, confidence])

    df[['Total Runs', 'Total Line', 'Total Play', 'Winner Odds', 'Moneyline Value', 'Confidence']] = df.apply(calculate_values, axis=1)
    top_picks = get_top_confidence_plays(df)

    if top_picks.empty:
        st.warning("⚠️ No confident plays found for today.")
    else:
        st.dataframe(top_picks.drop(columns=["Score"]))
