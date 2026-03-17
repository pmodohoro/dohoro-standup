# Dohoro Standup Bot ☕

A free automated daily standup bot for Slack. Sends questions to each team member privately, collects answers one by one, posts results to a channel, and saves everything to a monthly Excel file.

---

## How it works

1. At the scheduled time, the bot DMs each team member privately
2. Questions are asked one by one:
   - Q1: What did you complete yesterday?
   - Q2: What will you work on today?
   - Q3: Anything blocking your progress?
3. After all 3 answers, results are posted to the configured Slack channel
4. Everything is saved to a monthly Excel file
5. Anyone who doesn't reply by the deadline is marked as "Did not submit"

---

## Setup

### Requirements
- Slack workspace (free plan works)
- GitHub account (free)
- Render.com account (free)
- UptimeRobot account (free)

### Environment Variables (set in Render)

| Variable | Description | Example |
|---|---|---|
| `SLACK_BOT_TOKEN` | Bot token from Slack API | `xoxb-...` |
| `SLACK_SIGNING_SECRET` | Signing secret from Slack API | `abc123...` |
| `SLACK_CHANNEL` | Channel(s) to post results (comma separated) | `wpx--todos` or `wpx--todos,general` |
| `STANDUP_HOUR` | Hour to send standup (24hr format, NPT) | `7` |
| `STANDUP_MINUTE` | Minute to send standup | `20` |
| `STANDUP_WINDOW` | Minutes window to submit (e.g. 30 = closes 30 mins after start) | `30` |
| `ALLOWED_MEMBERS` | Team member names (comma separated, exact Slack names) | `Ram Sharma,Sita Thapa` |
| `RENDER_URL` | Your Render URL for keep-alive pings | `https://dohoro-standup.onrender.com` |
| `WEB_CONCURRENCY` | Always set to 1 | `1` |

---

## Managing the bot

### Change standup time
Go to Render → Environment → Edit:
- `STANDUP_HOUR` = hour (24hr format)
- `STANDUP_MINUTE` = minute
- Click Save and Deploy

### Add or remove team members
Go to Render → Environment → Edit:
- `ALLOWED_MEMBERS` = `Name1,Name2,Name3`
- Use exact names as they appear in Slack
- Leave empty to send to ALL workspace members
- Click Save and Deploy

### Change results channel
Go to Render → Environment → Edit:
- `SLACK_CHANNEL` = `channel-name`
- For multiple channels: `channel1,channel2`
- Click Save and Deploy

---

## Useful URLs

| URL | What it does |
|---|---|
| `https://your-app.onrender.com/` | Check bot status |
| `https://your-app.onrender.com/trigger` | Manually trigger standup now |
| `https://your-app.onrender.com/close` | Manually close standup |
| `https://your-app.onrender.com/members` | See allowed members list |
| `https://your-app.onrender.com/download` | Download current month Excel file |

---

## Schedule

Bot runs every **Sunday to Friday** at the configured time (Nepal Time, NPT).
Saturday is off.

---

## Excel Report

Monthly Excel files are auto-generated with these columns:

| Date | Name | Yesterday | Today | Blockers | Status |
|---|---|---|---|---|---|
| 2026-03-17 | Ram Sharma | Fixed bug | New feature | None | Submitted |
| 2026-03-17 | Sita Thapa | - | - | - | Did not submit |

Download anytime from:
```
https://your-app.onrender.com/download
```

---

## Tech Stack

- **Python** + **Flask** — web server
- **Slack SDK** — Slack API integration
- **APScheduler** — scheduled jobs
- **OpenPyXL** — Excel file generation
- **Gunicorn** — production server
- **Render.com** — free hosting
- **UptimeRobot** — keep-alive pings

---

## Total Cost: FREE 🎉
