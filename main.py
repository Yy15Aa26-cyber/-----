import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pyrogram import Client, filters
from pyrogram.types import Message
from google import genai

app = FastAPI()

# מאפשר לממשק האפליקציה לתקשר עם השרת בצורה מאובטחת
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# שליפת המפתחות מתוך הגדרות הענן המאובטחות
API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
STORAGE_CHANNEL = int(os.getenv("STORAGE_CHANNEL_ID", "0"))
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")

# חיבור לטלגרם עם תמיכה בקבצים כבדים עד 2GB
tg = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# חיבור למנוע Gemini
ai_client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

@app.on_event("startup")
async def start_bot():
    if BOT_TOKEN and API_ID:
        await tg.start()
        print("Telegram Bot Connected Successfully!")

@app.on_event("shutdown")
async def stop_bot():
    if tg.is_connected:
        await tg.stop()

# בדיקת בריאות לשרת (עבור UptimeRobot שלא יירדם)
@app.get("/health")
def health():
    return {"status": "ok", "message": "Server is alive"}

# מענה פשוט אם מישהו כותב /start ישירות לבוט
@tg.on_message(filters.command("start") & filters.private)
async def welcome(client: Client, message: Message):
    await message.reply_text("שלום! אני הבוט החכם שלך. פתח את האפליקציה כדי לחפש קבצים או לשוחח עם ה-AI.")

# ----------------- נקודות קצה לממשק (Mini-App API) -----------------

class ChatReq(BaseModel):
    message: str

@app.post("/api/chat")
async def chat(req: ChatReq):
    """שיחה עם מנוע הבינה המלאכותית Gemini"""
    if not ai_client:
        raise HTTPException(status_code=500, detail="Gemini key not configured")
    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=req.message
        )
        return {"reply": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search")
async def search_files(q: str):
    """חיפוש קבצים בערוץ האחסון והצגת המשקל שלהם"""
    if not STORAGE_CHANNEL:
        return {"results": []}
    
    results = []
    try:
        async for msg in tg.search_messages(chat_id=STORAGE_CHANNEL, query=q, limit=25):
            media = msg.document or msg.video or msg.audio
            if media:
                size_bytes = media.file_size
                size_mb = round(size_bytes / (1024 * 1024), 2)
                size_text = f"{size_mb} MB" if size_mb < 1000 else f"{round(size_mb / 1024, 2)} GB"
                results.append({
                    "message_id": msg.id,
                    "file_name": getattr(media, "file_name", "קובץ ללא שם"),
                    "size": size_text
                })
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SendReq(BaseModel):
    user_id: int
    message_id: int

@app.post("/api/send-file")
async def send_file(req: SendReq):
    """שליחת הקובץ שנבחר ישירות למשתמש בטלגרם"""
    try:
        await tg.copy_message(
            chat_id=req.user_id,
            from_chat_id=STORAGE_CHANNEL,
            message_id=req.message_id
        )
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
