import requests
import json

API_KEY = "81e55af3da11ceef34cc2920b94ba415"
SPORT = "baseball_mlb"
REGION = "us"  # options: us | uk | eu | au
MARKETS = "h2h,totals"  # moneyline and over/under

url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds"

params = {
    "regions": REGION,
    "markets": MARKETS,
    "oddsFormat": "american",
    "apiKey": API_KEY
}

response = requests.get(url, params=params)

if response.status_code == 200:
    data = response.json()
    with open("odds.json", "w") as f:
        json.dump(data, f, indent=2)
    print("✅ Odds saved to odds.json")
else:
    print("❌ Failed to fetch odds:", response.status_code, response.text)
