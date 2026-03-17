import os
import threading
import requests
from datetime import datetime, timedelta
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import openpyxl
from openpyxl import load_workbook
import pytz

app = Flask(__name__)
client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

NPT = pytz.timezone("Asia/Kathmandu")

CHANNEL_NAME = os.environ.get("SLACK_CHANNEL", "wpx--todos")
STANDUP_HOUR = int(os.environ.get("STANDUP_HOUR", "7"))
STANDUP_MINUTE = int(os.environ.get("STANDUP_MINUTE", "20"))
STANDUP_WINDOW_MINUTES = int(os.environ.get("STANDUP_WINDOW", "45"))
ALLOWED_MEMBERS = os.environ.get("ALLOWED_MEMBERS", "")
RENDER_URL = os.environ.get("RENDER_URL", "https://dohoro-standup.onrender.com")

QUESTIONS = [
    "👋 Good morning! Time for your daily standup!\n\n*Question 1 of 3:* ✅ What did you complete yesterday?",
    "*Question 2 of 3:* 🔨 What will you work on today?",
    "*Question 3 of 3:* 🚧 Anything blocking your progress? (Type 'none' if nothing)"
]

user_sessions = {}
sessions_lock = threading.Lock()
excel_lock = threading.Lock()

def keep_alive():
    try:
        requests.get(RENDER_URL, timeout=10)
        print(f"✅ Keep alive ping sent at {datetime.now(NPT).strftime('%H:%M NPT')}")
    except Exception as e:
        print(f"Keep alive failed: {e}")

def get_allowed_names():
    if not ALLOWED_MEMBERS.strip():
        return []
    return [n.strip().lower() for n in ALLOWED_MEMBERS.split(",") if n.strip()]

def get_excel_filepath():
    now = datetime.now(NPT)
    return f"/tmp/standup_{now.strftime('%B-%Y')}.xlsx"

def save_to_excel(user_name, answers, did_not_submit=False):
    filepath = get_excel_filepath()
    now = datetime.now(NPT)
    date_str = now.strftime("%Y-%m-%d")
    with excel_lock:
        try:
            wb = load_workbook(filepath)
            ws = wb.active
        except FileNotFoundError:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = now.strftime("%B %Y")
            ws.append(["Date", "Name", "Yesterday", "Today", "Blockers", "Status"])
        if did_not_submit:
            ws.append([date_str, user_name, "-", "-", "-", "Did not submit"])
        else:
            blockers = answers[2] if answers[2].lower() != "none" else "-"
            ws.append([date_str, user_name, answers[0], answers[1], blockers, "Submitted"])
        wb.save(filepath)

def get_channel_ids():
    channel_names = [c.strip() for c in CHANNEL_NAME.split(",") if c.strip()]
    found_ids = []
    try:
        result = client.conversations_list(types="public_channel,private_channel")
        for ch in result["channels"]:
            if ch["name"] in channel_names:
                found_ids.append(ch["id"])
    except SlackApiError as e:
        print(f"Error getting channels: {e}")
    return found_ids

def post_to_channel(user_name, user_id, answers):
    channel_ids = get_channel_ids()
    if not channel_ids:
        print(f"No channels found for: {CHANNEL_NAME}")
        return
    blockers = answers[2] if answers[2].lower() != "none" else "-"
    for channel_id in channel_ids:
        try:
            client.chat_postMessage(
                channel=channel_id,
                text=f"<@{user_id}> submitted standup *DOHORO-STANDUP* ☕☕☕",
                blocks=[
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"<@{user_id}> submitted standup *DOHORO-STANDUP* ☕☕☕"}
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*What did you complete yesterday?*\n• {answers[0]}"}
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*What will you do today?*\n• {answers[1]}"}
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*Anything blocking your progress?*\n{blockers}"}
                    }
                ]
            )
            print(f"✅ Posted to channel: {channel_id}")
        except SlackApiError as e:
            print(f"Error posting to channel {channel_id}: {e}")

def post_did_not_submit(user_name, user_id):
    channel_ids = get_channel_ids()
    for channel_id in channel_ids:
        try:
            client.chat_postMessage(
                channel=channel_id,
                text=f"⚠️ <@{user_id}> did not submit standup today."
            )
        except SlackApiError as e:
            print(f"Error posting missed standup: {e}")

def get_close_time():
    close_min = STANDUP_MINUTE + STANDUP_WINDOW_MINUTES
    close_hour = STANDUP_HOUR + close_min // 60
    close_min = close_min % 60
    return close_hour, close_min

def is_standup_open():
    now = datetime.now(NPT)
    open_time = now.replace(hour=STANDUP_HOUR, minute=STANDUP_MINUTE, second=0, microsecond=0)
    close_time = open_time + timedelta(minutes=STANDUP_WINDOW_MINUTES)
    return open_time <= now <= close_time

def close_standup():
    close_hour, close_min = get_close_time()
    print(f"Closing standup at {close_hour}:{close_min:02d} NPT")
    with sessions_lock:
        unfinished = list(user_sessions.items())
    for user_id, session in unfinished:
        user_name = session["name"]
        dm_channel = session["channel"]
        try:
            client.chat_postMessage(
                channel=dm_channel,
                text=f"⏰ Standup is now closed ({close_hour}:{close_min:02d} deadline reached). Your response was not recorded. Please submit on time tomorrow!"
            )
        except SlackApiError:
            pass
        post_did_not_submit(user_name, user_id)
        save_to_excel(user_name, [], did_not_submit=True)
        with sessions_lock:
            user_sessions.pop(user_id, None)
    print("Standup closed!")

