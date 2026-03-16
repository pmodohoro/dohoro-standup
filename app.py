import os
import json
import threading
from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import openpyxl
from openpyxl import load_workbook
import pytz

app = Flask(__name__)
client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

CHANNEL_NAME = "wpx--todos"
NPT = pytz.timezone("Asia/Kathmandu")

user_sessions = {}

QUESTIONS = [
    "👋 Good morning! Time for your daily standup!\n\n*Question 1:* ✅ What did you complete yesterday?",
    "*Question 2:* 🔨 What will you work on today?",
    "*Question 3:* 🚧 Anything blocking your progress? (Type 'none' if nothing)"
]

def get_excel_filename():
    now = datetime.now(NPT)
    return f"standup_{now.strftime('%B-%Y')}.xlsx"

def save_to_excel(user_name, answers):
    filename = get_excel_filename()
    filepath = f"/tmp/{filename}"
    now = datetime.now(NPT)
    date_str = now.strftime("%Y-%m-%d")
    
    try:
        wb = load_workbook(filepath)
        ws = wb.active
    except FileNotFoundError:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = now.strftime("%B %Y")
        ws.append(["Date", "Name", "Yesterday", "Today", "Blockers"])
    
    ws.append([date_str, user_name, answers[0], answers[1], answers[2]])
    wb.save(filepath)

def post_to_channel(user_name, user_id, answers):
    try:
        channels = client.conversations_list(types="public_channel,private_channel")
        channel_id = None
        for ch in channels["channels"]:
            if ch["name"] == CHANNEL_NAME:
                channel_id = ch["id"]
                break
        
        if not channel_id:
            return

        blockers = answers[2] if answers[2].lower() != "none" else "-"
        
        client.chat_postMessage(
            channel=channel_id,
            text=f"<@{user_id}> submitted standup *DOHORO-STANDUP* ☕☕☕",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"<@{user_id}> submitted standup *DOHORO-STANDUP* ☕☕☕"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*What did you complete yesterday?*\n• {answers[0]}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*What will you do today?*\n• {answers[1]}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Anything blocking your progress?*\n{blockers}"
                    }
                }
            ]
        )
    except SlackApiError as e:
        print(f"Error posting to channel: {e}")

def send_standup_prompts():
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
            
            if user_id in user_sessions:
                session = user_sessions[user_id]
                
                if session["channel"] == channel:
                    session["answers"].append(text)
                    session["step"] += 1
                    
                    if session["step"] < len(QUESTIONS):
                        client.chat_postMessage(
                            channel=channel,
                            text=QUESTIONS[session["step"]]
                        )
                    else:
                        client.chat_postMessage(
                            channel=channel,
                            text="✅ Thank you! Your standup has been submitted to #drive_new. Have a great day! 🚀"
                        )
                        
                        user_name = session["name"]
                        answers = session["answers"]
                        post_to_channel(user_name, user_id, answers)
                        save_to_excel(user_name, answers)
                        del user_sessions[user_id]
    
    return jsonify({"status": "ok"})

@app.route("/", methods=["GET"])
def home():
    return "Dohoro Standup Bot is running! ☕"

@app.route("/trigger", methods=["GET"])
def trigger():
    thread = threading.Thread(target=send_standup_prompts)
    thread.start()
    return "Standup triggered!"

def start_scheduler():
    scheduler = BackgroundScheduler(timezone=NPT)
    scheduler.add_job(
        send_standup_prompts,
        "cron",
        day_of_week="sun,mon,tue,wed,thu,fri",
        hour=7,
        minute=20
    )
    scheduler.start()

if __name__ == "__main__":
    start_scheduler()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
