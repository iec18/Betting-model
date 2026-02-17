# “””
⚽ BETTING MODEL V5 — LIVE DATA PIPELINE

Run this script weekly to update the model with fresh data.

WHAT IT DOES:

1. Scrapes FBref for xG data (all UEFA feeder leagues)
1. Downloads Football-Data.co.uk CSVs for corners/cards
1. Calculates rolling 5-game form for every team
1. Updates xg_data_live.json automatically
1. Model uses this fresh data on next analysis run

HOW TO RUN:
python data_pipeline.py              # Full update
python data_pipeline.py –league EPL # Single league
python data_pipeline.py –check      # Verify data freshness

REQUIREMENTS:
pip install requests beautifulsoup4 pandas lxml

SCHEDULE (recommended):
Run every Monday morning before placing bets
Or after every matchday to keep form data current
“””

import requests
import pandas as pd
from bs4 import BeautifulSoup
import json
import os
import time
import argparse
from datetime import datetime, timedelta

# ============================================================

# CONFIG

# ============================================================

DATA_DIR = os.path.dirname(os.path.abspath(**file**))
XG_FILE = os.path.join(DATA_DIR, “xg_data_live.json”)
CORNERS_FILE = os.path.join(DATA_DIR, “corners_data_live.json”)
CARDS_FILE = os.path.join(DATA_DIR, “cards_data_live.json”)
LOG_FILE = os.path.join(DATA_DIR, “pipeline_log.json”)

HEADERS = {
“User-Agent”: “Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36”
}

# How many recent games to use for rolling form

FORM_GAMES = 5

# How much weight to give recent form vs season average

FORM_WEIGHT = 0.4  # 40% recent, 60% season

# ============================================================

# LEAGUE CONFIG

# Maps league names to FBref URLs and Football-Data codes

# ============================================================

