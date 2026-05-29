# Stradegy v3.1.0 Release Notes

**Release Date:** May 27, 2026
**Codename:** Gem Unlock
**Live URL:** https://stradegy.duckdns.org

---

## Critical Fixes

### Gem Detection Thresholds Lowered
The original thresholds were impossibly high given that most scanners return empty results in production. After logging 209-ticker scans showing 0 gems found, we analyzed the scoring distribution and adjusted:

| Classification | Old | New |
|---------------|-----|-----|
| STRONG | >= 100 | >= 50 |
| POTENTIAL | >= 80 | >= 35 |
| WATCHLIST | >= 60 | >= 25 |

Real-world gems scoring 25-41 (previously DISCARD) will now correctly classify as WATCHLIST or POTENTIAL.

### All Gems Persisted to Database
Previously, gems classified as WATCHLIST or DISCARD were silently discarded with a `logger.debug` call. The UI always showed zero gems because the database was never populated. Now **every gem** is saved to `gem_signals` regardless of classification, making them visible in the Alerts tab.

### Validator Source Requirement Relaxed
The validator required 2+ independent signal sources. With most scanners returning empty due to rate limiting or missing API credentials, this blocked any gem from being approved. Reduced to 1 source so a single strong signal (e.g., Reddit mention + technical confirmation) is actionable.

### Reddit Scanner User-Agent Fixed
The browser-mimicking User-Agent was triggering Reddit 403 blocks. Updated to `Stradegy/3.0.0 (financial research bot)` — a clean, identifiable bot UA that Reddit's public JSON endpoints accept.

---

## Files Changed

| File | Change |
|------|--------|
| `models.py` | Gem thresholds: STRONG 100->50, POTENTIAL 80->35, WATCHLIST 60->25 |
| `validator.py` | Source count requirement: 2->1 |
| `orchestrator.py` | All gems persisted to DB via GemSignalRecord; info-level logging |
| `reddit_scanner.py` | User-Agent updated to bot identity |

---

## Upgrade Instructions

```bash
git pull
cd backend && source .venv/bin/activate && pip install -e .
sudo systemctl restart stradegy   # or ./start.sh
```

After restart, check `/api/alerts` within 15 minutes of the next market open -- gems should appear.

---

*Stradegy v3.1.0 -- Lower the bar, raise the signal.*
