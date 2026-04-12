# PVI Range Calculator

SPX weekly PVI range predictor. Runs as a web app, iOS home screen app, or locally.

## Features

- **Auto-fetches** live SPX & VIX from Yahoo Finance on open
- **Auto-updates** every Saturday via GitHub Actions (no manual input needed)
- **Installable on iOS** — add to home screen for a native app feel
- **Works offline** — service worker caches last known data
- **Prediction history** saved in browser localStorage

## Formula

```
PVI Low/High = round(Close × (1 ∓ k × VIX/100 × √(5/252)))
```

| VIX | Regime | k |
|-----|--------|---|
| < 17 | Calm | 1.60 |
| ≥ 17 | Stressed | 1.80 |

Calibrated on 12 weeks of 2026 SPX data. Avg error: ~33 pts Low, ~36 pts High.

---

## Setup (5 minutes)

### 1. Create GitHub repo

1. Go to [github.com/new](https://github.com/new)
2. Name it `pvi-calculator` (or anything you like)
3. Set to **Public** (required for free GitHub Pages)
4. Click **Create repository**

### 2. Upload the files

Drag and drop all files from this folder into the repo, or use GitHub Desktop.

Files to upload:
```
index.html
manifest.json
sw.js
data/market.json
.github/workflows/saturday-update.yml
README.md
```

### 3. Enable GitHub Pages

1. Go to repo **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / `/ (root)`
4. Click **Save**

Your app will be live at: `https://YOUR-USERNAME.github.io/pvi-calculator/`

### 4. Add repo permissions for the Action

1. Go to repo **Settings → Actions → General**
2. Under "Workflow permissions" → select **Read and write permissions**
3. Click **Save**

The GitHub Action now runs every Saturday at 9pm ET automatically.
You can also trigger it manually: **Actions → Saturday Market Update → Run workflow**.

---

## Install on iPhone (no App Store needed)

1. Open your GitHub Pages URL in Safari
2. Tap the **Share** button (box with arrow)
3. Tap **Add to Home Screen**
4. Tap **Add**

It will appear on your home screen and open full-screen like a native app.

---

## Generate App Icons (optional)

You need two PNG files for the iOS icon:
- `icon-192.png` (192×192px)
- `icon-512.png` (512×512px)

You can generate these from any image using [realfavicongenerator.net](https://realfavicongenerator.net).

Without icons, the app still works — it just uses a default browser icon.

---

## Running locally

Just open `index.html` in any browser. The auto-fetch button calls Yahoo Finance directly.
No server needed.

For the Saturday auto-update to work locally, you'd run the Python script in
`.github/workflows/saturday-update.yml` manually, or just use the fetch button.
