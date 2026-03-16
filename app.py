import os
import threading
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

QUESTIONS = [
    "👋 Good morning! Time for your daily standup!\n\n*Question 1 of 3:* ✅ What did you complete yesterday?",
    "*Question 2 of 3:* 🔨 What will you work on today?",
    "*Question 3 of 3:* 🚧 Anything blocking your progress? (Type 'none' if nothing)"
]

user_sessions = {}
sessions_lock = threading.Lock()
excel_lock = threading.Lock()

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

def get_channel_id():
    try:
        result = client.conversations_list(types="public_channel,private_channel")
        for ch in result["channels"]:
            if ch["name"] == CHANNEL_NAME:
                return ch["id"]
    except SlackApiError as e:
        print(f"Error getting channel: {e}")
    return None

def post_to_channel(user_name, user_id, answers):
    try:
        channel_id = get_channel_id()
        if not channel_id:
            print(f"Channel #{CHANNEL_NAME} not found!")
            return
        blockers = answers[2] if answers[2].lower() != "none" else "-"
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
    except SlackApiError as e:
        print(f"Error posting to channel: {e}")

def post_did_not_submit(user_name, user_id):
    try:
        channel_id = get_channel_id()
        if not channel_id:
            return
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
                text=f"⏰ Standup is now closed ({close_hour}:{close_min:02d}am deadline reached). Your response was not recorded. Please submit on time tomorrow!"
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
    try:
        result = client.users_list()
        for user in result["members"]:
            if user.get("is_bot") or user.get("deleted") or user.get("is_app_user"):
                continue
            if user["id"] == "USLACKBOT":
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
            except SlackApiError as e:
                print(f"Error DMing user {user_id}: {e}")
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
                if not is_standup_open():
                    try:
                        client.chat_postMessage(
                            channel=channel,
                            text="⏰ Sorry, the standup window is now closed. Please submit on time tomorrow!"
                        )
                    except SlackApiError:
                        pass
                    return jsonify({"status": "ok"})
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
    return (
        f"Dohoro Standup Bot is running! ☕<br><br>"
        f"Channel: #{CHANNEL_NAME}<br>"
        f"Standup opens: {STANDUP_HOUR}:{STANDUP_MINUTE:02d}am NPT<br>"
        f"Standup closes: {close_hour}:{close_min:02d}am NPT<br>"
        f"Window: {STANDUP_WINDOW_MINUTES} minutes"
    )

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
    scheduler.add_job(
        send_standup_prompts, "cron",
        day_of_week="sun,mon,tue,wed,thu,fri",
        hour=STANDUP_HOUR, minute=STANDUP_MINUTE
    )
    scheduler.add_job(
        close_standup, "cron",
        day_of_week="sun,mon,tue,wed,thu,fri",
        hour=close_hour, minute=close_min
    )
    scheduler.start()
    print(f"✅ Scheduler started! Opens: {STANDUP_HOUR}:{STANDUP_MINUTE:02d}, Closes: {close_hour}:{close_min:02d} NPT")

if __name__ == "__main__":
    start_scheduler()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
