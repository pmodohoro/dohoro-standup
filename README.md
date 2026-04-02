# Dohoro Standup Bot ☕

A free automated daily standup bot for Slack. Sends questions to each team member privately one by one, collects answers, posts beautifully formatted results to team-specific channels, and saves everything to monthly Excel files.

---

## How it works

1. At **7:25am NPT**, bot DMs each team member privately
2. Questions are asked one by one:
   - ✅ What did you complete yesterday?
   - 💻 What will you work on today?
   - 🚧 Anything blocking your progress?
3. Answers are posted to the team's dedicated Slack channel with colored card
4. Everything saved to a monthly Excel file per team
5. Anyone who doesn't reply by **8:10am** is marked as "Did not submit"
6. Late submissions (after 8:10am) are still accepted — tagged as late
7. Users can edit their submission anytime by typing `edit` in the bot DM

---

## Features

- ✅ 3 separate teams (DEV, QA, UIUX) each with dedicated channels
- ✅ Questions asked one by one — Q1 → Q2 → Q3
- ✅ Beautiful colored cards in channel (green/red/purple per team)
- ✅ Status badges — On time / Late / Edited / Did not submit
- ✅ Edit standup anytime by typing `edit` in bot DM
- ✅ Late submissions accepted anytime during the day
- ✅ Monthly Excel reports per team — downloadable anytime
- ✅ Admin alerts if something goes wrong
- ✅ Bot never sleeps — kept alive by UptimeRobot
- ✅ Slack retry protection — no duplicate questions
- ✅ Event deduplication — each message processed only once
- ✅ File-based sessions — no memory loss on restart
- ✅ All settings manageable from Render — no code changes ever needed
- ✅ Works for 20+ people simultaneously
- ✅ Runs Sunday to Friday only

---

## Setup Requirements

- Slack workspace (free plan works)
- GitHub account (free)
- Render.com account (free)
- UptimeRobot account (free)

---

## Slack App Permissions

### Bot Token Scopes
Add these in **api.slack.com → OAuth & Permissions → Bot Token Scopes:**
- `chat:write`
- `im:write`
- `im:read`
- `im:history`
- `users:read`
- `channels:read`
- `groups:read`
- `groups:history`

### Event Subscriptions
Add these in **api.slack.com → Event Subscriptions → Subscribe to bot events:**
- `message.im`
- `message.channels`
- `message.groups`

### App Home
Enable in **api.slack.com → App Home:**
- ✅ Home Tab — ON
- ✅ Messages Tab — ON
- ✅ Allow users to send messages — checked

---

## Environment Variables (Render)

| Variable | Description | Example |
|---|---|---|
| `SLACK_BOT_TOKEN` | Bot token from Slack API | `xoxb-...` |
| `SLACK_SIGNING_SECRET` | Signing secret from Slack API | `abc123...` |
| `DEV_MEMBERS` | Dev team names (comma separated, exact Slack names) | `Suraj Pahari,Sujan Thapa` |
| `DEV_CHANNEL` | Dev team Slack channel name | `standup-wpx-dev` |
| `QA_MEMBERS` | QA team names | `Amrita Shrestha,Kabita Banstola` |
| `QA_CHANNEL` | QA team Slack channel name | `standup-qa` |
| `UIUX_MEMBERS` | UIUX team names | `Supreme Gaire,Safalta Shrestha` |
| `UIUX_CHANNEL` | UIUX team Slack channel name | `standup-uiux` |
| `STANDUP_HOUR` | Hour to send standup (24hr NPT) | `7` |
| `STANDUP_MINUTE` | Minute to send standup | `25` |
| `STANDUP_WINDOW` | Minutes window to submit | `45` |
| `ADMIN_SLACK_ID` | Admin Slack IDs for alerts (comma separated) | `U08XXXXX,U09XXXXX` |
| `RENDER_URL` | Your Render app URL | `https://dohoro-standup.onrender.com` |
| `WEB_CONCURRENCY` | Always set to 1 | `1` |

---

## Managing the bot (from Render only — no coding needed)

### Change standup time
Render → Environment → Edit → change `STANDUP_HOUR` and `STANDUP_MINUTE` → Save and Deploy

### Add team member
Render → Environment → Edit → add name to `DEV_MEMBERS` / `QA_MEMBERS` / `UIUX_MEMBERS` → Save and Deploy

### Remove team member
Render → Environment → Edit → remove name from the list → Save and Deploy

### Change results channel
Render → Environment → Edit → update `DEV_CHANNEL` / `QA_CHANNEL` / `UIUX_CHANNEL` → Save and Deploy

### Change standup window
Render → Environment → Edit → update `STANDUP_WINDOW` (minutes) → Save and Deploy

---

## Useful URLs

| URL | What it does |
|---|---|
| `/` | Check bot status, teams and timing |
| `/ping` | Health check — returns pong |
| `/members` | View all team members and channels |
| `/trigger` | Manually trigger standup now |
| `/close` | Manually close standup |
| `/download` | See all download links |
| `/download/dev` | Download DEV team Excel report |
| `/download/qa` | Download QA team Excel report |
| `/download/uiux` | Download UIUX team Excel report |

---

## User Guide (for team members)

| Action | How |
|---|---|
| Submit standup | Wait for 7:25am DM → answer Q1, Q2, Q3 |
| Submit late | Just message the bot anytime — it starts Q1 automatically |
| Edit submission | Type `edit` in the bot DM |
| Find the bot | Slack sidebar → Apps → Dohoro_Standup |
| Never miss it | Star the bot in your Slack sidebar |

---

## Status Badges

| Badge | Meaning |
|---|---|
| ✅ Submitted on time | Before 8:10am deadline |
| ⏰ Submitted late | After 8:10am deadline |
| ✏️ Edited | Updated after submission |
| ⚠️ Did not submit | No response received |

---

## Channel Colors

| Team | Border color |
|---|---|
| DEV | 🟢 Green |
| QA | 🔴 Red |
| UIUX | 🟣 Purple |

---

## Excel Reports

Monthly Excel files saved per team with columns:

`Date | Time | Name | Team | Yesterday | Today | Blockers | Status`

**Important:** Download Excel at end of each month — Render free tier resets `/tmp` on restart!

Download links:
- `https://your-app.onrender.com/download/dev`
- `https://your-app.onrender.com/download/qa`
- `https://your-app.onrender.com/download/uiux`

---

## Current Team Setup

### DEV team → #standup-wpx-dev
Suraj Pahari, Sujan Thapa, Sangam Giri, Samir Karki, Sajan Adhikari, Rupesh Acharya, Nishan Bishwokarma, Hem Pun, Dikshyant Aryal,Arjun Adhikari

### QA team → #standup-qa
Amrita Shrestha, Kabita Banstola, Dikshyant Adhikari

### UIUX team → #standup-uiux
Supreme Gaire, Safalta Shrestha, Yakeen Kapali

---

## Tech Stack

- **Python + Flask** — web server
- **Slack SDK** — Slack API
- **APScheduler** — scheduled jobs
- **OpenPyXL** — Excel generation
- **Gunicorn** — production server
- **Render.com** — free hosting
- **UptimeRobot** — keep alive

---

## Total Cost: FREE 🎉
