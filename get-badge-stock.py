#! /usr/bin/env python3

import json
import requests
import logging
import time
from datetime import date
import pandas as pd
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

log_level = "WARNING"
logging.basicConfig(level=log_level)

token_url = 'https://www.onlinescoutmanager.co.uk/oauth/token'
api_url = 'https://www.onlinescoutmanager.co.uk'

# Read credentials from .credentials file
credentials = {}
with open('.credentials', 'r') as f:
    for line in f:
        line = line.strip()
        if '=' in line:
            key, value = line.split('=', 1)
            credentials[key.strip()] = value.strip()

client_id = credentials.get('client_id', '')
client_secret = credentials.get('secret', '')

# Load section name mappings
with open('sections.json', 'r') as f:
    sections_config = json.load(f)
    section_names = sections_config['sections']
    excluded_sections = set(sections_config.get('exclude', []))


def get_access_token(client_id, client_secret, token_url):
    try:
        oauth_client = BackendApplicationClient(client_id=client_id)
        oauth = OAuth2Session(client=oauth_client)
        token = oauth.fetch_token(
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,
            scope='section:badge:read',
        )
        logging.info(f"Token obtained, expires in {token.get('expires_in')}s")
        return token.get('access_token')
    except Exception as e:
        logging.error(f"Failed to obtain token: {e}")
        return None


def make_api_call(url, headers, data=None):
    """Make an API call with rate limit handling."""
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()

        ratelimit_remaining = int(response.headers.get('X-RateLimit-Remaining', 999))
        ratelimit_reset = int(response.headers.get('X-RateLimit-Reset', 0))
        logging.info(f"API requests remaining: {ratelimit_remaining}")

        if ratelimit_remaining < 100:
            logging.warning(f"Close to rate limit - pausing for {ratelimit_reset}s")
            time.sleep(ratelimit_reset)

        if response.status_code == 429:
            delay = int(response.headers.get('Retry-After', 60))
            logging.warning(f"Rate limited. Retrying in {delay}s")
            time.sleep(delay)
            return make_api_call(url, headers, data)

        return response.json()

    except requests.exceptions.RequestException as e:
        logging.error(e)
        return None


def find_current_term(terms):
    """Find the term that covers today's date."""
    today = date.today().isoformat()
    for term in terms:
        if term.get('startdate', '') <= today <= term.get('enddate', ''):
            return term
    if terms:
        return terms[-1]
    return None


def get_sections_and_terms(access_token):
    """Fetch section config and current terms from the API."""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    config = make_api_call(f"{api_url}/api.php?action=getSectionConfig", headers)
    terms = make_api_call(f"{api_url}/api.php?action=getTerms", headers)

    if not config or not terms:
        return {}

    sections = {}
    for section_id, section_config in config.items():
        if not isinstance(section_config, dict):
            continue

        # Skip excluded sections
        if section_id in excluded_sections:
            continue

        section_terms = terms.get(section_id, [])
        section_type = section_config.get('section_type', section_config.get('sectionType', ''))
        current_term = find_current_term(section_terms)

        if current_term:
            sections[section_id] = {
                'name': section_names.get(section_id, f'Section {section_id}'),
                'section_type': section_type,
                'term_id': current_term['termid'],
            }

    return sections


def get_badge_stock(access_token, section_id, section_type, term_id):
    """Fetch badge stock for a section."""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    url = (
        f"{api_url}/ext/badges/stock/?action=getBadgeStock"
        f"&section={section_type}&section_id={section_id}"
        f"&term_id={term_id}&seeIfShared=y"
    )
    return make_api_call(url, headers)


def collate_badge_stock(access_token, sections):
    """Collect badge stock from all sections and combine into one list."""
    all_items = []

    for section_id, config in sections.items():
        name = config['name']
        print(f"Fetching badge stock for {name}...")
        result = get_badge_stock(
            access_token, section_id, config['section_type'], config['term_id']
        )

        if result is None:
            logging.error(f"Failed to get badge stock for {name}")
            continue

        items = result.get('items', [])
        for item in items:
            all_items.append({
                'Section': name,
                'Badge': item.get('name', ''),
                'Stock': item.get('stock', 0),
                'Desired': item.get('desired', 0),
                'To Buy': item.get('buy', 0),
                'Due': item.get('due', 0),
            })

    return all_items


# Main
access_token = get_access_token(client_id, client_secret, token_url)

if not access_token:
    logging.error("Failed to obtain the access token.")
    exit(1)

# Auto-discover sections and current terms
sections = get_sections_and_terms(access_token)

if not sections:
    print("No sections found.")
    exit(1)

print(f"Found {len(sections)} sections\n")

all_items = collate_badge_stock(access_token, sections)

if all_items:
    df = pd.DataFrame(all_items)

    # Pivot for To Buy tab: one row per badge, one column per section
    pivot = df.pivot_table(
        index='Badge', columns='Section', values='To Buy',
        aggfunc='sum', fill_value=0
    )
    pivot['Total'] = pivot.sum(axis=1)
    to_buy = pivot[pivot['Total'] > 0].sort_index()

    if not to_buy.empty:
        print("\nBadges to buy:\n")
        print(to_buy.to_string())
    else:
        print("\nNo badges need purchasing across any section.")

    # Save to Excel
    output_path = f"badge-stock-collated-{date.today().strftime('%Y_%m_%d')}.xlsx"
    with pd.ExcelWriter(output_path) as writer:
        df.to_excel(writer, sheet_name='All Stock', index=False)
        to_buy.to_excel(writer, sheet_name='To Buy')
    print(f"\nSaved to {output_path}")

    # Show which sections need badge orders
    if not to_buy.empty:
        sections_needing_badges = [
            col for col in to_buy.columns
            if col != 'Total' and to_buy[col].sum() > 0
        ]
        if sections_needing_badges:
            print("\nSections needing badge orders:")
            for name in sections_needing_badges:
                total = int(to_buy[name].sum())
                print(f"  {name}: {total} badges to buy")
else:
    print("No badge stock data collected.")
