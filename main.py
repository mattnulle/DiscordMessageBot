import os
import discord
from discord.ext import commands, tasks

from flask import Flask
from threading import Thread

import asyncio
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.dm_messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Admin and regular users
ADMIN_USER_IDS = {287387174947520513}  # Replace with actual admin IDs
REGULAR_USER_IDS = {1348784300753031269, 768962125615726613}

# Channels to monitor
TARGET_CHANNEL_IDS = {
    1362245135492059290, 1339298329997082624,
    1345189811962642504, 1341556002218315909
}


@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')
    send_alive_message.start()  # Start the midnight task


@bot.event
async def on_message(message):
    # Ignore bot's own messages
    if message.author == bot.user:
        return

    # Respond to DMs
    if isinstance(message.channel, discord.DMChannel):
        await message.channel.send("I'm alive")
        return

    # Forward messages from target channels
    if message.channel.id in TARGET_CHANNEL_IDS:
        all_user_ids = ADMIN_USER_IDS | REGULAR_USER_IDS  # Union of both sets
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


@tasks.loop(hours=24)
async def send_alive_message():
    # Wait until midnight UTC (or adjust time as needed)
    now = datetime.utcnow()
    next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    wait_seconds = (next_midnight - now).total_seconds()
    await asyncio.sleep(wait_seconds)

    for user_id in ADMIN_USER_IDS:
        user = await bot.fetch_user(user_id)
        if user:
            try:
                await user.send("I'm alive")
            except discord.Forbidden:
                print(f"Cannot DM admin user {user_id}")


app = Flask('')


@app.route('/')
def home():
    return "I'm alive!"


def run():
    app.run(host='0.0.0.0', port=8080)


def keep_alive():
    t = Thread(target=run)
    t.start()


keep_alive()
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
