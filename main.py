import discord
import json
import re
import os

# Load Discord token from Railway environment variables
TOKEN = os.getenv("DISCORD_TOKEN")

# Discord bot intents
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Load or create stock data
DATA_FILE = "data.json"
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        stock_data = json.load(f)
else:
    stock_data = {
        "Bamboo": 1.0,
        "Tomato": 1.0,
        "Blueberry": 1.0,
        "Strawberry": 1.0,
        "Carrot": 1.0
    }

@client.event
async def on_ready():
    print(f"Bot is online as {client.user}")

@client.event
async def on_message(message):
    # Ignore our own messages
    if message.author == client.user:
        return

    # Detect Grow a Garden Stock messages
    if message.author.bot and "Grow a Garden Stock" in message.content:
        # Extract seed names (before "x<number>")
        seeds_found = re.findall(r"\n\s*([\w\s]+?)\s*x\d+", message.content)
        seeds_found = [s.strip() for s in seeds_found]

        print(f"Detected seeds: {seeds_found}")

        # Update scores
        for seed in stock_data.keys():
            if seed in seeds_found:
                stock_data[seed] += 0.05  # appeared
            else:
                stock_data[seed] += 0.01  # didn't appear (small decay)

        # Add new seeds if not in data
        for seed in seeds_found:
            if seed not in stock_data:
                stock_data[seed] = 1.0

        # Save updated data
        with open(DATA_FILE, "w") as f:
            json.dump(stock_data, f, indent=2)

        # Predict next stock
        next_stock = max(stock_data, key=stock_data.get)
        await message.channel.send(f"🌱 Next predicted stock: **{next_stock}**")

# Start the bot
client.run(TOKEN)