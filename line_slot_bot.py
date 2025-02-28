from flask import Flask, request
import sqlite3
import os
import random
from datetime import datetime
import requests

app = Flask(__name__)

LINE_ACCESS_TOKEN = "zzFBMOrSDsv4jK5t0U/zue1wNuZoYM2ksoXkU30XVKf+mBpQ3HVomJBvtIkYjWcJDrujEDeLBbjfjgwFa/8ayYNGcj7W99EBUgoJOCjieCUq4UtZccfaxAE/9j7X98Xjo1xyVgEKj6ojahz+RumyMwdB04t89/1O/w1cDnyilFU="
LINE_API_URL = "https://api.line.me/v2/bot/message/reply"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
}

ADMIN_IDS = ["U9a952e1e4e8580107b52b5f5fd4f0ab3", "管理者のLINEユーザーID2"]

def init_db():
    conn = sqlite3.connect("ncoin.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            ncoin INTEGER DEFAULT 20
        )
    """)
    conn.commit()
    conn.close()

init_db()

def is_admin(user_id):
    return user_id in ADMIN_IDS

@app.route("/callback", methods=["POST"])
def callback():
    req = request.json
    events = req.get("events", [])
    
    for event in events:
        if event.get("type") == "message" and event["message"]["type"] == "text":
            user_id = event["source"]["userId"]
            reply_token = event["replyToken"]
            text = event["message"]["text"].strip()
            
            if text == "絵スロット":
                message = slot_game(user_id, "emoji")
            elif text == "スロット":
                message = slot_game(user_id, "number")
            elif text == "コイン":
                message = get_balance(user_id)
            elif text == "check":
                message = user_id
            elif text.startswith("付与:") and is_admin(user_id):
                message = modify_ncoin(text, "add")
            elif text.startswith("削除:") and is_admin(user_id):
                message = modify_ncoin(text, "remove")
            elif text.startswith("All付与:") and is_admin(user_id):
                message = modify_all_ncoin(text, "add")
            elif text.startswith("All削除:") and is_admin(user_id):
                message = modify_all_ncoin(text, "remove")
            else:
                message = "無効なコマンドです。"
            
            send_line_message(reply_token, message)
    
    return "OK"

def slot_game(user_id, mode):
    conn = sqlite3.connect("ncoin.db")
    c = conn.cursor()
    c.execute("SELECT ncoin FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    
    if not row:
        c.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        ncoin = 20
    else:
        ncoin = row[0]
    
    if ncoin < 1:
        return "Nコインが不足しています。管理者に付与を依頼してください。"
    
    ncoin -= 1
    
    if mode == "emoji":
        result = random.choices(["🍒", "🍋", "🔔", "⭐"], k=3)
        payout = 10 if len(set(result)) == 1 else 0
    else:
        result = [str(random.randint(1, 9)) * 3 for _ in range(3)]
        payout = 100 if result[0] in ["111", "222", "333", "444", "555", "666", "888", "999"] else 0
        payout = 777 if result[0] == "777" else payout
    
    ncoin += payout
    c.execute("UPDATE users SET ncoin = ? WHERE user_id = ?", (ncoin, user_id))
    conn.commit()
    conn.close()
    
    message = f"{' '.join(result)}\n現在のNコイン: {ncoin}"
    if payout > 0:
        message = f"おめでとうございます！！{payout}Nコインの当たりです\nあなたの残りは{ncoin}Nコインです。"
    
    return message

def get_balance(user_id):
    conn = sqlite3.connect("ncoin.db")
    c = conn.cursor()
    c.execute("SELECT ncoin FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return f"あなたのNコイン残高: {row[0] if row else 20}Nコイン"

def modify_ncoin(text, action):
    _, user_id, amount = text.split(":")
    amount = int(amount)
    conn = sqlite3.connect("ncoin.db")
    c = conn.cursor()
    c.execute("SELECT ncoin FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    ncoin = row[0] if row else 20
    
    ncoin = ncoin + amount if action == "add" else max(0, ncoin - amount)
    c.execute("INSERT INTO users (user_id, ncoin) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET ncoin = ?", (user_id, ncoin, ncoin))
    conn.commit()
    conn.close()
    
    return f"{user_id}に{amount}Nコイン{'付与' if action == 'add' else '削除'}しました。"

def modify_all_ncoin(text, action):
    _, amount = text.split(":")
    amount = int(amount)
    conn = sqlite3.connect("ncoin.db")
    c = conn.cursor()
    if action == "add":
        c.execute("UPDATE users SET ncoin = ncoin + ?", (amount,))
    elif action == "remove":
        c.execute("UPDATE users SET ncoin = 0")
    conn.commit()
    conn.close()
    return f"全ユーザーのNコインを{'付与' if action == 'add' else '削除'}しました。"

def send_line_message(reply_token, message):
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": message}]
    }
    requests.post(LINE_API_URL, headers=HEADERS, json=payload)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
