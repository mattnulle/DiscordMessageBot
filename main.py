import os
import json
import asyncio
import re
import discord
from discord.ext import commands, tasks
from flask import Flask
from threading import Thread
from pathlib import Path
from datetime import datetime, timedelta
import dateparser  # Install this: pip install dateparser

# === DISCORD INTENTS & BOT SETUP ===

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.dm_messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

# === CONFIG ===

# Admin and regular users
ADMIN_USER_IDS = {287387174947520513}
REGULAR_USER_IDS = {1348784300753031269, 768962125615726613}

# Channels to monitor
TARGET_CHANNEL_IDS = {
    1362245135492059290, 1339298329997082624,
    1345189811962642504, 1341556002218315909
}

# Channel to send session reminders to
SESSION_ANNOUNCE_CHANNEL_ID = 1341556002218315909

# File to store scheduled sessions
SESSIONS_FILE = "sessions.json"

# In-memory store for scheduled sessions
# Each item: {'time': datetime, 'channel_id': int}
scheduled_sessions = []


# === FLASK KEEP-ALIVE SERVER ===

app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()


# === PERSISTENCE ===

def load_scheduled_sessions():
    if Path(SESSIONS_FILE).exists():
        with open(SESSIONS_FILE, 'r') as f:
            raw_sessions = json.load(f)
            return [
                {
                    'time': datetime.fromisoformat(item['time']),
                    'channel_id': item['channel_id']
                }
                for item in raw_sessions
            ]
    return []

def save_scheduled_sessions():
    with open(SESSIONS_FILE, 'w') as f:
        json.dump(
            [
                {
                    'time': item['time'].isoformat(),
                    'channel_id': item['channel_id']
                }
                for item in scheduled_sessions
            ],
            f,
            indent=2
        )


# === UTILITIES ===

def parse_session_date(date_text):
    """
    Parses a natural-language date string and returns a datetime object
    """
    try:
        parsed_date = dateparser.parse(date_text)
        if parsed_date:
            return parsed_date
    except Exception as e:
        print(f"Date parsing failed: {e}")
    return None


# === EVENTS ===

@bot.event
async def on_ready():
    global scheduled_sessions
    scheduled_sessions = load_scheduled_sessions()
    print(f'Bot is ready. Logged in as {bot.user}')
    send_alive_message.start()
    check_scheduled_sessions.start()


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Respond to DMs
    if isinstance(message.channel, discord.DMChannel):
        match = re.match(r"^\s*next\s*session\s*:\s*(.+)", message.content, re.IGNORECASE)
        if match:
            date_str = match.group(1).strip()
            session_date = parse_session_date(date_str)
            if session_date:
                scheduled_time = session_date.replace(hour=8, minute=0, second=0, microsecond=0)
                scheduled_sessions.append({
                    'time': scheduled_time,
                    'channel_id': SESSION_ANNOUNCE_CHANNEL_ID
                })
                save_scheduled_sessions()
                await message.channel.send(
                    f"Session scheduled for {scheduled_time.strftime('%Y-%m-%d %H:%M')}"
                )
            else:
                await message.channel.send("Sorry, I couldn't understand the date.")
        else:
            await message.channel.send("I'm alive")
        return

    # Forward messages from target channels
    if message.channel.id in TARGET_CHANNEL_IDS:
        all_user_ids = ADMIN_USER_IDS | REGULAR_USER_IDS
        for user_id in all_user_ids:
            user = await bot.fetch_user(user_id)
            if user:
                try:
                    await user.send(
                        f'New message in #{message.channel.name} by {message.author}:\n{message.content}'
                    )
                except discord.Forbidden:
                    print(f"Cannot DM user {user_id} — DMs may be closed.")

    await bot.process_commands(message)


# === TASKS ===

@tasks.loop(hours=24)
async def send_alive_message():
    for user_id in ADMIN_USER_IDS:
        user = await bot.fetch_user(user_id)
        if user:
            try:
                await user.send("I'm alive")
            except discord.Forbidden:
                print(f"Cannot DM admin user {user_id}")


@tasks.loop(seconds=60)
async def check_scheduled_sessions():
    now = datetime.now()
    to_run = [s for s in scheduled_sessions if s['time'] <= now]

    for session in to_run:
        channel = bot.get_channel(session['channel_id'])
        if channel:
            try:
                await channel.send("You have a session today")
            except Exception as e:
                print(f"Failed to send session message: {e}")

    # Remove run sessions
    if to_run:
        scheduled_sessions[:] = [s for s in scheduled_sessions if s['time'] > now]
        save_scheduled_sessions()


# === STARTUP ===

keep_alive()
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
