from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
import asyncio
import os
import pymongo

# Initialize your Pyrogram Client session with the provided API information and bot token
app = Client("video_compressor_bot", api_id=YOUR_API_ID, api_hash="YOUR_API_HASH", bot_token="YOUR_BOT_TOKEN")

# Initialize MongoDB client and connect to your MongoDB database
mongo_client = pymongo.MongoClient("mongodb://your_mongodb_uri")
db = mongo_client["video_compressor_bot"]
collection = db["users"]

# Define the owner's user ID
owner_id = YOUR_OWNER_USER_ID

# Function to send inline keyboard with start, help, and about commands
def send_start_keyboard(chat_id):
    keyboard = [
        [InlineKeyboardButton("Start", callback_data="start")],
        [InlineKeyboardButton("Help", callback_data="help"), InlineKeyboardButton("About", callback_data="about")],
        [InlineKeyboardButton("Bot Status", callback_data="status")],
        [InlineKeyboardButton("Total Users", callback_data="total_users")]
    ]
    
    # Only add the Broadcast Message button for the owner
    if chat_id == owner_id:
        keyboard.append([InlineKeyboardButton("Broadcast Message", callback_data="broadcast")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    app.send_message(chat_id, "Select an option:", reply_markup=reply_markup)

# Function to start the bot and display format options
@app.on_message(filters.command("start"))
async def start_command(_, message):
    user_id = message.chat.id
    user_data[user_id] = {}
    
    send_start_keyboard(user_id)

# Function to handle button clicks
@app.on_callback_query(filters.regex(r'^start$|^help$|^about$|^status$|^total_users$|^broadcast$'))
async def button_click(_, callback_query: CallbackQuery):
    user_id = callback_query.message.chat.id
    command = callback_query.data
    
    if command == "start":
        user_data[user_id] = {}
    elif command == "help":
        await callback_query.message.reply_text(
            "This bot allows you to compress videos. Start by selecting a format with the /start command, then send a video to compress."
            "\nUse /format to select advanced options like custom bitrate, codec, and resolution."
        )
        return
    elif command == "about":
        await callback_query.message.reply_text(
            "This bot was created to demonstrate video compression. If you have any questions or need assistance, feel free to ask!"
        )
        return
    elif command == "status":
        # Send bot status information
        status_message = "Bot is running normally."
        await callback_query.message.reply_text(status_message)
        return
    elif command == "total_users":
        # Get the total number of users from the database
        total_users = collection.count_documents({})
        await callback_query.message.reply_text(f"Total Users: {total_users}")
        return
    elif command == "broadcast":
        if user_id == owner_id:
            await callback_query.message.reply_text("Enter the message you want to broadcast:")
            user_data[user_id]["broadcast"] = True
        else:
            await callback_query.message.reply_text("Only the bot owner can use this feature.")
        return
    
    await callback_query.message.reply_text("Welcome to the Video Compressor Bot! Select a format to compress your video:")
    send_start_keyboard(user_id)

# Function to simulate a progress bar
async def send_progress(user_id, progress):
    await app.send_chat_action(user_id, "typing")
    await asyncio.sleep(1)  # Simulate typing action
    await app.send_message(user_id, f"Compression Progress: {progress}%")

# Function to compress video
@app.on_message(filters.video)
async def compress_video(_, message):
    user_id = message.chat.id
    # Automatically select a format based on video resolution
    selected_format = auto_select_format(message)
    
    if selected_format:
        await message.download(file_name='input_video.mp4')
        
        async def compress():
            output_format = formats[selected_format]
            process = await asyncio.create_subprocess_exec(
                'ffmpeg', '-i', 'input_video.mp4', *output_format,
                'output_video.mp4', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            while True:
                await asyncio.sleep(1)
                if process.returncode is not None:
                    break
                output = (await process.stderr.read()).decode().strip()
                if "time=" in output:
                    try:
                        progress_time = output.split("time=")[1].split()[0]
                        total_time = output.split("time=")[2].split()[0]
                        progress_percent = int((float(progress_time) / float(total_time)) * 100)
                        await send_progress(user_id, progress_percent)
                    except:
                        pass
            
            await app.send_video(user_id, open('output_video.mp4', 'rb'))
            
            # Upload the compressed video to the chat
            await app.send_video(user_id, 'output_video.mp4', duration=message.video.duration, width=message.video.width, height=message.video.height)
            
            # Upload the compressed video to the specified
