import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True  # Required to read message content

bot = commands.Bot(command_prefix='!', intents=intents)

# Replace with the actual user ID you want to DM
TARGET_USER_ID = 123456789012345678  

# Replace with the channel IDs you want to monitor
TARGET_CHANNEL_IDS = {111111111111111111, 222222222222222222}

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

bot.run("YOUR_BOT_TOKEN")