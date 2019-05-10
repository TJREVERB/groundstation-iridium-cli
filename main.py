import json
from os import path
import click
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
SECRETS_URL = "credentials.json"
SECRETS_ENCRYPTED_URL = "credentials.json.gpg"
IMEI = None


def check_secrets_exists() -> bool:
    if path.exists(SECRETS_URL):
        return True
    elif path.exists(SECRETS_ENCRYPTED_URL):
        click.echo("Decrypt "
                   + click.style(SECRETS_ENCRYPTED_URL, bold=True)
                   + " to "
                   + click.style(SECRETS_URL, bold=True))
        return False
    else:
        click.echo("Obtain the credentials file "
                   + click.style(SECRETS_ENCRYPTED_URL, bold=True))
        return False


def get_imei() -> int:
    if check_secrets_exists():
        with open(SECRETS_URL) as f:
            data = json.load(f)

        imei = data["imei"]

        return imei


def get_service():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)

    return service


@click.group()
def main():
    global IMEI
    IMEI = get_imei()

    print(IMEI)


@main.command()
@click.option("-m", "--msg", "use_msg", is_flag=True)
@click.option("-f", "--file", "use_file", is_flag=True)
@click.argument("body")
def send(use_msg, use_file, body):
    service = get_service()

    if use_msg:
        create_file(body)
    elif use_file:
        pass
    else:
        create_file(body)

def create_file(msg):
    pass
