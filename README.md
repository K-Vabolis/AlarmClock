# Account Timers

A small desktop app that tracks reset timers for your accounts and pops up a reminder when time is up.

Built with Python and Tkinter. No extra packages needed.

## Features

- **Two timer types**
  - **Countdown**: set a length in days, hours, minutes and seconds
  - **Clock time**: fires at a set time on your computer's clock (24-hour), once or **daily**
- **Popup alert** that stays on top, with a sound, when a timer ends
- **Status colors**: Running, Almost (under 10 minutes left), Reset now
- **Auto re-arm**: daily timers set themselves for the next day
- **Remembered names**: reuse account names from a dropdown
- **Auto-save**: timers survive closing the app
- Dark theme, including the title bar on Windows 10/11

## Requirements

- Python 3.8+ (with Tkinter, included in the standard Windows installer)
- Windows recommended (the dark title bar is Windows-only, everything else works anywhere)

## Install and run

1. Install [Python](https://www.python.org/downloads/) and tick **"Add Python to PATH"**.
2. Download this repo.
3. Double-click `run_account_timers.bat`

Or run it manually:

```bash
python account_timers.py
```

## How to use

| Action | How |
|---|---|
| Add a timer | **Add** button |
| Edit a timer | Double-click, or press Enter |
| Restart a timer | Select it and click **Restart**, or use the popup |
| Delete a timer | Select it and press Delete, or right-click > Delete |

## Data

Timers are saved to `~/.account_timers.json` in your user folder. Delete that file to reset everything.

## Files

- `account_timers.py` : the app
- `run_account_timers.bat` : Windows launcher (no console window)

## License

MIT
