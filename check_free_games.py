import json
import urllib.request
import sys
import os
import re
from datetime import datetime, timezone

# Ensure UTF-8 output even in Windows cmd/powershell
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLAIMED_FILE = os.path.join(SCRIPT_DIR, "claimed_games.json")

def load_claimed_db():
    if not os.path.exists(CLAIMED_FILE):
        return {"tracking_started": datetime.now().strftime("%Y-%m-%d"), "claimed_games": []}
    try:
        with open(CLAIMED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"tracking_started": datetime.now().strftime("%Y-%m-%d"), "claimed_games": []}

def save_claimed_db(data):
    with open(CLAIMED_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def normalize_title(title):
    if not title:
        return ""
    # Remove giveaway noise words
    for noise in ['(epic games) giveaway', '(steam) giveaway', 'giveaway', 'playtest']:
        title = title.lower().replace(noise, '')
    # Keep only alphanumeric
    return re.sub(r'[^a-z0-9]', '', title.lower())

def titles_match(t1, t2):
    n1 = normalize_title(t1)
    n2 = normalize_title(t2)
    if not n1 or not n2:
        return False
    if n1 == n2:
        return True
    if (n1.startswith(n2) or n2.startswith(n1)) and min(len(n1), len(n2)) >= 4:
        return True
    return False

def find_claimed_entry(title, claimed_list):
    for entry in claimed_list:
        if titles_match(title, entry.get('title', '')):
            return entry
    return None

def is_expired(date_str):
    if not date_str or date_str == 'N/A':
        return False
    try:
        if 'T' in date_str:
            clean_str = date_str.replace('Z', '+00:00')
            dt = datetime.fromisoformat(clean_str)
            return dt < datetime.now(timezone.utc)
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return dt < datetime.now(timezone.utc)
    except Exception:
        return False

def is_key_giveaway(item):
    """Excludes any giveaways requiring redeeming external product keys."""
    title = item.get('title', '').lower()
    g_type = item.get('type', '').lower()
    desc = item.get('description', '').lower()
    inst = item.get('instructions', '').lower()
    
    if re.search(r'\bkeys?\b', title) or 'key' in g_type:
        return True
    key_phrases = [
        'unlock your key', 'redeem your', 'steam key', 
        'claim a key', 'to unlock a key', 'game key', 'product key'
    ]
    if any(p in desc or p in inst for p in key_phrases):
        return True
    return False

def fetch_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception:
        return None

def get_epic_official():
    url = "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions?locale=en-US&country=US&allowCountries=US"
    data = fetch_json(url)
    if not data:
        return []
    
    games = []
    try:
        elements = data['data']['Catalog']['searchStore']['elements']
        for item in elements:
            promos = item.get('promotions')
            if not promos:
                continue
            offers = promos.get('promotionalOffers')
            if offers and len(offers) > 0 and len(offers[0].get('promotionalOffers', [])) > 0:
                po = offers[0]['promotionalOffers'][0]
                if po.get('discountSetting', {}).get('discountPercentage') == 0:
                    end_date = po.get('endDate')
                    if is_expired(end_date):
                        continue
                    slug = item.get('productSlug') or (item.get('catalogNs', {}).get('mappings', [{}])[0].get('pageSlug') if item.get('catalogNs', {}).get('mappings') else None) or item.get('urlSlug')
                    link = f"https://store.epicgames.com/p/{slug}" if slug else "https://store.epicgames.com/free-games"
                    games.append({
                        'title': item.get('title'),
                        'platform': 'Epic Games Store',
                        'type': 'Game',
                        'worth': '100% off',
                        'end_date': end_date,
                        'url': link,
                        'source': 'Epic Games Store'
                    })
    except Exception:
        pass
    return games

def get_gamerpower_giveaways():
    games = []
    for platform in ['steam', 'epic-games-store']:
        data = fetch_json(f"https://www.gamerpower.com/api/giveaways?platform={platform}")
        if not data or not isinstance(data, list):
            continue
        for item in data:
            if is_key_giveaway(item):
                continue
            # Only standalone full games (skip DLCs, loot, early access playtests)
            g_type = item.get('type', '')
            if g_type.lower() not in ['game', 'full game']:
                continue
            end_date = item.get('end_date')
            if is_expired(end_date):
                continue
            games.append({
                'title': item.get('title'),
                'platform': item.get('platforms'),
                'type': 'Game',
                'worth': item.get('worth', 'N/A'),
                'end_date': end_date,
                'url': item.get('open_giveaway_url') or item.get('gamerpower_url'),
                'source': f'GamerPower ({platform})'
            })
    return games

def claim_game_cli(title, platform='PC', worth='Free', url=''):
    db = load_claimed_db()
    existing = find_claimed_entry(title, db['claimed_games'])
    today = datetime.now().strftime("%Y-%m-%d")
    if existing:
        print(f"'{title}' is already recorded as claimed on {existing.get('claimed_at')}.")
        return
    db['claimed_games'].append({
        'title': title,
        'platform': platform,
        'worth': worth,
        'claimed_at': today,
        'url': url
    })
    save_claimed_db(db)
    print(f"Marked '{title}' as claimed on {today}.")

def unclaim_game_cli(title):
    db = load_claimed_db()
    initial_len = len(db['claimed_games'])
    db['claimed_games'] = [g for g in db['claimed_games'] if not titles_match(g.get('title', ''), title)]
    if len(db['claimed_games']) < initial_len:
        save_claimed_db(db)
        print(f"Removed '{title}' from claimed history.")
    else:
        print(f"'{title}' was not found in claimed history.")

def main():
    args = sys.argv[1:]
    if '--claim' in args:
        idx = args.index('--claim')
        if idx + 1 < len(args):
            title = args[idx + 1]
            platform = 'PC'
            if '--platform' in args:
                p_idx = args.index('--platform')
                if p_idx + 1 < len(args):
                    platform = args[p_idx + 1]
            claim_game_cli(title, platform=platform)
            return
    if '--unclaim' in args:
        idx = args.index('--unclaim')
        if idx + 1 < len(args):
            unclaim_game_cli(args[idx + 1])
            return
    if '--list-claimed' in args:
        db = load_claimed_db()
        print(f"### Claimed Games History (Tracking started: {db.get('tracking_started', '2026-10-29')})\n")
        for g in db.get('claimed_games', []):
            print(f"- ✅ **{g['title']}** ({g.get('platform', 'PC')}) — Claimed on {g.get('claimed_at', 'N/A')}")
        return

    # Regular Report Generation
    db = load_claimed_db()
    claimed_history = db.get('claimed_games', [])
    start_date = db.get('tracking_started', '2026-10-29')

    epic_games = get_epic_official()
    gp_games = get_gamerpower_giveaways()

    combined = []

    for g in epic_games:
        if not any(titles_match(g['title'], c['title']) for c in combined):
            combined.append(g)

    for g in gp_games:
        matched = next((c for c in combined if titles_match(g['title'], c['title'])), None)
        if not matched:
            combined.append(g)
        elif (matched.get('worth') in ['100% off', 'Free', 'N/A']) and g.get('worth') and g.get('worth') not in ['100% off', 'Free', 'N/A']:
            matched['worth'] = g['worth']

    full_games = [g for g in combined if g['type'].lower() in ['game', 'full game']]

    # Partition active full games into unclaimed vs claimed
    ready_to_claim = []
    active_claimed = []

    for g in full_games:
        claimed_entry = find_claimed_entry(g['title'], claimed_history)
        if claimed_entry:
            g_copy = dict(g)
            g_copy['claimed_at'] = claimed_entry.get('claimed_at')
            active_claimed.append(g_copy)
        else:
            ready_to_claim.append(g)

    print("## 🎮 Free PC Games Daily Status Report (Standalone Full Games Only)\n")

    # 1. Ready to Claim
    print("### 🟢 Ready to Claim (Available Now & Not Yet Claimed)\n")
    if ready_to_claim:
        for g in ready_to_claim:
            end = g.get('end_date') or 'Limited time'
            worth = g.get('worth', '')
            worth_str = f" (Value: {worth})" if worth and worth != 'N/A' else ""
            print(f"- **[{g['title']}]({g['url']})**{worth_str}")
            print(f"  - **Platform:** {g['platform']}")
            print(f"  - **Expires:** {end}")
            print(f"  - **Direct Claim Link:** {g['url']}\n")
    else:
        print("🎉 You have claimed all currently active free games!\n")

    # 2. Available & Already Claimed
    print("### ✅ Available Now & Already Claimed\n")
    if active_claimed:
        for g in active_claimed:
            print(f"- **[{g['title']}]({g['url']})**")
            print(f"  - **Platform:** {g['platform']}")
            print(f"  - **Status:** Claimed on {g.get('claimed_at', 'today')}")
            print(f"  - **Expires for others:** {g.get('end_date', 'N/A')}\n")
    else:
        print("None of the currently active giveaways have been marked as claimed yet.\n")

    # 3. All Claimed History
    print(f"### 📜 All Claimed Games History (Since {start_date})\n")
    if claimed_history:
        for idx, g in enumerate(claimed_history, 1):
            url_part = f" - [Store Page]({g['url']})" if g.get('url') else ""
            print(f"{idx}. **{g['title']}** ({g.get('platform', 'PC')}) — *Claimed: {g.get('claimed_at', 'N/A')}*{url_part}")
        print()
    else:
        print("No claimed games recorded yet.\n")

if __name__ == '__main__':
    main()
