#!/usr/bin/env python3
"""Merge Pages CMS JSON entries into the existing Toy JSON format.

Each entry is authoritative; the published resources.json retains order for
unchanged IDs, while new IDs are appended in stable filename order.
Never edit resources.json manually after migration.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "toy" / "resources.json"
ENTRIES = ROOT / "toy" / "entries"
CATEGORIES = ROOT / "toy" / "categories.json"
REQUIRED = {"name", "group"}
CATEGORY_TYPES = {"wow": "魔兽资源", "ios": "游戏", "other": "其他"}
ALLOWED = {"id", "autoId", "name", "group", "desc", "type", "icon", "tags", "url", "links", "linkItems"}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def build():
    old = load(OUT)
    categories = load(CATEGORIES)
    if not isinstance(categories, list) or not categories:
        raise ValueError("Categories cannot be empty")
    group_ids = {c["id"] for c in categories}
    category_by_id = {c["id"]: c for c in categories}
    if len(group_ids) != len(categories):
        raise ValueError("Duplicate category IDs")
    existing = old.get("resources", [])
    if not isinstance(existing, list):
        raise ValueError("resources must be an array")
    source = {}
    entry_updates = []
    paths = sorted(ENTRIES.glob("*.json"))
    if not paths:
        raise ValueError("No entries found: refusing to replace the catalog")
    for path in paths:
        original = load(path)
        item = dict(original) if isinstance(original, dict) else original
        if not isinstance(item, dict) or not REQUIRED.issubset(item):
            raise ValueError(f"{path}: missing required fields")
        rid = item.get("id") or path.stem
        if not isinstance(rid, str) or not rid or rid != path.stem:
            raise ValueError(f"{path}: ID must match filename")
        # autoId only helps Pages CMS name newly created files; it is not
        # part of the published resource schema.
        item.pop("autoId", None)
        item["id"] = rid
        if rid in source:
            raise ValueError(f"Duplicate ID: {rid}")
        if not isinstance(item["name"], str) or not item["name"].strip():
            raise ValueError(f"{path}: empty name")
        if item["group"] not in group_ids:
            raise ValueError(f"{path}: invalid group {item['group']}")
        if not set(item).issubset(ALLOWED):
            raise ValueError(f"{path}: unrecognized keys {set(item)-ALLOWED}")
        # Backfill only missing values; preserve existing custom type/icon.
        # Category icons come from the same categories.json used by Toy.
        if not item.get("type"):
            item["type"] = CATEGORY_TYPES.get(item["group"], "其他")
        if not item.get("icon"):
            item["icon"] = category_by_id[item["group"]].get("icon") or "📂"
        if "tags" in item and (not isinstance(item["tags"], list) or any(not isinstance(x,str) for x in item["tags"])):
            raise ValueError(f"{path}: invalid tags")
        if "links" in item and (not isinstance(item["links"], dict) or any(not isinstance(v,str) for v in item["links"].values())):
            raise ValueError(f"{path}: invalid links")
        if "url" in item and not isinstance(item["url"], str):
            raise ValueError(f"{path}: invalid url")
        # linkItems is the canonical editable list. Derive legacy links for old Toy.
        # Multiple URLs with the same display name remain in linkItems; legacy
        # Toy receives the first one for that name, rather than failing to load.
        if "linkItems" in item:
            links = item["linkItems"]
            if not isinstance(links, list) or len(links) > 60:
                raise ValueError(f"{path}: invalid linkItems")
            legacy = {}
            for link in links:
                if (not isinstance(link, dict) or set(link) != {"name", "url"}
                    or not isinstance(link["name"], str)
                    or not link["name"].strip() or len(link["name"]) > 120
                    or not isinstance(link["url"], str)
                    or len(link["url"]) > 4096
                    or not link["url"].startswith(("https://", "http://"))):
                    raise ValueError(f"{path}: invalid linkItems record")
                name = link["name"].strip()
                if name not in legacy and len(legacy) < 20:
                    legacy[name] = link["url"].strip()
            item["links"] = legacy
        # Persist only the auto-filled metadata into the editable source.
        # Do not persist derived legacy links; the editor keeps linkItems as
        # the single source of truth for new resources.
        if any(original.get(k) != item[k] for k in ("id", "type", "icon")):
            updated = dict(original)
            for k in ("id", "type", "icon"):
                updated[k] = item[k]
            entry_updates.append((path, updated))
        source[rid] = item
    ordered_ids = [r["id"] for r in existing if r["id"] in source]
    ordered_set = set(ordered_ids)
    ordered_ids.extend(sorted(set(source) - ordered_set))
    merged = dict(old)
    merged["categories"] = categories
    merged["resources"] = [source[rid] for rid in ordered_ids]
    if not merged["resources"]:
        raise ValueError("Refusing to publish an empty catalog")
    encoded = json.dumps(merged, ensure_ascii=False, indent=2) + "\n"
    if "--check" in sys.argv:
        if entry_updates:
            print(f"Entries require metadata backfill: {len(entry_updates)}")
            return 1
        live = load(OUT)
        if live.get("resources") != merged["resources"] or live.get("categories") != categories:
            print("Generated catalog differs from published JSON")
            return 1
        print(f"OK: {len(source)} entries, {len(categories)} categories")
        return 0
    for path, updated in entry_updates:
        path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    if entry_updates:
        print(f"Backfilled {len(entry_updates)} editable entries")
    if OUT.read_text(encoding="utf-8") != encoded:
        OUT.write_text(encoded, encoding="utf-8")
        print(f"Updated {OUT} ({len(source)} entries)")
    else:
        print(f"Unchanged: {len(source)} entries")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(build())
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
