from django.core.management.base import BaseCommand
from msal import ConfidentialClientApplication
import requests
from decouple import config

# Constants
CLIENT_ID = config("MS_GRAPH_CLIENT_ID", default="")
TENANT_ID = config("MS_GRAPH_TENANT_ID", default="")
AUTHORITY = f'https://login.microsoftonline.com/{TENANT_ID}'
CLIENT_SECRET = config("MS_GRAPH_CLIENT_SECRET", default="")
USER_ID = config("MS_GRAPH_USER_ID", default="no.reply@paymentsave.co.uk")


def get_access_token():
    if not CLIENT_ID or not TENANT_ID or not CLIENT_SECRET:
        raise Exception("Missing Microsoft Graph credentials. Set MS_GRAPH_CLIENT_ID, MS_GRAPH_TENANT_ID, MS_GRAPH_CLIENT_SECRET.")
    # Initialize MSAL Confidential Client Application
    app = ConfidentialClientApplication(
        client_id=CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )
    # Acquire Token
    result = app.acquire_token_for_client(scopes=['https://graph.microsoft.com/.default'])
    print(result)
    if 'access_token' not in result:
        raise Exception("Failed to acquire token: " + str(result.get('error_description')))

    token = result['access_token']
    return token

# Function to send email
def send_email(subject, body, recipient):
    access_token = get_access_token()
    url = f"https://graph.microsoft.com/v1.0/users/{USER_ID}/sendMail"
    headers = {
        'Authorization': 'Bearer ' + access_token,
        'Content-Type': 'application/json'
    }
    body = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "html",
                "content": body
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": recipient
                    }
                }
            ]
        },
        "saveToSentItems": "true"
    }
    response = requests.post(url, headers=headers, json=body)
    return response.status_code, response.text


