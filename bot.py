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

# Initialize MongoDB client and database
mongo_client = pymongo.MongoClient("mongodb+srv://mrshokrullah:L7yjtsOjHzGBhaSR@cluster0.aqxyz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = mongo_client["shah"]
users_collection = db["shm"]

# Helper function: Register users
def register_user(user_id):
    if not users_collection.find_one({"user_id": user_id}):
        users_collection.insert_one({"user_id": user_id, "banned": False})
        logger.info(f"New user registered: {user_id}")

# Define a function to create the main menu inline keyboard
def create_main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Start", callback_data="start"),
                InlineKeyboardButton("Help", callback_data="help"),
                InlineKeyboardButton("About", callback_data="about"),
            ],
        ]
    )
    return keyboard

# Define a function to create the video format selection inline keyboard
def create_format_selection_keyboard():
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("1080p", callback_data="1080p"),
                InlineKeyboardButton("720p", callback_data="720p"),
                InlineKeyboardButton("480p", callback_data="480p"),
            ],
            [
                InlineKeyboardButton("360p", callback_data="360p"),
                InlineKeyboardButton("240p", callback_data="240p"),
            ],
            [
                InlineKeyboardButton("Back to Main Menu", callback_data="main_menu"),
            ],
        ]
    )
    return keyboard

# Command: /start
@app.on_message(filters.command("start"))
def start_command(client, message):
    user_id = message.from_user.id
    register_user(user_id)
    keyboard = create_main_menu_keyboard()
    message.reply_text("Welcome to the Video Compressor Bot! Send me a video to compress.", reply_markup=keyboard)

# Command: /help
@app.on_message(filters.command("help"))
def help_command(client, message):
    user_id = message.from_user.id
    register_user(user_id)
    help_text = (
        "Here are the available commands:\n\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/about - Learn more about the bot\n"
        "/broadcast - Send a broadcast message\n"
        "/total_users - Show the total number of users\n"
        "/ban - Ban a user\n"
        "/unban - Unban a user\n"
    )
    keyboard = create_main_menu_keyboard()
    message.reply_text(help_text, reply_markup=keyboard)

# Command: /about
@app.on_message(filters.command("about"))
def about_command(client, message):
    user_id = message.from_user.id
    register_user(user_id)
    keyboard = create_main_menu_keyboard()
    message.reply_text("This bot compresses videos using FFmpeg. Developed by Your Name.", reply_markup=keyboard)

# Command: /broadcast (admin-only)
@app.on_message(filters.command("broadcast") & filters.user("YOUR_USER_ID"))
def broadcast_command(client, message):
    message.reply_text("Send me the message to broadcast:")
    app.listen_for_message(message.chat.id, process_broadcast)

def process_broadcast(client, message):
    text = message.text
    for user in users_collection.find({"banned": False}):
        try:
            app.send_message(user["user_id"], text)
        except Exception as e:
            logger.error(f"Failed to send broadcast to {user['user_id']}: {e}")
    message.reply_text("Broadcast sent.")

# Command: /total_users (admin-only)
@app.on_message(filters.command("total_users") & filters.user("YOUR_USER_ID"))
def total_users_command(client, message):
    total_users = users_collection.count_documents({})
    message.reply_text(f"Total users: {total_users}")

# Command: /ban (admin-only)
@app.on_message(filters.command("ban") & filters.user("YOUR_USER_ID"))
def ban_user(client, message):
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        users_collection.update_one({"user_id": user_id}, {"$set": {"banned": True}})
        message.reply_text(f"User {user_id} has been banned.")

# Command: /unban (admin-only)
@app.on_message(filters.command("unban") & filters.user("YOUR_USER_ID"))
def unban_user(client, message):
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        users_collection.update_one({"user_id": user_id}, {"$set": {"banned": False}})
        message.reply_text(f"User {user_id} has been unbanned.")

# Video handling
@app.on_message(filters.video)
def handle_video(client, message):
    user_id = message.from_user.id
    user_data = users_collection.find_one({"user_id": user_id})
    
    if user_data.get("banned", False):
        message.reply_text("You are banned from using this bot.")
        return

    # Video download
    video = message.video
    file_path = app.download_media(video)
    output_path = f"compressed_{video.file_name}"
    
    # Compress video
    try:
        subprocess.run(
            ["ffmpeg", "-i", file_path, "-vcodec", "libx264", "-crf", "28", output_path],
            check=True,
        )
        app.send_document(message.chat.id, output_path)
        os.remove(output_path)
    except Exception as e:
        message.reply_text("Failed to process the video.")
        logger.error(f"FFmpeg error: {e}")

# Button handling
@app.on_callback_query()
def button_callback(client, query: CallbackQuery):
    data = query.data
    if data == "start":
        query.message.reply_text("Welcome back! Send me a video to compress.")

# Run the bot
if __name__ == "__main__":
    app.run()
