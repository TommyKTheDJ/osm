import requests
import logging
import pprint

log_level = "WARNING"
logging.basicConfig(level=log_level)
pp = pprint.PrettyPrinter(indent=4)

token_url = 'https://www.onlinescoutmanager.co.uk/oauth/token'
api_url = 'https://www.onlinescoutmanager.co.uk/api.php'

# Replace these with your actual client credentials and token URL
client_id = ''
client_secret = ''


def get_access_token(client_id, client_secret, token_url):
    # Set up the OAuth 2.0 token request data
    token_data = {
        'grant_type': 'client_credentials',
        'scope': 'section:programme:write',
        'client_id': client_id,
        'client_secret': client_secret
    }

    try:
        # Send a POST request to the token endpoint to get the access token
        response = requests.post(token_url, data=token_data)

        # Check if the request was successful
        response.raise_for_status()

        # Parse the response JSON to get the access token
        access_token = response.json().get('access_token')
        return access_token

    except requests.exceptions.RequestException as e:
        logging.error(e)
        return None


def get_sections(access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',  # Include the access token in the Authorization header
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    request_url = f"{api_url}?action=getSectionConfig"
    try:
        # Send a POST request to the API endpoint with the access token in the headers
        response = requests.post(request_url, headers=headers)

        # Check if the request was successful
        response.raise_for_status()

        # Process the API response
        data = response.json()
        logging.debug(data)
        pp.pprint(data)

        ## OSM docs on rate limits suggest:
        # Please monitor the standard rate limit headers to ensure your application does not get blocked automatically. Applications that are frequently blocked will be permanently blocked.
        # X-RateLimit-Limit - this is the number of requests per hour that your API can perform (per authenticated user)
        # X-RateLimit-Remaining - this is the number of requests remaining that the current user can perform before they are blocked
        # X-RateLimit-Reset - this is the number of seconds until the rate limit for the current user resets back to your overall limit
        # An HTTP 429 status code will be sent if the user goes over the limit, along with a Retry-After header with the number of seconds until you can use the API again.
        # Please also enforce your own lower rate limits, especially if you are allowing unauthenticated users to manipulate your data (e.g. allowing members to join a waiting list).

        ratelimit_remaining = int(response.headers['X-RateLimit-Remaining'])
        logging.info(f"Number of API requests remaining: {ratelimit_remaining}")
        ratelimit_reset = int(response.headers['X-RateLimit-Reset'])
        logging.info(f"Time until number of remaining requests resets: {ratelimit_reset}")

        if ratelimit_remaining < 100:
            logging.info(f"Close to rate limit - pausing for {ratelimit_reset}")
            time.sleep(delay)
            # Once delayed, retry the API call
            return make_api_call(url, headers, data)

        # If the response code is 429, wait for the specified time (this shouldn't happen if the above code is working as expected)
        if response.status_code == 429:
            if 'Retry-After' in response.headers:
                delay = int(response.headers['Retry-After'])
                logging.info(f"Rate limited. Retrying in {delay} seconds")
                time.sleep(delay)
                # Once delayed, retry the API call
                return make_api_call(url, headers, data)

        logging.info(f"Response Status Code: {str(response.status_code)}")
        for key, value in response.headers.items():
            if 'X-RateLimit' in key: 
                logging.info(f"{key}: {value}")

    except requests.exceptions.RequestException as e:
        logging.error(e)
        return None


# Get the access token
access_token = get_access_token(client_id, client_secret, token_url)

if access_token:
    get_sections(access_token)
else:
    logging.error("Failed to obtain the access token.")
