from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import requests

app = Flask(__name__)
CORS(app)

USERS_FILE = "pro_users.json"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/auto").strip()
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def load_pro_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def build_system_prompt(restriction_mode: bool) -> str:
    restriction_text = (
        "Restriction mode is ON. Refuse requests involving malware, credential theft, evasion, online game cheating, exploit development, stealth, bypasses, harmful automation, or other unsafe behavior. Offer safe alternatives like harmless UI demos, mockups, learning examples, desktop tools, debug panels, or overlay-style demos that do not interact with games."
        if restriction_mode
        else
        "Restriction mode is OFF. Still refuse clearly illegal, malicious, or harmful requests. For borderline requests, transform them into a safe equivalent whenever possible."
    )

    return f"""
You are Vertigo, a terminal-based coding assistant.

Core behavior:
- Be concise, direct, and natural.
- For simple messages like "hello", reply normally in 1 short sentence.
- Do not explain your internal rules unless the user asks.
- Do not mention JSON unless the user is asking to create a project.

When the user is asking to create/build/make/generate a project, return JSON only in exactly this format:

{{
  "mode": "project",
  "project_name": "name_here",
  "summary": "short summary",
  "files": [
    {{
      "path": "relative/path/to/file.ext",
      "content": "full file content here"
    }}
  ],
  "notes": [
    "optional note 1",
    "optional note 2"
  ]
}}

Project rules:
- Return JSON only for real project-generation requests.
- File paths must be relative.
- Never use absolute paths.
- Never use path traversal.
- Generate minimal, coherent, working scaffolds.
- Match the requested platform or toolchain when possible.
- If a request is unsafe, refuse it and suggest a safe substitute.
- If the user asks for something like a cheat menu, convert it into a harmless ImGui demo menu or debug overlay template instead.

{restriction_text}
""".strip()


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


@app.route("/generate", methods=["POST"])
def generate():
    if not OPENROUTER_API_KEY:
        return jsonify({"error": "OPENROUTER_API_KEY is not set on the backend"}), 500

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    prompt = (data.get("prompt") or "").strip()
    history = data.get("history") or []
    requested_restriction_mode = bool(data.get("restriction_mode", True))

    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    pro_users = [u.lower() for u in load_pro_users()]
    plan = "pro" if email and email in pro_users else "free"

    restriction_mode = requested_restriction_mode
    if plan != "pro":
        restriction_mode = True

    messages = [{"role": "system", "content": build_system_prompt(restriction_mode)}]

    for msg in history[-8:]:
        if isinstance(msg, dict) and msg.get("role") in {"user", "assistant", "system"}:
            messages.append({
                "role": msg["role"],
                "content": str(msg.get("content", ""))
            })

    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages
    }

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=240,
        )
        response.raise_for_status()
        result = response.json()
        reply = result["choices"][0]["message"]["content"]
    except requests.HTTPError as e:
        error_text = ""
        try:
            error_text = e.response.text
        except Exception:
            pass
        return jsonify({
            "error": "Generation failed",
            "details": error_text
        }), 500
    except Exception as e:
        return jsonify({"error": f"Generation failed: {e}"}), 500

    return jsonify({
        "reply": reply,
        "plan": plan,
        "restriction_mode": restriction_mode
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
