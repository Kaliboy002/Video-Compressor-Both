from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import subprocess
import os
import pymongo
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Replace with your API credentials
api_id = '15787995'
api_hash = 'e51a3154d2e0c45e5ed70251d68382de'
bot_token = '7628087790:AAFADZ1UQ1II7ECu2zwnctkbCbziDKW0QsA'

# Initialize the Pyrogram client
app = Client("video_compressor_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# MongoDB setup
mongo_client = pymongo.MongoClient("mongodb+srv://mrshokrullah:L7yjtsOjHzGBhaSR@cluster0.aqxyz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = mongo_client["shah"]
users_collection = db["users"]

# Ensure FFmpeg is installed
def ensure_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info("FFmpeg is already installed.")
    except FileNotFoundError:
        logger.info("FFmpeg not found. Installing...")
        subprocess.run(["apt-get", "update"], check=True)
        subprocess.run(["apt-get", "install", "-y", "ffmpeg"], check=True)
        logger.info("FFmpeg installed successfully.")

ensure_ffmpeg()

# Helper function: Register users
def register_user(user_id):
    if not users_collection.find_one({"user_id": user_id}):
        users_collection.insert_one({"user_id": user_id, "banned": False})
        logger.info(f"New user registered: {user_id}")

# Create main menu keyboard
def create_main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Help", callback_data="help"), InlineKeyboardButton("About", callback_data="about")],
        [InlineKeyboardButton("Compress Video", callback_data="compress")]
    ])

# Handle /start command
@app.on_message(filters.command("start"))
def start_command(client, message):
    user_id = message.from_user.id
    register_user(user_id)
    keyboard = create_main_menu_keyboard()
    message.reply_text("Welcome to the Video Compressor Bot! Send me a video to compress.", reply_markup=keyboard)

# Handle /help command
@app.on_message(filters.command("help"))
def help_command(client, message):
    user_id = message.from_user.id
    register_user(user_id)
    help_text = (
        "Available commands:\n"
        "/start - Start the bot\n"
        "/help - Show help\n"
        "/about - About this bot\n"
        "/total_users - Admin-only: Count total users\n"
        "/ban - Admin-only: Ban a user\n"
        "/unban - Admin-only: Unban a user\n"
    )
    message.reply_text(help_text)

# Handle /about command
@app.on_message(filters.command("about"))
def about_command(client, message):
    message.reply_text("This bot compresses videos using FFmpeg. Developed with ❤️.")

# Admin command: /total_users
@app.on_message(filters.command("total_users") & filters.user("YOUR_USER_ID"))
def total_users_command(client, message):
    total_users = users_collection.count_documents({})
    message.reply_text(f"Total registered users: {total_users}")

# Admin command: /ban
@app.on_message(filters.command("ban") & filters.user("YOUR_USER_ID"))
def ban_user(client, message):
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        users_collection.update_one({"user_id": user_id}, {"$set": {"banned": True}})
        message.reply_text(f"User {user_id} has been banned.")

# Admin command: /unban
@app.on_message(filters.command("unban") & filters.user("YOUR_USER_ID"))
def unban_user(client, message):
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        users_collection.update_one({"user_id": user_id}, {"$set": {"banned": False}})
        message.reply_text(f"User {user_id} has been unbanned.")

# Handle video messages
@app.on_message(filters.video)
def handle_video(client, message):
    user_id = message.from_user.id
    user_data = users_collection.find_one({"user_id": user_id})
    if user_data.get("banned"):
        message.reply_text("You are banned from using this bot.")
        return

    # Download video
    video = message.video
    input_path = app.download_media(video)
    output_path = f"compressed_{video.file_name}"

    # Compress video
    try:
        subprocess.run(
            ["ffmpeg", "-i", input_path, "-vcodec", "libx264", "-crf", "28", output_path],
            check=True
        )
        app.send_document(message.chat.id, output_path)
        os.remove(input_path)
        os.remove(output_path)
    except Exception as e:
        logger.error(f"Error compressing video: {e}")
        message.reply_text("Failed to process the video.")

# Handle inline button actions
@app.on_callback_query()
def callback_query_handler(client, query: CallbackQuery):
    if query.data == "help":
        query.message.reply_text("Send me a video, and I'll compress it for you.")
    elif query.data == "about":
        query.message.reply_text("Video Compressor Bot using FFmpeg.")
    elif query.data == "compress":
        query.message.reply_text("Send me a video to start compression.")

# Run the bot
if __name__ == "__main__":
    app.run()