LEAGUES = {
# TOP 5 LEAGUES
“EPL”: {
“name”: “Premier League”,
“country”: “England”,
“fbref_url”: “https://fbref.com/en/comps/9/Premier-League-Stats”,
“fbref_squad_url”: “https://fbref.com/en/comps/9/shooting/Premier-League-Stats”,
“fd_url”: “https://www.football-data.co.uk/mmz4281/2526/E0.csv”,
“card_avg”: 3.8,
“red_avg”: 0.12,
},
“LaLiga”: {
“name”: “La Liga”,
“country”: “Spain”,
“fbref_url”: “https://fbref.com/en/comps/12/La-Liga-Stats”,
“fbref_squad_url”: “https://fbref.com/en/comps/12/shooting/La-Liga-Stats”,
“fd_url”: “https://www.football-data.co.uk/mmz4281/2526/SP1.csv”,
“card_avg”: 4.2,
“red_avg”: 0.18,
},
“Bundesliga”: {
“name”: “Bundesliga”,
“country”: “Germany”,
“fbref_url”: “https://fbref.com/en/comps/20/Bundesliga-Stats”,
“fbref_squad_url”: “https://fbref.com/en/comps/20/shooting/Bundesliga-Stats”,
“fd_url”: “https://www.football-data.co.uk/mmz4281/2526/D1.csv”,
“card_avg”: 3.5,
“red_avg”: 0.10,
},
“SerieA”: {
“name”: “Serie A”,
“country”: “Italy”,
“fbref_url”: “https://fbref.com/en/comps/11/Serie-A-Stats”,
“fbref_squad_url”: “https://fbref.com/en/comps/11/shooting/Serie-A-Stats”,
“fd_url”: “https://www.football-data.co.uk/mmz4281/2526/I1.csv”,
“card_avg”: 4.8,
“red_avg”: 0.22,
},
“Ligue1”: {
“name”: “Ligue 1”,
“country”: “France”,
“fbref_url”: “https://fbref.com/en/comps/13/Ligue-1-Stats”,
“fbref_squad_url”: “https://fbref.com/en/comps/13/shooting/Ligue-1-Stats”,
“fd_url”: “https://www.football-data.co.uk/mmz4281/2526/F1.csv”,
“card_avg”: 4.1,
“red_avg”: 0.15,
},

```
# UEFA FEEDER LEAGUES
"Portugal": {
    "name": "Primeira Liga",
    "country": "Portugal",
    "fbref_url": "https://fbref.com/en/comps/32/Primeira-Liga-Stats",
    "fbref_squad_url": "https://fbref.com/en/comps/32/shooting/Primeira-Liga-Stats",
    "fd_url": "https://www.football-data.co.uk/mmz4281/2526/P1.csv",
    "card_avg": 4.5,
    "red_avg": 0.20,
},
"Eredivisie": {
    "name": "Eredivisie",
    "country": "Netherlands",
    "fbref_url": "https://fbref.com/en/comps/23/Eredivisie-Stats",
    "fbref_squad_url": "https://fbref.com/en/comps/23/shooting/Eredivisie-Stats",
    "fd_url": "https://www.football-data.co.uk/mmz4281/2526/N1.csv",
    "card_avg": 3.6,
    "red_avg": 0.11,
},
"Belgium": {
    "name": "Belgian Pro League",
    "country": "Belgium",
    "fbref_url": "https://fbref.com/en/comps/37/Belgian-Pro-League-Stats",
    "fbref_squad_url": "https://fbref.com/en/comps/37/shooting/Belgian-Pro-League-Stats",
    "fd_url": "https://www.football-data.co.uk/mmz4281/2526/B1.csv",
    "card_avg": 4.0,
    "red_avg": 0.14,
},
"Scotland": {
    "name": "Scottish Premiership",
    "country": "Scotland",
    "fbref_url": "https://fbref.com/en/comps/40/Scottish-Premiership-Stats",
    "fbref_squad_url": "https://fbref.com/en/comps/40/shooting/Scottish-Premiership-Stats",
    "fd_url": "https://www.football-data.co.uk/mmz4281/2526/SC0.csv",
    "card_avg": 3.9,
    "red_avg": 0.13,
},
"Turkey": {
    "name": "Süper Lig",
    "country": "Turkey",
    "fbref_url": "https://fbref.com/en/comps/26/Super-Lig-Stats",
    "fbref_squad_url": "https://fbref.com/en/comps/26/shooting/Super-Lig-Stats",
    "fd_url": "https://www.football-data.co.uk/mmz4281/2526/T1.csv",
    "card_avg": 5.2,
    "red_avg": 0.25,
},
"Austria": {
    "name": "Austrian Bundesliga",
    "country": "Austria",
    "fbref_url": "https://fbref.com/en/comps/56/Austrian-Football-Bundesliga-Stats",
    "fbref_squad_url": "https://fbref.com/en/comps/56/shooting/Austrian-Football-Bundesliga-Stats",
    "fd_url": "https://www.football-data.co.uk/mmz4281/2526/A1.csv",
    "card_avg": 3.7,
    "red_avg": 0.12,
},
"Greece": {
    "name": "Super League",
    "country": "Greece",
    "fbref_url": "https://fbref.com/en/comps/27/Super-League-Greece-Stats",
    "fbref_squad_url": "https://fbref.com/en/comps/27/shooting/Super-League-Greece-Stats",
    "fd_url": "https://www.football-data.co.uk/mmz4281/2526/G1.csv",
    "card_avg": 4.6,
    "red_avg": 0.21,
},
"CzechRep": {
    "name": "Czech First League",
    "country": "Czech Republic",
    "fbref_url": "https://fbref.com/en/comps/66/Czech-First-League-Stats",
    "fbref_squad_url": "https://fbref.com/en/comps/66/shooting/Czech-First-League-Stats",
    "fd_url": "https://www.football-data.co.uk/mmz4281/2526/CZ1.csv",
    "card_avg": 3.8,
    "red_avg": 0.13,
},
"Denmark": {
    "name": "Superliga",
    "country": "Denmark",
    "fbref_url": "https://fbref.com/en/comps/50/Danish-Superliga-Stats",
    "fbref_squad_url": "https://fbref.com/en/comps/50/shooting/Danish-Superliga-Stats",
    "fd_url": "https://www.football-data.co.uk/mmz4281/2526/DK1.csv",
    "card_avg": 3.5,
    "red_avg": 0.10,
},
"Norway": {
    "name": "Eliteserien",
    "country": "Norway",
    "fbref_url": "https://fbref.com/en/comps/28/Eliteserien-Stats",
    "fbref_squad_url": "https://fbref.com/en/comps/28/shooting/Eliteserien-Stats",
    "fd_url": "https://www.football-data.co.uk/mmz4281/2526/NO1.csv",
    "card_avg": 3.4,
    "red_avg": 0.09,
},
"Switzerland": {
    "name": "Super League",
    "country": "Switzerland",
    "fbref_url": "https://fbref.com/en/comps/57/Swiss-Super-League-Stats",
    "fbref_squad_url": "https://fbref.com/en/comps/57/shooting/Swiss-Super-League-Stats",
    "fd_url": "https://www.football-data.co.uk/mmz4281/2526/SZ1.csv",
    "card_avg": 3.6,
    "red_avg": 0.11,
},
"Croatia": {
    "name": "HNL",
    "country": "Croatia",
    "fbref_url": "https://fbref.com/en/comps/63/Croatian-Football-League-Stats",
    "fbref_squad_url": "https://fbref.com/en/comps/63/shooting/Croatian-Football-League-Stats",
    "fd_url": "https://www.football-data.co.uk/mmz4281/2526/HR1.csv",
    "card_avg": 4.2,
    "red_avg": 0.16,
},
```

}

