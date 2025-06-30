import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# Simulated Stake.ca odds (replace with scraper later)
def get_stake_odds():
    return {
        ('St. Louis', 'Pittsburgh'): {'total_line': 9.0, 'moneyline': {'St. Louis': -105, 'Pittsburgh': -105}},
        ('NY Yankees', 'Toronto'): {'total_line': 8.5, 'moneyline': {'NY Yankees': -140, 'Toronto': +120}},
        ('Cincinnati', 'Boston'): {'total_line': 8.0, 'moneyline': {'Boston': -170, 'Cincinnati': +150}},
        ('Sacramento', 'Tampa Bay'): {'total_line': 8.0, 'moneyline': {'Tampa Bay': -165, 'Sacramento': +145}},
        ('Baltimore', 'Texas'): {'total_line': 8.0, 'moneyline': {'Texas': -110, 'Baltimore': -110}},
        ('Kansas City', 'Seattle'): {'total_line': 7.5, 'moneyline': {'Kansas City': +125, 'Seattle': -130}},
        ('SF Giants', 'Arizona'): {'total_line': 8.5, 'moneyline': {'SF Giants': -135, 'Arizona': +115}},
    }

# Simulated run projections (replace with FanGraphs API)
def get_run_projections():
    return pd.DataFrame({
        'Date': ['2025-06-30']*7,
        'Away Team': ['St. Louis', 'NY Yankees', 'Cincinnati', 'Sacramento', 'Baltimore', 'Kansas City', 'SF Giants'],
        'Home Team': ['Pittsburgh', 'Toronto', 'Boston', 'Tampa Bay', 'Texas', 'Seattle', 'Arizona'],
        'Away SP': ['Erick Fedde', 'Carlos Rodon', 'Chase Burns', 'Jacob Lopez', 'Trevor Rogers', 'Michael Wacha', 'Logan Webb'],
        'Home SP': ['Andrew Heaney', 'Max Scherzer', 'Garrett Crochet', 'Drew Rasmussen', 'Patrick Corbin', 'George Kirby', 'Ryne Nelson'],
        'Away Runs': [4.29, 4.82, 3.86, 3.56, 3.50, 4.26, 4.58],
        'Home Runs': [4.07, 3.98, 4.72, 4.72, 3.57, 3.72, 3.96]
    })

# Simulated head-to-head stats and standings
def get_h2h_stats():
    return {
        ('St. Louis', 'Pittsburgh'): 'Last 10: STL 6-4 | Avg Score: 5.1 - 4.6',
        ('NY Yankees', 'Toronto'): 'Last 10: NYY 7-3 | Avg Score: 6.0 - 3.5',
        ('Cincinnati', 'Boston'): 'Last 10: BOS 5-5 | Avg Score: 4.4 - 4.1',
        ('Sacramento', 'Tampa Bay'): 'Last 10: TB 8-2 | Avg Score: 5.8 - 3.0',
        ('Baltimore', 'Texas'): 'Last 10: TEX 6-4 | Avg Score: 4.9 - 4.6',
        ('Kansas City', 'Seattle'): 'Last 10: SEA 6-4 | Avg Score: 4.5 - 3.9',
        ('SF Giants', 'Arizona'): 'Last 10: ARI 6-4 | Avg Score: 5.0 - 4.5',
    }

# Confidence scoring and unit assignment
def calculate_values(row, odds_data):
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

    # Confidence logic (unit assignment)
    diff = abs(total_proj - total_line)
    if diff >= 1.0:
        confidence = '🟩 2U'
    elif diff >= 0.5:
        confidence = '⬜️ 1U'
    else:
        confidence = '🟥 0.5U'

    return pd.Series([total_proj, total_line, total_play, away_odds, moneyline_value, confidence])

# Streamlit UI
st.set_page_config(layout="wide")
st.title("MLB Betting Dashboard - Stake.ca")

st.markdown("---")
odds_data = get_stake_odds()
projections = get_run_projections()
h2h_stats = get_h2h_stats()

# Filters
dates = projections['Date'].unique()
teams = sorted(set(projections['Away Team']) | set(projections['Home Team']))

selected_date = st.selectbox("Select Game Date:", dates)
selected_team = st.selectbox("Filter by Team (optional):", ["All"] + teams)

filtered = projections[projections['Date'] == selected_date]
if selected_team != "All":
    filtered = filtered[(filtered['Away Team'] == selected_team) | (filtered['Home Team'] == selected_team)]

filtered[['Total Runs', 'Total Line', 'Total Play', 'Winner Odds', 'Moneyline Value', 'Confidence']] = filtered.apply(
    calculate_values, axis=1, odds_data=odds_data
)

# Show H2H details in sidebar on selection
st.sidebar.markdown("### Matchup Insights")
for i, row in filtered.iterrows():
    matchup = (row['Away Team'], row['Home Team'])
    st.sidebar.markdown(f"**{row['Away Team']} vs {row['Home Team']}**")
    st.sidebar.markdown(h2h_stats.get(matchup, 'No recent H2H data'))
    st.sidebar.markdown("---")

# Display main table
st.dataframe(filtered[['Away Team', 'Home Team', 'Away SP', 'Home SP', 'Total Runs', 'Total Line', 'Total Play', 'Winner Odds', 'Moneyline Value', 'Confidence']].style.applymap(
    lambda x: 'background-color: lightgreen' if '🟩' in str(x) else ('background-color: lightcoral' if '🟥' in str(x) else ('background-color: lightyellow' if '⬜️' in str(x) else '')),
    subset=['Confidence']
).applymap(
    lambda x: 'background-color: lightyellow' if x == 'Over' else ('background-color: lightblue' if x == 'Under' else ''),
    subset=['Total Play']
))
