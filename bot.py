from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import subprocess
import os
import pymongo

# Replace with your API credentials
api_id = '15787995' 
api_hash = 'e51a3154d2e0c45e5ed70251d68382de'
bot_token = '7628087790:AAFADZ1UQ1II7ECu2zwnctkbCbziDKW0QsA'

# Initialize the Pyrogram client
app = Client("video_compressor_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Initialize MongoDB client and database
mongo_client = pymongo.MongoClient("mongodb+srv://mrshokrullah:L7yjtsOjHzGBhaSR@cluster0.aqxyz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = mongo_client["shah"]

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

# Define the /start command
@app.on_message(filters.command("start"))
def start_command(client, message):
    keyboard = create_main_menu_keyboard()
    message.reply_text("Welcome to the Video Compressor Bot! Send me a video to compress.", reply_markup=keyboard)

# Define the /help command
@app.on_message(filters.command("help"))
def help_command(client, message):
    keyboard = create_main_menu_keyboard()
    help_text = "Here are the available commands:\n\n"
    help_text += "/start - Start the bot\n"
    help_text += "/help - Show this help message\n"
    help_text += "/about - Learn more about the bot\n"
    help_text += "/broadcast - Send a broadcast message\n"
    help_text += "/total_users - Show the total number of users\n"
    help_text += "/ban - Ban a user\n"
    help_text += "/unban - Unban a user\n"
    message.reply_text(help_text, reply_markup=keyboard)

# Define the /about command
@app.on_message(filters.command("about"))
def about_command(client, message):
    keyboard = create_main_menu_keyboard()
    message.reply_text("This bot was created to compress videos using FFmpeg with x264 codec. Developed by Your Name.", reply_markup=keyboard)

# Define the /broadcast command
@app.on_message(filters.command("broadcast") & filters.user("YOUR_USER_ID"))
def broadcast_command(client, message):
    keyboard = create_main_menu_keyboard()
    message.reply_text("Enter the broadcast message you want to send to all users:")
    client.register_next_step_handler(message, broadcast_message, keyboard)

# Function to handle broadcast message input
def broadcast_message(client, message, keyboard):
    text = message.text
    user_collection = db["users"]
    for user_doc in user_collection.find():
        try:
            chat_id = user_doc["chat_id"]
            client.send_message(chat_id, text, reply_markup=keyboard)
        except Exception as e:
            print(f"Error sending broadcast: {str(e)}")
    message.reply_text("Broadcast sent successfully!")

# Define the /total_users command
@app.on_message(filters.command("total_users") & filters.user("YOUR_USER_ID"))
def total_users_command(client, message):
    user_collection = db["users"]
    total_users = user_collection.count_documents({})
    message.reply_text(f"Total number of users: {total_users}")

# Define the /ban command
@app.on_message(filters.command("ban") & filters.user("YOUR_USER_ID"))
def ban_command(client, message):
    user_id_to_ban = None
    if message.reply_to_message:
        user_id_to_ban = message.reply_to_message.from_user.id
    elif len(message.command) > 1:
        try:
            user_id_to_ban = int(message.command[1])
        except ValueError:
            pass
    
    if user_id_to_ban:
        user_collection = db["users"]
        user_collection.update_one({"user_id": user_id_to_ban}, {"$set": {"banned": True}})
        message.reply_text(f"User {user_id_to_ban} has been banned.")
    else:
        message.reply_text("Please reply to a user's message or provide a valid user ID to ban.")

# Define the /unban command
@app.on_message(filters.command("unban") & filters.user("YOUR_USER_ID"))
def unban_command(client, message):
    user_id_to_unban = None
    if message.reply_to_message:
        user_id_to_unban = message.reply_to_message.from_user.id
    elif len(message.command) > 1:
        try:
            user_id_to_unban = int(message.command[1])
        except ValueError:
            pass
    
    if user_id_to_unban:
        user_collection = db["users"]
        user_collection.update_one({"user_id": user_id_to_unban}, {"$set": {"banned": False}})
        message.reply_text(f"User {user_id_to_unban} has been unbanned.")
    else:
        message.reply_text("Please reply to a user's message or provide a valid user ID to unban.")

# Define a function to handle video messages
@app.on_message(filters.video)
def handle_video(client, message):
    chat_id = message.chat.id
    video_file = message.video.file_id
    download_path = f"downloads/{video_file}.mp4"
    
    # Get the resolution of the video
    resolution = f"{message.video.width}x{message.video.height}"
    
    # Determine the format based on resolution
    if "1920x1080" in resolution:
        selected_format = "1080p"
    elif "1280x720" in resolution:
        selected_format = "720p"
    elif "854x480" in resolution:
        selected_format = "480p"
    elif "640x360" in resolution:
        selected_format = "360p"
    elif "426x240" in resolution:
        selected_format = "240p"
    else:
        selected_format = "unknown"
    
    # Compose the output file name based on the resolution
    output_file = f"downloads/compressed_{selected_format}_{video_file}.mp4"
    
    if selected_format == "unknown":
        message.reply_text("Unsupported resolution. Please choose a format manually.")
    else:
        # Compress the video using FFmpeg with x264 codec and the detected resolution
        ffmpeg_command = (
            f"ffmpeg -i {download_path} -c:v libx264 -vf 'scale={resolution}' {output_file}"
        )
        subprocess.run(ffmpeg_command, shell=True)
        
        # Send the compressed video back to the user as a file
        client.send_document(chat_id, output_file, reply_to_message_id=message.message_id)

# Define a function to handle button presses
@app.on_callback_query()
def button_callback(client, query: CallbackQuery):
    chat_id = query.message.chat.id
    message_id = query.message.message_id
    data = query.data
    
    if data == "start":
        keyboard = create_main_menu_keyboard()
        app.edit_message_text(chat_id, message_id, "Welcome to the Video Compressor Bot! Send me a video to compress.", reply_markup=keyboard)

# Run the bot
app.run()
