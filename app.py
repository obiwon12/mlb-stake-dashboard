import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
from datetime import datetime

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

# --- Live Run Projections via ESPN Scraper ---
def get_live_run_projections():
    url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
    try:
        response = requests.get(url)
        response.raise_for_status()
        games = response.json().get("events", [])
    except Exception as e:
        st.error(f"❌ Failed to fetch live projections: {e}")
        return pd.DataFrame()

    rows = []
    for game in games:
        competitions = game.get("competitions", [{}])[0]
        competitors = competitions.get("competitors", [])
        if len(competitors) < 2:
            continue

        away_team = competitors[0] if competitors[0].get("homeAway") == "away" else competitors[1]
        home_team = competitors[0] if competitors[0].get("homeAway") == "home" else competitors[1]

        away = TEAM_NAME_MAP.get(away_team.get("team", {}).get("displayName"))
        home = TEAM_NAME_MAP.get(home_team.get("team", {}).get("displayName"))
        if not away or not home:
            continue

        date = game.get("date", "").split("T")[0]
        # Use neutral baseline for now
        rows.append({
            'Date': date,
            'Away Team': away,
            'Home Team': home,
            'Away Runs': 4.5,
            'Home Runs': 4.5
        })

    return pd.DataFrame(rows)

# --- Get Canadian Odds from TheOddsAPI ---
def get_stake_odds():
    api_key = "81e55af3da11ceef34cc2920b94ba415"
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/?regions=ca&markets=totals,h2h&oddsFormat=decimal&apiKey={api_key}"

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

            away_full = [o["name"] for o in outcomes if o["name"] != home_full][0]

            away = TEAM_NAME_MAP.get(away_full)
            home = TEAM_NAME_MAP.get(home_full)
            if not away or not home:
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
        except:
            continue

    return odds_data

@st.cache_data
def get_top_confidence_plays(df):
    confidence_map = {'🟩 2U': 3, '⬜️ 1U': 2, '🟥 0.5U': 1}
    df['Score'] = df['Confidence'].map(confidence_map)
    return df.sort_values(by='Score', ascending=False).head(3)

st.title(f"🏆 MLB Top 3 Confidence Picks - {datetime.today().strftime('%B %d')}")
df = get_live_run_projections()
odds_data = get_stake_odds()

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
        elif away_odds >= 2.3:
            moneyline_value = 'GOOD'
        elif away_odds <= 1.3:
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

    st.subheader("📊 Projections Data Preview:")
    st.dataframe(df[['Date', 'Away Team', 'Home Team', 'Away Runs', 'Home Runs', 'Total Runs', 'Total Line', 'Total Play', 'Winner Odds', 'Moneyline Value']])

    if top_picks.empty:
        st.warning("⚠️ No confident plays found for today.")
    else:
        st.subheader("✅ Top 3 Confidence Plays")
        st.dataframe(top_picks[['Date', 'Away Team', 'Home Team', 'Away Runs', 'Home Runs', 'Total Runs', 'Total Line', 'Total Play', 'Winner Odds', 'Moneyline Value', 'Confidence']])
