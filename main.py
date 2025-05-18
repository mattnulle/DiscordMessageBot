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
import dateparser  # pip install dateparser

# === DISCORD INTENTS & BOT SETUP ===

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.dm_messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

# === CONFIG ===

ADMIN_USER_IDS = {287387174947520513}
REGULAR_USER_IDS = {1348784300753031269, 768962125615726613}

TARGET_CHANNEL_IDS = {
    1362245135492059290, 1339298329997082624,
    1345189811962642504, 1341556002218315909
}

DEFAULT_ANNOUNCE_CHANNEL_ID = 1362245135492059290
SESSION_ANNOUNCE_CHANNEL_ID = DEFAULT_ANNOUNCE_CHANNEL_ID
SESSIONS_FILE = "sessions.json"

# In-memory store
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
    global SESSION_ANNOUNCE_CHANNEL_ID
    if Path(SESSIONS_FILE).exists():
        with open(SESSIONS_FILE, 'r') as f:
            data = json.load(f)

        SESSION_ANNOUNCE_CHANNEL_ID = data.get("announce_channel_id", DEFAULT_ANNOUNCE_CHANNEL_ID)
        raw_sessions = data.get("sessions", [])
        return [
            {
                'time': datetime.fromisoformat(item['time']),
                'channel_id': item['channel_id'],
                'added_by': item.get('added_by', 'unknown')
            }
            for item in raw_sessions
        ]
    return []

def save_scheduled_sessions():
    global SESSION_ANNOUNCE_CHANNEL_ID

    data = {
        "announce_channel_id": SESSION_ANNOUNCE_CHANNEL_ID,
        "sessions": [
            {
                'time': item['time'].isoformat(),
                'channel_id': item['channel_id'],
                'added_by': item.get('added_by', 'unknown')
            }
            for item in scheduled_sessions
        ]
    }
    with open(SESSIONS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# === UTILITIES ===

def parse_session_date(date_text):
    try:
        parsed_date = dateparser.parse(date_text)
        if parsed_date and parsed_date > datetime.now():
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
    global SESSION_ANNOUNCE_CHANNEL_ID
    if message.author == bot.user:
        return

    # Respond to DMs
    if isinstance(message.channel, discord.DMChannel):
        content = message.content.strip()

        # Add session
        match = re.match(r"^\s*next\s*session\s*:\s*(.+)", content, re.IGNORECASE)
        if match:
            date_str = match.group(1).strip()
            session_date = parse_session_date(date_str)
            if session_date:
                scheduled_time = session_date.replace(hour=8, minute=0, second=0, microsecond=0)
                scheduled_sessions.append({
                    'time': scheduled_time,
                    'channel_id': SESSION_ANNOUNCE_CHANNEL_ID,
                    'added_by': str(message.author)
                })
                save_scheduled_sessions()
                await message.channel.send(
                    f"Session scheduled for {scheduled_time.strftime('%Y-%m-%d %H:%M')}"
                )
            else:
                await message.channel.send("Sorry, I couldn't understand the date.")
            return

        # List sessions
        elif content.lower() == "list sessions":
            if not scheduled_sessions:
                await message.channel.send("No sessions scheduled.")
            else:
                msg = "\n".join(
                    f"- {s['time'].strftime('%Y-%m-%d %H:%M')} by {s.get('added_by', 'unknown')} in <#{s['channel_id']}>"
                    for s in sorted(scheduled_sessions, key=lambda s: s['time'])
                )
                await message.channel.send(f"Scheduled sessions:\n{msg}")
            return

        # Cancel session
        elif content.lower().startswith("cancel session"):
            match = re.match(r"cancel session\s+(\d{4}-\d{2}-\d{2})", content, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                try:
                    cancel_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    before_count = len(scheduled_sessions)
                    scheduled_sessions[:] = [
                        s for s in scheduled_sessions
                        if s['time'].date() != cancel_date
                    ]
                    removed = before_count - len(scheduled_sessions)
                    save_scheduled_sessions()
                    await message.channel.send(
                        f"Cancelled {removed} session(s) on {cancel_date.strftime('%Y-%m-%d')}."
                        if removed else f"No sessions found on {cancel_date.strftime('%Y-%m-%d')}."
                    )
                except ValueError:
                    await message.channel.send("Invalid date format. Use YYYY-MM-DD.")
            else:
                await message.channel.send("Usage: `cancel session <YYYY-MM-DD>`")
            return

        # Change announcement channel
        elif content.lower().startswith("set announce channel"):
            if message.author.id not in ADMIN_USER_IDS:
                await message.channel.send("You don't have permission to do that.")
                return

            match = re.match(r"set announce channel\s+(\d+)", content, re.IGNORECASE)
            if match:
                new_channel_id = int(match.group(1))
                channel = bot.get_channel(new_channel_id)
                if channel:
                    SESSION_ANNOUNCE_CHANNEL_ID = new_channel_id
                    save_scheduled_sessions()
                    await message.channel.send(
                        f"Announcement channel updated to <#{new_channel_id}>"
                    )
                else:
                    await message.channel.send("Invalid channel ID or I can't access that channel.")
            else:
                await message.channel.send("Usage: `set announce channel <channel_id>`")
            return

        # Help / usage info
        elif content.lower() in {"help", "usage"}:
            help_text = (
                "**Bot Commands:**\n"
                "`next session: <date>` – Schedule a session at 8AM on the given date.\n"
                "`list sessions` – Show all upcoming scheduled sessions.\n"
                "`cancel session <YYYY-MM-DD>` – Cancel any session scheduled on that date.\n"
                "`set announce channel <channel_id>` – Set the channel for session reminders (admin only).\n"
                "`help` or `usage` – Show this message.\n"
                "`any other message` – Bot replies with 'I'm alive'."
            )
            await message.channel.send(help_text)
            return

        # Default DM response
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
            added_by = session.get('added_by', 'unknown user')
            try:
                await channel.send(f"You have a session today (added by {added_by})")
            except Exception as e:
                print(f"Failed to send session message: {e}")

    if to_run:
        scheduled_sessions[:] = [s for s in scheduled_sessions if s['time'] > now]
        save_scheduled_sessions()

# === STARTUP ===

keep_alive()
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