# ============================================================

# SCRAPER 1 — FBREF xG DATA

# ============================================================

def scrape_fbref_xg(league_key):
“””
Scrapes FBref squad shooting stats to get xG for/against per team.
Returns dict: {team_name: {xG_h, xG_a, xGA_h, xGA_a}}
“””
league = LEAGUES[league_key]
url = league[“fbref_squad_url”]

```
print(f"  Scraping FBref: {league['name']}...", end=" ")

try:
    time.sleep(4)  # Be respectful — FBref rate limits aggressively
    resp = requests.get(url, headers=HEADERS, timeout=15)
    
    if resp.status_code == 429:
        print("⚠️ Rate limited — waiting 60 seconds")
        time.sleep(60)
        resp = requests.get(url, headers=HEADERS, timeout=15)
    
    if resp.status_code != 200:
        print(f"❌ HTTP {resp.status_code}")
        return None
    
    soup = BeautifulSoup(resp.content, "lxml")
    
    # Find the squad shooting table (for xG)
    table = soup.find("table", {"id": "stats_squads_shooting_for"})
    if not table:
        # Try alternative table ID
        table = soup.find("table", id=lambda x: x and "shooting" in x)
    
    if not table:
        print("❌ Table not found")
        return None
    
    teams_xg = {}
    rows = table.find("tbody").find_all("tr")
    
    for row in rows:
        if row.get("class") and "thead" in row.get("class", []):
            continue
        
        team_cell = row.find("td", {"data-stat": "team"})
        xg_cell = row.find("td", {"data-stat": "xg"})
        npxg_cell = row.find("td", {"data-stat": "npxg"})
        
        if not team_cell or not xg_cell:
            continue
        
        team_name = team_cell.get_text(strip=True)
        xg_val = xg_cell.get_text(strip=True)
        
        try:
            xg_total = float(xg_val)
            teams_xg[team_name] = {"xg_for": xg_total}
        except:
            continue
    
    # Now get xG against
    table_against = soup.find("table", {"id": "stats_squads_shooting_against"})
    if table_against:
        rows = table_against.find("tbody").find_all("tr")
        for row in rows:
            team_cell = row.find("td", {"data-stat": "team"})
            xg_cell = row.find("td", {"data-stat": "xg"})
            if not team_cell or not xg_cell:
                continue
            team_name = team_cell.get_text(strip=True)
            try:
                xga_total = float(xg_cell.get_text(strip=True))
                if team_name in teams_xg:
                    teams_xg[team_name]["xg_against"] = xga_total
            except:
                continue
    
    print(f"✅ {len(teams_xg)} teams found")
    return teams_xg
    
except Exception as e:
    print(f"❌ Error: {str(e)[:50]}")
    return None
```

# ============================================================

# SCRAPER 2 — FOOTBALL-DATA.CO.UK (Corners, Cards, Results)

# ============================================================

def download_fd_csv(league_key):
“””
Downloads Football-Data CSV for a league.
Contains: home/away corners, cards, results per match.
“””
league = LEAGUES[league_key]
url = league[“fd_url”]

