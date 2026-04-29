import requests, json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.espn.com.mx/"
}

r = requests.get(
    "https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/teams/219/schedule",
    headers=HEADERS
)

data = r.json()

season_types = set()
for evento in data.get("events", []):
    st = evento.get("seasonType", {})
    season_types.add((st.get("id"), st.get("name")))

for s in sorted(season_types):
    print(s)