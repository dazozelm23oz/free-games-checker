# 🎮 Free Games Checker

An automated tracker and notification sidecar that checks for 100% free-to-keep PC games across **Epic Games Store**, **Steam**, and other gaming platforms.

## ✨ Features

- **Store Integrations:** Queries Epic Games Store Promotions API and GamerPower giveaways.
- **Noise Filtering:** Filters out DLCs, beta playtests, and external key giveaways to prioritize standalone full games.
- **Claim Tracking:** Maintains local history in `claimed_games.json` to avoid duplicate notifications once a game is claimed.
- **Direct Claim Links:** Provides direct store links for one-click claiming.
- **Antigravity Automation Sidecar:** Configured with `sidecar.json` for scheduled execution twice daily.

## 🚀 Usage

### Check Active Games
```bash
python check_free_games.py
```

### Mark a Game as Claimed
```bash
python check_free_games.py --claim "Game Title" --platform "Epic Games Store"
```

### Unclaim a Game
```bash
python check_free_games.py --unclaim "Game Title"
```

### View Claim History
```bash
python check_free_games.py --list-claimed
```

## ⚙️ Automation & Sidecar

The included `sidecar.json` configures Antigravity to run this checker twice daily (at 1:00 AM and 7:00 PM Africa/Cairo time).