```
print(f"  Downloading Football-Data: {league['name']}...", end=" ")

try:
    time.sleep(1)
    resp = requests.get(url, headers=HEADERS, timeout=15)
    
    if resp.status_code != 200:
        print(f"❌ HTTP {resp.status_code}")
        return None
    
    # Parse CSV
    from io import StringIO
    df = pd.read_csv(StringIO(resp.text), on_bad_lines='skip')
    
    # Drop empty rows
    df = df.dropna(subset=["HomeTeam", "AwayTeam"])
    
    print(f"✅ {len(df)} matches loaded")
    return df
    
except Exception as e:
    print(f"❌ Error: {str(e)[:50]}")
    return None
```

# ============================================================

# PROCESSOR — Calculate per-team stats from match data

# ============================================================

def calculate_team_stats(df, league_key, n_games=FORM_GAMES):
“””
From raw match CSV, calculate:
- Home/Away corners for/against
- Home/Away cards per game
- Last N games form
Returns dict: {team: {c_h, c_a, ca_h, ca_a, cards_h, cards_a, form}}
“””
league = LEAGUES[league_key]
team_stats = {}

```
# Column mappings (Football-Data format)
col_maps = {
    "home_corners": ["HC", "HCorners"],
    "away_corners": ["AC", "ACorners"],
    "home_yellow": ["HY", "HYELL"],
    "away_yellow": ["AY", "AYELL"],
    "home_red": ["HR", "HRED"],
    "away_red": ["AR", "ARED"],
    "home_goals": ["FTHG", "HG"],
    "away_goals": ["FTAG", "AG"],
}

def get_col(df, options):
    for col in options:
        if col in df.columns:
            return col
    return None

hc_col = get_col(df, col_maps["home_corners"])
ac_col = get_col(df, col_maps["away_corners"])
hy_col = get_col(df, col_maps["home_yellow"])
ay_col = get_col(df, col_maps["away_yellow"])
hr_col = get_col(df, col_maps["home_red"])
ar_col = get_col(df, col_maps["away_red"])
hg_col = get_col(df, col_maps["home_goals"])
ag_col = get_col(df, col_maps["away_goals"])

all_teams = set(df["HomeTeam"].tolist() + df["AwayTeam"].tolist())

for team in all_teams:
    home_matches = df[df["HomeTeam"] == team].tail(n_games * 3)
    away_matches = df[df["AwayTeam"] == team].tail(n_games * 3)
    
    stats = {
        "c_h": 5.0,   # Default corners home
        "c_a": 4.0,   # Default corners away
        "ca_h": 5.0,  # Default corners against home
        "ca_a": 5.5,  # Default corners against away
        "cards_h": league["card_avg"],
        "cards_a": league["card_avg"],
        "form": [],
    }
    
    # Corners when playing at home
    if hc_col and len(home_matches) > 0:
        stats["c_h"] = round(home_matches[hc_col].mean(), 2)
    if ac_col and len(home_matches) > 0:
        stats["ca_h"] = round(home_matches[ac_col].mean(), 2)
    
    # Corners when playing away
    if ac_col and len(away_matches) > 0:
        stats["c_a"] = round(away_matches[ac_col].mean(), 2)
    if hc_col and len(away_matches) > 0:
        stats["ca_a"] = round(away_matches[hc_col].mean(), 2)
    
    # Cards per game
    if hy_col and hr_col and len(home_matches) > 0:
        home_cards = home_matches[hy_col].fillna(0) + home_matches[hr_col].fillna(0)
        away_cards_in_home = home_matches[ay_col].fillna(0) + home_matches[ar_col].fillna(0) if ay_col else 0
        stats["cards_h"] = round((home_cards + away_cards_in_home).mean(), 1)
    
    # Recent form (last 5 games W/D/L)
    if hg_col and ag_col:
        all_matches = []
        for _, row in home_matches.iterrows():
            try:
                hg, ag = int(row[hg_col]), int(row[ag_col])
                result = "W" if hg > ag else ("D" if hg == ag else "L")
                all_matches.append({"result": result, "scored": hg, "conceded": ag})
            except:
                pass
        for _, row in away_matches.iterrows():
            try:
                hg, ag = int(row[hg_col]), int(row[ag_col])
                result = "W" if ag > hg else ("D" if hg == ag else "L")
                all_matches.append({"result": result, "scored": ag, "conceded": hg})
            except:
                pass
        stats["form"] = [m["result"] for m in all_matches[-5:]]
    
    team_stats[team] = stats

return team_stats
```

# ============================================================

# PROCESSOR — Calculate xG per team from FBref + match count

# ============================================================

