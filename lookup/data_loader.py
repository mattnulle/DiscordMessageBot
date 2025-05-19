import json
from pathlib import Path

DATA_PATH = Path("data")

data_cache = {}      # { category: [entries] }
search_index = {}    # { name_lower: (category, entry) }

def load_all_data():
    for json_file in DATA_PATH.rglob("*.json"):
        if json_file.name.startswith("fluff-"):
            continue  # Skip fluff files

        category = json_file.parent.name  # e.g., 'spells' from 'data/spells/spells-phb.json'
        try:
            with open(json_file, encoding="utf-8") as f:
                json_data = json.load(f)

            # Skip if not a dict or empty
            if not isinstance(json_data, dict) or not json_data:
                continue

            for key, entries in json_data.items():
                if not isinstance(entries, list):
                    entries = [entries]

                data_cache.setdefault(category, []).extend(entries)

                for entry in entries:
                    name = entry.get("name", "").lower()
                    if name:
                        search_index[name] = (category, entry)
        except Exception as e:
            print(f"⚠️ Failed to load {json_file}: {e}")
