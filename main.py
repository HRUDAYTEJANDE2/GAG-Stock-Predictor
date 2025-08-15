# bot.py
import discord
from discord.ext import commands
import json, os, random, re
from typing import Dict, List

# ===== CONFIG =====
TOKEN = DISCORD_TOKEN         # put your bot token here
OTHER_BOT_ID = 1364847027674021938    # replace with the other bot's user ID
PROB_FILE = "probabilities.json"
LEARN_INCREMENT = 0.1                  # how much to bump an item when seen
MIN_WEIGHT = 0.0001                    # tiny floor to keep items selectable
# ==================

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------- Probabilities storage ----------
def _lower_keys(d: Dict[str, float]) -> Dict[str, float]:
    return {k.lower(): float(v) for k, v in d.items()}

def _title_keys(d: Dict[str, float]) -> Dict[str, float]:
    return {k.title(): float(max(v, MIN_WEIGHT)) for k, v in d.items()}

def load_probabilities() -> Dict[str, Dict[str, float]]:
    if not os.path.exists(PROB_FILE):
        return {"seeds": {}, "gear": {}}
    with open(PROB_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return {
        "seeds": _lower_keys(raw.get("seeds", {})),
        "gear": _lower_keys(raw.get("gear", {})),
    }

def save_probabilities(probs: Dict[str, Dict[str, float]]) -> None:
    out = {"seeds": _title_keys(probs["seeds"]), "gear": _title_keys(probs["gear"])}
    with open(PROB_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

PROBS = load_probabilities()

# ---------- Helpers ----------
def clean_item_line(line: str) -> str:
    """
    Convert lines like '🫐 Blueberry x5' -> 'blueberry'
    - remove trailing ' xN' (supports × or x)
    - strip leading non-word chars (emoji)
    """
    s = line.strip()
    s = re.sub(r"\s*[x×]\s*\d+\s*$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^[^\w]+", "", s)
    s = re.sub(r"\s{2,}", " ", s)
    return s.lower().strip()

def weighted_sample_without_replacement(weights: Dict[str, float], k: int) -> List[str]:
    items = list(weights.keys())
    w = [max(weights[i], MIN_WEIGHT) for i in items]
    chosen = []
    k = min(k, len(items))
    for _ in range(k):
        pick = random.choices(items, weights=w, k=1)[0]
        idx = items.index(pick)
        chosen.append(pick)
        items.pop(idx); w.pop(idx)
    return chosen

def update_learning(category: str, observed: List[str]) -> None:
    table = PROBS[category]
    for item in observed:
        table[item] = table.get(item, MIN_WEIGHT) + LEARN_INCREMENT
    # keep a floor
    for k in list(table.keys()):
        table[k] = max(table[k], MIN_WEIGHT)
    save_probabilities(PROBS)

def predict_next(category: str, exclude: List[str], count: int) -> List[str]:
    table = {k: v for k, v in PROBS[category].items() if k not in exclude}
    if not table:
        return []
    return weighted_sample_without_replacement(table, count)

# ---------- Bot events ----------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}. Using {PROB_FILE}")

@bot.event
async def on_message(message: discord.Message):
    # ignore ourselves
    if message.author.id == bot.user.id:
        return

    # only handle the other bot's embed posts
    if message.author.id == OTHER_BOT_ID and message.embeds:
        embed = message.embeds[0]
        seeds_found, gear_found = [], []

        for field in embed.fields:
            fname = (field.name or "").lower()
            lines = [ln for ln in (field.value or "").split("\n") if ln.strip()]
            if "seed" in fname:
                for ln in lines:
                    item = clean_item_line(ln)
                    if item:
                        seeds_found.append(item)
            elif "gear" in fname:
                for ln in lines:
                    item = clean_item_line(ln)
                    if item:
                        gear_found.append(item)

        if seeds_found or gear_found:
            # learn
            if seeds_found: update_learning("seeds", seeds_found)
            if gear_found: update_learning("gear", gear_found)

            # predict same counts, excluding just-seen items
            predicted_seeds = predict_next("seeds", seeds_found, len(seeds_found))
            predicted_gear  = predict_next("gear",  gear_found,  len(gear_found))

            # reply in same 2-section style (no emojis/quantities)
            e = discord.Embed(
                title="Next Stock Will Be",
                description="(predicted from learned frequencies)",
                color=discord.Color.green()
            )
            if predicted_seeds:
                e.add_field(name="Seeds", value="\n".join([s.title() for s in predicted_seeds]), inline=True)
            if predicted_gear:
                e.add_field(name="Gear",  value="\n".join([g.title() for g in predicted_gear]),  inline=True)

            await message.channel.send(embed=e)

    await bot.process_commands(message)

# Optional: quick debug command
@bot.command()
async def top(ctx, category: str = "seeds"):
    category = category.lower()
    if category not in PROBS:
        await ctx.send("Use: !top seeds  or  !top gear")
        return
    top5 = sorted(PROBS[category].items(), key=lambda kv: kv[1], reverse=True)[:5]
    await ctx.send("\n".join([f"{k.title()}: {v:.3f}" for k, v in top5]))

bot.run(TOKEN)