def calculate_xg_per_game(fbref_data, df, team_name, league_key):
“””
Converts FBref season totals to per-game home/away averages
using actual home/away match counts from the CSV.
“””
league = LEAGUES[league_key]

```
if not fbref_data or team_name not in fbref_data:
    return None

raw = fbref_data[team_name]
xg_for_total = raw.get("xg_for", 0)
xg_against_total = raw.get("xg_against", 0)

if df is not None and len(df) > 0:
    home_games = len(df[df["HomeTeam"] == team_name])
    away_games = len(df[df["AwayTeam"] == team_name])
    
    if home_games > 0 and away_games > 0:
        # Rough split (FBref totals include both home and away)
        xg_h = round(xg_for_total / (home_games + away_games) * (1 + 0.15), 2)
        xg_a = round(xg_for_total / (home_games + away_games) * (1 - 0.10), 2)
        xga_h = round(xg_against_total / (home_games + away_games) * (1 - 0.15), 2)
        xga_a = round(xg_against_total / (home_games + away_games) * (1 + 0.10), 2)
        
        return {
            "xG_h": xg_h,
            "xG_a": xg_a,
            "xGA_h": xga_h,
            "xGA_a": xga_a,
            "league": league_key,
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "games_h": home_games,
            "games_a": away_games,
        }

return None
```

# ============================================================

# MAIN PIPELINE

# ============================================================

def run_pipeline(leagues_to_update=None, dry_run=False):
“””
Main entry point. Updates all data files.
“””
print(”=”*70)
print(”  ⚽ LIVE DATA PIPELINE — V5”)
print(f”  {datetime.now().strftime(’%A %d %B %Y %H:%M’)}”)
print(”=”*70)

```
# Load existing data
existing_xg = {}
if os.path.exists(XG_FILE):
    with open(XG_FILE) as f:
        existing_xg = json.load(f)

existing_corners = {}
if os.path.exists(CORNERS_FILE):
    with open(CORNERS_FILE) as f:
        existing_corners = json.load(f)

if leagues_to_update is None:
    leagues_to_update = list(LEAGUES.keys())

updated_teams = []
failed_leagues = []

print(f"\n  Updating {len(leagues_to_update)} leagues...")
print(f"  Strategy: FBref (xG) + Football-Data (corners/cards)\n")

for league_key in leagues_to_update:
    league = LEAGUES[league_key]
    print(f"\n  📋 {league['name']} ({league['country']})")
    print(f"  {'─'*50}")
    
    # Step 1: Get match data from Football-Data
    df = download_fd_csv(league_key)
    
    # Step 2: Calculate corners/cards from match data
    if df is not None:
        team_stats = calculate_team_stats(df, league_key)
        for team, stats in team_stats.items():
            existing_corners[team] = {
                "c_h": stats["c_h"],
                "c_a": stats["c_a"],
                "ca_h": stats["ca_h"],
                "ca_a": stats["ca_a"],
                "league": league_key,
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
            }
        print(f"  ✅ Corners/cards updated for {len(team_stats)} teams")
    
    # Step 3: Get xG from FBref
    fbref_data = scrape_fbref_xg(league_key)
    
    if fbref_data and df is not None:
        for team_name, raw in fbref_data.items():
            xg_data = calculate_xg_per_game(fbref_data, df, team_name, league_key)
            if xg_data:
                existing_xg[team_name] = xg_data
                updated_teams.append(team_name)
        print(f"  ✅ xG updated for {len(fbref_data)} teams")
    else:
        print(f"  ⚠️  xG scrape failed — keeping existing data")
        failed_leagues.append(league_key)
    
    # Be nice to servers
    time.sleep(3)

# Save updated files
if not dry_run:
    with open(XG_FILE, "w") as f:
        json.dump(existing_xg, f, indent=2)
    
    with open(CORNERS_FILE, "w") as f:
        json.dump(existing_corners, f, indent=2)
    
    # Log the run
    log = {
        "last_run": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "leagues_updated": [l for l in leagues_to_update if l not in failed_leagues],
        "leagues_failed": failed_leagues,
        "teams_updated": len(updated_teams),
    }
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)

print(f"\n\n{'='*70}")
print(f"  ✅ PIPELINE COMPLETE")
print(f"{'='*70}")
print(f"  Teams updated: {len(updated_teams)}")
print(f"  Leagues failed: {failed_leagues if failed_leagues else 'None'}")
print(f"  Files saved: xg_data_live.json, corners_data_live.json")
print(f"\n  Run model_v4_pro.py to use fresh data")
print("="*70)

return len(updated_teams), failed_leagues
```

