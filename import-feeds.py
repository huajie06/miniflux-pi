#!/usr/bin/env python3
"""Import RSS feeds from rss-feed.yaml into Miniflux via API."""

import os
import sys
from pathlib import Path

import miniflux
import yaml


def load_env():
    """Load .env file into os.environ."""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print("Error: .env file not found. Copy .env.example to .env and fill in values.")
        sys.exit(1)
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def main():
    load_env()

    url = os.environ.get("MINIFLUX_URL")
    api_key = os.environ.get("MINIFLUX_API_KEY")
    if not url or not api_key:
        print("Error: MINIFLUX_URL and MINIFLUX_API_KEY must be set in .env")
        sys.exit(1)

    # Load feed definitions
    yaml_path = Path(__file__).parent / "rss-feed.yaml"
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    feeds = data.get("sources", {}).get("rss", [])

    # Connect to Miniflux
    client = miniflux.Client(url, api_key=api_key)
    try:
        client.me()  # Test connection
    except Exception as e:
        print(f"Error: Cannot connect to Miniflux at {url}: {e}")
        sys.exit(1)

    # Get existing categories (title -> id)
    existing_categories = {c["title"]: c["id"] for c in client.get_categories()}
    print(f"Found {len(existing_categories)} existing categories")

    # Get existing feeds (set of feed_urls)
    existing_feed_urls = {f["feed_url"] for f in client.get_feeds()}
    print(f"Found {len(existing_feed_urls)} existing feeds")

    # Create missing categories
    unique_categories = set(f["category"] for f in feeds)
    for cat_name in sorted(unique_categories):
        if cat_name not in existing_categories:
            result = client.create_category(cat_name)
            existing_categories[cat_name] = result["id"]
            print(f"  Created category: {cat_name} (id={result['id']})")

    # Create feeds
    created = 0
    skipped = 0
    failed = 0
    for feed in feeds:
        feed_url = feed["url"]
        category_name = feed["category"]
        enabled = feed.get("enabled", True)

        if feed_url in existing_feed_urls:
            print(f"  Skip (exists): {feed['name']}")
            skipped += 1
            continue

        category_id = existing_categories.get(category_name)
        if not category_id:
            print(f"  Error: category '{category_name}' not found for {feed['name']}")
            failed += 1
            continue

        try:
            feed_id = client.create_feed(
                feed_url,
                category_id=category_id,
                disabled=not enabled,
            )
            print(f"  Created: {feed['name']} (id={feed_id})")
            created += 1
        except Exception as e:
            print(f"  Failed: {feed['name']}: {e}")
            failed += 1

    print(f"\nDone: {created} created, {skipped} skipped, {failed} failed")


if __name__ == "__main__":
    main()
