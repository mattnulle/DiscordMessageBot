import difflib
import discord
from .data_loader import search_index
import re

async def lookup_term(message, term):
    term_lower = term.lower()

    # Direct match
    if term_lower in search_index:
        category, entry = search_index[term_lower]
        await send_entry_embed(message, entry, category)
        return

    # Fuzzy match
    close_matches = difflib.get_close_matches(term_lower, search_index.keys(), n=1, cutoff=0.6)
    if close_matches:
        match = close_matches[0]
        category, entry = search_index[match]
        await message.channel.send(f"🔍 Did you mean **{entry.get('name')}**?")
        await send_entry_embed(message, entry, category)
    else:
        await message.channel.send(f"❌ No entry found for '{term}'.")

def strip_5e_tags(text):
    """
    Replaces 5eTools-style {@...} tags with the visible display text.
    Example:
        {@spell fireball|phb} → fireball
        {@i italic text} → italic text
    """
    tag_pattern = re.compile(r"\{@[^} ]+ ([^}|]+)(?:\|[^}]*)?\}")
    return tag_pattern.sub(r"\1", text)

def render_table_as_string(table_data, max_rows=20):
    """
    Convert a 5eTools-style table JSON into a readable string format.
    """
    col_labels = table_data.get("colLabels", ["", ""])
    rows = table_data.get("rows", [])

    lines = []

    if col_labels:
        col1, col2 = col_labels
        lines.append(f"**{col1}** | **{col2}**")
        lines.append(f"{'-'*len(col1)} | {'-'*len(col2)}")

    for i, row in enumerate(rows):
        if i >= max_rows:
            lines.append(f"...and {len(rows) - max_rows} more rows.")
            break
        if len(row) >= 2:
            left = row[0].replace("\n", " ").strip()
            right = row[1].replace("\n", " ").strip()
            lines.append(f"`{left:>6}` | {right}")

    return "\n".join(lines)

def parse_entries(entry):
    if isinstance(entry, str):
        return entry
    elif isinstance(entry, dict):
        if 'name' in entry and 'entries' in entry:
            return "**" + entry['name'] + ":**\n> " +  "\n> ".join([parse_entries(x) for x in entry["entries"]])
        elif 'entries' in entry:
            return "\n".join([parse_entries(x) for x in entry["entries"]])
        elif entry['type'] == 'table':
            return render_table_as_string(entry)
        else:
            return "***Unparsed " + entry['type'] + "***\n> " + str(entry)
    else:
        return str(entry)

async def send_entry_embed(message, entry, category):
    name = entry.get("name", "Unknown")
    description = ""

    if "entries" in entry:
        if isinstance(entry["entries"], list):
            description = "\n\n".join([parse_entries(x) for x in entry["entries"]])
        else:
            description = str(entry["entries"])
    elif "desc" in entry:
        description = entry["desc"] if isinstance(entry["desc"], str) else "\n\n".join(entry["desc"])
    else:
        description = "No description available."

    embed = discord.Embed(
        title=name,
        description=strip_5e_tags(description)[:2048],
        color=discord.Color.blurple()
    )

    for field in ["level", "type", "size", "school", "source", "ac", "hp", "speed", "str" ,"dex" ,"con" ,"int" ,"wis" ,"cha", "range", "duration", "savingThrow", "time"]:
        if field in entry:
            value = entry[field]
            if isinstance(value, dict) and "name" in value:
                value = value["name"]
            embed.add_field(name=field.capitalize(), value=str(value), inline=True)

    embed.set_footer(text=f"Category: {category}")
    await message.channel.send(embed=embed)

