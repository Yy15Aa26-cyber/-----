import os
import json
import httpx
from http.server import BaseHTTPRequestHandler
from google import genai

GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

ai_client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "live", "message": "Bot API is running!"}).encode())

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            body = json.loads(post_data.decode())
        except:
            body = {}

        # אם זו פנייה מהצ'אט של ה-AI
        if self.path == '/api/chat':
            user_msg = body.get("message", "")
            try:
                response = ai_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=user_msg
                )
                reply = response.text
            except Exception as e:
                reply = f"שגיאה ב-AI: {str(e)}"

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"reply": reply}).encode())
            return

        # ברירת מחדל
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(b"OK")
