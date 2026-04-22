#! /usr/bin/env python3

import json
import requests
import logging
import time
from datetime import date
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

log_level = "WARNING"
logging.basicConfig(level=log_level)

token_url = 'https://www.onlinescoutmanager.co.uk/oauth/token'
api_url = 'https://www.onlinescoutmanager.co.uk/api.php'

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
    # If no exact match, return the latest term
    if terms:
        return terms[-1]
    return None


def get_sections(access_token):
    """Fetch section config and display section ID, type, and current term."""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    result = make_api_call(f"{api_url}?action=getSectionConfig", headers)
    if result is None:
        logging.error("Failed to get section config")
        return

    terms_result = make_api_call(f"{api_url}?action=getTerms", headers)

    # Build terms lookup by section_id
    terms_by_section = {}
    if isinstance(terms_result, dict):
        terms_by_section = terms_result

    print(f"{'ID':<8} {'Name':<20} {'Type':<10} {'Current Term':<25} {'Term ID':<10} {'Dates'}")
    print("-" * 100)

    for section_id, config in result.items():
        if not isinstance(config, dict):
            continue

        name = section_names.get(section_id, '?')
        section_type = config.get('section_type', config.get('sectionType', '?'))
        terms = terms_by_section.get(section_id, [])
        current = find_current_term(terms)

        if current:
            term_name = current.get('name', '?')
            term_id = current.get('termid', '?')
            dates = f"{current.get('startdate', '?')} to {current.get('enddate', '?')}"
        else:
            term_name = 'No terms'
            term_id = '-'
            dates = '-'

        print(f"{section_id:<8} {name:<20} {section_type:<10} {term_name:<25} {term_id:<10} {dates}")


# Main
access_token = get_access_token(client_id, client_secret, token_url)

if access_token:
    get_sections(access_token)
else:
    logging.error("Failed to obtain the access token.")
