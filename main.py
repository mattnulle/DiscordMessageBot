import os
import discord
from discord.ext import commands

from flask import Flask
from threading import Thread

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True  # Required to read message content

bot = commands.Bot(command_prefix='!', intents=intents)

# Replace with the actual user ID you want to DM
TARGET_USER_ID = 287387174947520513

# Replace with the channel IDs you want to monitor
TARGET_CHANNEL_IDS = {
    1362245135492059290, 1339298329997082624, 1345189811962642504,
    1341556002218315909
}


@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')


@bot.event
async def on_message(message):
    # Ignore bot's own messages
    if message.author == bot.user:
        return

    # Only respond to messages in the target channels
    if message.channel.id in TARGET_CHANNEL_IDS:
        target_user = await bot.fetch_user(TARGET_USER_ID)
        if target_user:
            await target_user.send(
                f'New message in #{message.channel.name} by {message.author}:\n{message.content}'
            )

    await bot.process_commands(message)  # Ensures other commands still work


app = Flask('')


@app.route('/')
def home():
    return "I'm alive!"


def run():
    app.run(host='0.0.0.0', port=8080)


def keep_alive():
    t = Thread(target=run)
    t.start()


# Call keep_alive() before bot.run()
keep_alive()

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
