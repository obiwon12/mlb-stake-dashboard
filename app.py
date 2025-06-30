import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import matplotlib.pyplot as plt
import json
import os

# Fetch MLB team stats from public API with error handling and fallback

def get_live_run_projections():
    teams = {
        'St. Louis': 'St. Louis Cardinals', 'Pittsburgh': 'Pittsburgh Pirates',
        'NY Yankees': 'New York Yankees', 'Toronto': 'Toronto Blue Jays',
        'Cincinnati': 'Cincinnati Reds', 'Boston': 'Boston Red Sox',
        'Sacramento': 'Sacramento', 'Tampa Bay': 'Tampa Bay Rays',
        'Baltimore': 'Baltimore Orioles', 'Texas': 'Texas Rangers',
        'Kansas City': 'Kansas City Royals', 'Seattle': 'Seattle Mariners',
        'SF Giants': 'San Francisco Giants', 'Arizona': 'Arizona Diamondbacks'
    }

    base_url = "https://statsapi.mlb.com/api/v1/teams/stats"
    params = {"season": "2024", "group": "hitting", "stats": "season"}
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        with open("cached_team_stats.json", "w") as f:
            json.dump(data, f)
    except Exception as e:
        st.warning("⚠️ Using cached data due to API issue.")
        if os.path.exists("cached_team_stats.json"):
            with open("cached_team_stats.json", "r") as f:
                data = json.load(f)
        else:
            st.error("❌ No cached data available. Displaying fallback averages.")
            return pd.DataFrame({})

    team_runs = {}
    for team_stat in data['stats'][0]['splits']:
        name = team_stat['team']['name']
        avg_runs = float(team_stat['stat'].get('runsPerGame', 4.5))
        for abbr, full in teams.items():
            if name == full:
                team_runs[abbr] = avg_runs

    return pd.DataFrame({
        'Date': ['2025-06-30']*7,
        'Away Team': ['St. Louis', 'NY Yankees', 'Cincinnati', 'Sacramento', 'Baltimore', 'Kansas City', 'SF Giants'],
        'Home Team': ['Pittsburgh', 'Toronto', 'Boston', 'Tampa Bay', 'Texas', 'Seattle', 'Arizona'],
        'Away SP': ['Erick Fedde', 'Carlos Rodon', 'Chase Burns', 'Jacob Lopez', 'Trevor Rogers', 'Michael Wacha', 'Logan Webb'],
        'Home SP': ['Andrew Heaney', 'Max Scherzer', 'Garrett Crochet', 'Drew Rasmussen', 'Patrick Corbin', 'George Kirby', 'Ryne Nelson'],
        'Away Runs': [team_runs.get(t, 4.5) for t in ['St. Louis', 'NY Yankees', 'Cincinnati', 'Sacramento', 'Baltimore', 'Kansas City', 'SF Giants']],
        'Home Runs': [team_runs.get(t, 4.5) for t in ['Pittsburgh', 'Toronto', 'Boston', 'Tampa Bay', 'Texas', 'Seattle', 'Arizona']]
    })

# Simulated Stake.ca odds (from local file)
def get_stake_odds():
    with open("odds.json", "r") as f:
        data = f.read()
    return {
        ('St. Louis', 'Pittsburgh'): {'total_line': 9.0, 'moneyline': {'St. Louis': -105, 'Pittsburgh': -105}},
        ('NY Yankees', 'Toronto'): {'total_line': 8.5, 'moneyline': {'NY Yankees': -140, 'Toronto': +120}},
        ('Cincinnati', 'Boston'): {'total_line': 8.0, 'moneyline': {'Boston': -170, 'Cincinnati': +150}},
        ('Sacramento', 'Tampa Bay'): {'total_line': 8.0, 'moneyline': {'Tampa Bay': -165, 'Sacramento': +145}},
        ('Baltimore', 'Texas'): {'total_line': 8.0, 'moneyline': {'Texas': -110, 'Baltimore': -110}},
        ('Kansas City', 'Seattle'): {'total_line': 7.5, 'moneyline': {'Kansas City': +125, 'Seattle': -130}},
        ('SF Giants', 'Arizona'): {'total_line': 8.5, 'moneyline': {'SF Giants': -135, 'Arizona': +115}},
    }

# Display top 3 bets
@st.cache_data
def get_top_confidence_plays(df):
    confidence_map = {'🟩 2U': 3, '⬜️ 1U': 2, '🟥 0.5U': 1}
    df['Score'] = df['Confidence'].map(confidence_map)
    return df.sort_values(by='Score', ascending=False).head(3)

# Inject top picks into Streamlit view
st.subheader("🏆 Top 3 Picks by Confidence")
try:
    top_picks = get_top_confidence_plays(get_live_run_projections())
    st.dataframe(top_picks.drop(columns=["Score"]))
except:
    st.warning("Unable to display top picks.")
