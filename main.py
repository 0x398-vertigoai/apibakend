from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)

USERS_FILE = "pro_users.json"

def load_pro_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

@app.route("/")
def home():
    return "Vertigo backend is running."

@app.route("/check-email", methods=["POST"])
def check_email():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    if not email:
        return jsonify({"error": "Email is required"}), 400

    pro_users = [u.lower() for u in load_pro_users()]
    plan = "pro" if email in pro_users else "free"

    return jsonify({
        "email": email,
        "plan": plan
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
