import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import matplotlib.pyplot as plt
import json
import os

# --- UPDATED TEAM NAME MAP ---
TEAM_NAME_MAP = {
    'St. Louis Cardinals': 'St. Louis', 'Pittsburgh Pirates': 'Pittsburgh',
    'New York Yankees': 'NY Yankees', 'Toronto Blue Jays': 'Toronto',
    'Cincinnati Reds': 'Cincinnati', 'Boston Red Sox': 'Boston',
    'Tampa Bay Rays': 'Tampa Bay', 'Baltimore Orioles': 'Baltimore',
    'Texas Rangers': 'Texas', 'Kansas City Royals': 'Kansas City',
    'Seattle Mariners': 'Seattle', 'San Francisco Giants': 'SF Giants',
    'Arizona Diamondbacks': 'Arizona', 'Atlanta Braves': 'Atlanta',
    'Miami Marlins': 'Miami', 'Philadelphia Phillies': 'Philadelphia',
    'Chicago Cubs': 'Chicago Cubs', 'Chicago White Sox': 'Chicago WS',
    'Cleveland Guardians': 'Cleveland', 'Detroit Tigers': 'Detroit',
    'Houston Astros': 'Houston', 'Los Angeles Angels': 'LA Angels',
    'Los Angeles Dodgers': 'LA Dodgers', 'Milwaukee Brewers': 'Milwaukee',
    'Minnesota Twins': 'Minnesota', 'New York Mets': 'NY Mets',
    'Oakland Athletics': 'Oakland', 'San Diego Padres': 'San Diego',
    'Colorado Rockies': 'Colorado', 'Washington Nationals': 'Washington'
}


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

    matchups = [
        ('St. Louis', 'Pittsburgh'),
        ('NY Yankees', 'Toronto'),
        ('Cincinnati', 'Boston'),
        ('Baltimore', 'Texas'),
        ('Kansas City', 'Seattle'),
        ('SF Giants', 'Arizona')
    ]

    seen = set()
    unique_matchups = []
    for away, home in matchups:
        key = tuple(sorted((away, home)))
        if key not in seen:
            seen.add(key)
            unique_matchups.append((away, home))

    return pd.DataFrame({
        'Date': ['2025-06-30'] * len(unique_matchups),
        'Away Team': [m[0] for m in unique_matchups],
        'Home Team': [m[1] for m in unique_matchups],
        'Away SP': ['Erick Fedde', 'Carlos Rodon', 'Chase Burns', 'Trevor Rogers', 'Michael Wacha', 'Logan Webb'],
        'Home SP': ['Andrew Heaney', 'Max Scherzer', 'Garrett Crochet', 'Patrick Corbin', 'George Kirby', 'Ryne Nelson'],
        'Away Runs': [team_runs.get(t[0], 4.5) for t in unique_matchups],
        'Home Runs': [team_runs.get(t[1], 4.5) for t in unique_matchups]
    })


# Fetch MLB team stats from public API with error handling and fallback
def get_stake_odds():
    api_key = "81e55af3da11ceef34cc2920b94ba415"
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/?regions=us&markets=totals,h2h&oddsFormat=american&apiKey={api_key}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        games = response.json()
    except Exception as e:
        st.error(f"❌ Failed to fetch live odds from TheOddsAPI: {e}")
        return {}

    odds_data = {}

    for game in games:
        try:
            home_full = game.get("home_team")
            if not home_full or "bookmakers" not in game:
                continue

            outcomes = []
            for bookmaker in game["bookmakers"]:
                for market in bookmaker["markets"]:
                    if "outcomes" in market:
                        outcomes = market["outcomes"]
                        break
                if outcomes:
                    break

            if not outcomes or len(outcomes) < 2:
                continue

            away_full = [o["name"] for o in outcomes if o["name"] != home_full]
            if not away_full:
                continue
            away_full = away_full[0]

            away = TEAM_NAME_MAP.get(away_full)
            home = TEAM_NAME_MAP.get(home_full)

            if not away or not home:
                st.warning(f"⚠️ Unmapped team(s): {away_full}, {home_full}")
                continue

            key = tuple(sorted((away, home)))

            total_line = None
            moneyline = {}

            for bookmaker in game["bookmakers"]:
                for market in bookmaker["markets"]:
                    if market["key"] == "totals":
                        total_line = market["outcomes"][0].get("point")
                    elif market["key"] == "h2h":
                        moneyline = {
                            TEAM_NAME_MAP.get(o["name"], o["name"]): o["price"]
                            for o in market["outcomes"]
                        }

            odds_data[key] = {
                "total_line": total_line,
                "moneyline": moneyline
            }

        except Exception as e:
            st.warning(f"⚠️ Could not parse game odds: {e}")
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

st.write("🧷 Odds Keys Returned:", list(odds_data.keys()))
st.write("📊 Projections Data Preview:")
st.dataframe(df)

if df.empty or not odds_data:
    st.warning("⚠️ No data available from the MLB API or odds source. Top picks cannot be displayed.")
else:
    def calculate_values(row):
        teams = tuple(sorted((row['Away Team'], row['Home Team'])))
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