def send_standup_prompts():
    print(f"Sending standup prompts at {datetime.now(NPT).strftime('%H:%M NPT')}")
    allowed_names = get_allowed_names()
    try:
        result = client.users_list()
        sent_count = 0
        for user in result["members"]:
            if user.get("is_bot") or user.get("deleted") or user.get("is_app_user"):
                continue
            if user["id"] == "USLACKBOT":
                continue
            if allowed_names:
                user_name_check = user.get("real_name", user.get("name", "")).lower()
                if user_name_check not in allowed_names:
                    print(f"Skipping {user.get('real_name')} — not in allowed list")
                    continue
            user_id = user["id"]
            try:
                dm = client.conversations_open(users=user_id)
                dm_channel = dm["channel"]["id"]
                with sessions_lock:
                    user_sessions[user_id] = {
                        "step": 0,
                        "answers": [],
                        "channel": dm_channel,
                        "name": user.get("real_name", user.get("name", "Team member"))
                    }
                client.chat_postMessage(
                    channel=dm_channel,
                    text=QUESTIONS[0]
                )
                sent_count += 1
                print(f"✅ Sent to: {user.get('real_name')}")
            except SlackApiError as e:
                print(f"Error DMing user {user_id}: {e}")
        print(f"Standup sent to {sent_count} members!")
    except SlackApiError as e:
        print(f"Error fetching users: {e}")

@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.json
    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})
    if "event" in data:
        event = data["event"]
        if event.get("type") == "message" and not event.get("bot_id"):
            user_id = event.get("user")
            text = event.get("text", "").strip()
            channel = event.get("channel")
            with sessions_lock:
                session = user_sessions.get(user_id)
            if session and session["channel"] == channel:
                with sessions_lock:
                    session["answers"].append(text)
                    session["step"] += 1
                    current_step = session["step"]
                    answers = list(session["answers"])
                    user_name = session["name"]
                if current_step < len(QUESTIONS):
                    try:
                        client.chat_postMessage(
                            channel=channel,
                            text=QUESTIONS[current_step]
                        )
                    except SlackApiError as e:
                        print(f"Error sending question: {e}")
                else:
                    try:
                        client.chat_postMessage(
                            channel=channel,
                            text="✅ *Thank you! Your standup has been submitted!* 🚀\nHave a productive day! 💪"
                        )
                    except SlackApiError:
                        pass
                    post_to_channel(user_name, user_id, answers)
                    save_to_excel(user_name, answers)
                    with sessions_lock:
                        user_sessions.pop(user_id, None)
    return jsonify({"status": "ok"})

@app.route("/", methods=["GET"])
def home():
    close_hour, close_min = get_close_time()
    allowed_names = get_allowed_names()
    members_info = f"{len(allowed_names)} specific members" if allowed_names else "ALL workspace members"
    return (
        f"Dohoro Standup Bot is running! ☕<br><br>"
        f"Channel: #{CHANNEL_NAME}<br>"
        f"Standup opens: {STANDUP_HOUR}:{STANDUP_MINUTE:02d} NPT<br>"
        f"Standup closes: {close_hour}:{close_min:02d} NPT<br>"
        f"Window: {STANDUP_WINDOW_MINUTES} minutes<br>"
        f"Members: {members_info}<br><br>"
        f"Bot is alive and will never sleep! ✅"
    )

@app.route("/members", methods=["GET"])
def list_members():
    allowed_names = get_allowed_names()
    if not allowed_names:
        return "No specific members set — bot will DM ALL workspace members."
    result = "<b>Allowed standup members:</b><br><br>"
    for i, name in enumerate(allowed_names, 1):
        result += f"{i}. {name}<br>"
    return result

@app.route("/trigger", methods=["GET"])
def trigger():
    thread = threading.Thread(target=send_standup_prompts)
    thread.start()
    return "Standup triggered! Check your Slack DMs 🚀"

@app.route("/close", methods=["GET"])
def manual_close():
    thread = threading.Thread(target=close_standup)
    thread.start()
    return "Standup closed manually!"

def start_scheduler():
    close_hour, close_min = get_close_time()
    scheduler = BackgroundScheduler(timezone=NPT)

    # Send standup at configured time
    scheduler.add_job(
        send_standup_prompts, "cron",
        day_of_week="sun,mon,tue,wed,thu,fri",
        hour=STANDUP_HOUR, minute=STANDUP_MINUTE
    )

    # Close standup after window
    scheduler.add_job(
        close_standup, "cron",
        day_of_week="sun,mon,tue,wed,thu,fri",
        hour=close_hour, minute=close_min
    )

    # Keep alive ping every 5 minutes so bot never sleeps!
    scheduler.add_job(
        keep_alive, "interval", minutes=5
    )

    scheduler.start()
    print(f"✅ Scheduler started!")
    print(f"✅ Standup opens: {STANDUP_HOUR}:{STANDUP_MINUTE:02d} NPT")
    print(f"✅ Standup closes: {close_hour}:{close_min:02d} NPT")
    print(f"✅ Keep alive: every 5 minutes")

# Start scheduler when app loads (works with gunicorn too)
start_scheduler()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