# ============================================================

# DATA FRESHNESS CHECK

# ============================================================

def check_freshness():
“””
Check when data was last updated and whether it needs refreshing.
“””
print(”=”*70)
print(”  🔍 DATA FRESHNESS CHECK”)
print(”=”*70)

```
if not os.path.exists(LOG_FILE):
    print("\n  ❌ No pipeline log found — data never updated")
    print("  Run: python data_pipeline.py")
    return

with open(LOG_FILE) as f:
    log = json.load(f)

last_run = datetime.strptime(log["last_run"], "%Y-%m-%d %H:%M")
days_ago = (datetime.now() - last_run).days

if days_ago == 0:
    status = "🔥 FRESH — Updated today"
elif days_ago <= 3:
    status = f"✅ OK — Updated {days_ago} days ago"
elif days_ago <= 7:
    status = f"⚠️  STALE — Updated {days_ago} days ago (update recommended)"
else:
    status = f"❌ VERY STALE — Updated {days_ago} days ago (must update)"

print(f"\n  Status: {status}")
print(f"  Last run: {log['last_run']}")
print(f"  Teams in database: {log.get('teams_updated', '?')}")
print(f"  Leagues updated: {len(log.get('leagues_updated', []))}")

if log.get("leagues_failed"):
    print(f"  ⚠️  Failed leagues: {log['leagues_failed']}")

if days_ago > 3:
    print(f"\n  👉 Run: python data_pipeline.py")

print("="*70)
```

# ============================================================

# TEAM NAME NORMALIZER

# Football-Data and FBref use different team names

# ============================================================

TEAM_NAME_MAP = {
# Premier League
“Man United”: “Manchester United”,
“Man City”: “Manchester City”,
“Nottm Forest”: “Nottingham Forest”,
“Wolves”: “Wolverhampton Wanderers”,
“Spurs”: “Tottenham Hotspur”,
# La Liga
“Atletico”: “Atletico Madrid”,
“Betis”: “Real Betis”,
“Celta”: “Celta Vigo”,
# Bundesliga
“Bayern”: “Bayern Munich”,
“Dortmund”: “Borussia Dortmund”,
“Leverkusen”: “Bayer Leverkusen”,
“Leipzig”: “RB Leipzig”,
“Frankfurt”: “Eintracht Frankfurt”,
“Gladbach”: “Borussia Monchengladbach”,
“Werder”: “Werder Bremen”,
# Serie A
“Inter”: “Inter Milan”,
“Juventus”: “Juventus”,
“Milan”: “AC Milan”,
# Ligue 1
“PSG”: “Paris Saint-Germain”,
# Portugal
“Sporting”: “Sporting CP”,
# Turkey
“Galatasaray”: “Galatasaray SK”,
}

def normalize_team_name(name, direction=“to_model”):
“”“Convert between Football-Data/FBref names and model names”””
if direction == “to_model”:
# Reverse lookup
for model_name, source_name in TEAM_NAME_MAP.items():
if source_name.lower() == name.lower():
return model_name
return name
else:
return TEAM_NAME_MAP.get(name, name)

# ============================================================

# CLI INTERFACE

# ============================================================

if **name** == “**main**”:
parser = argparse.ArgumentParser(description=“Live data pipeline for betting model”)
parser.add_argument(”–league”, help=“Update single league (e.g. EPL, LaLiga)”)
parser.add_argument(”–check”, action=“store_true”, help=“Check data freshness”)
parser.add_argument(”–dry-run”, action=“store_true”, help=“Test without saving”)
parser.add_argument(”–list”, action=“store_true”, help=“List all supported leagues”)
args = parser.parse_args()

```
if args.check:
    check_freshness()

elif args.list:
    print("\n  Supported leagues:")
    for key, league in LEAGUES.items():
        print(f"  {key:<15} {league['name']} ({league['country']})")

elif args.league:
    if args.league not in LEAGUES:
        print(f"  ❌ Unknown league: {args.league}")
        print(f"  Run with --list to see all options")
    else:
        run_pipeline([args.league], dry_run=args.dry_run)

else:
    # Full update
    run_pipeline(dry_run=args.dry_run)
```