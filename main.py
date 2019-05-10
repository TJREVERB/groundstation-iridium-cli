import base64
import json
import mimetypes
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from os import path
import click
import pickle
import os.path
from googleapiclient.discovery import build
from googleapiclient import errors
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.send']
SECRETS_FILENAME = "credentials.json"
SECRETS_FILENAME_ENCRYPTED = "credentials.json.gpg"
IMEI = None

MSG_FILENAME_DEFAULT = "msg.sbd"

MAIL_TO_SEND = "data@sbd.iridium.com"
MAIL_FROM = "tjreverb@gmail.com"


def check_secrets_exists() -> bool:
    if path.exists(SECRETS_FILENAME):
        return True
    elif path.exists(SECRETS_FILENAME_ENCRYPTED):
        click.echo("Decrypt "
                   + click.style(SECRETS_FILENAME_ENCRYPTED, bold=True)
                   + " to "
                   + click.style(SECRETS_FILENAME, bold=True))
        return False
    else:
        click.echo("Obtain the credentials file "
                   + click.style(SECRETS_FILENAME_ENCRYPTED, bold=True))
        return False


def get_imei() -> int:
    if check_secrets_exists():
        with open(SECRETS_FILENAME) as f:
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


@main.command()
@click.option("-m", "--msg", "use_msg", is_flag=True)
@click.option("-f", "--file", "use_file", is_flag=True)
@click.argument("body")
def send(use_msg, use_file, body):
    service = get_service()
    click.echo("IMEI: " + str(IMEI))

    if use_msg:
        create_msg_file(body)
        send_mail(MSG_FILENAME_DEFAULT, service)
        delete_msg_file()
    elif use_file:
        if not os.path.exists(body):
            click.echo("ERROR: File not found", err=True)
            return
        if not body.endswith(".sbd"):
            click.echo("ERROR: Invalid filename", err=True)
            return
        send_mail(body, service)
    else:
        create_msg_file(body)
        send_mail(MSG_FILENAME_DEFAULT, service)
        delete_msg_file()


def send_mail(msg_filename, service):
    message = MIMEMultipart()
    message["to"] = MAIL_TO_SEND
    message["from"] = MAIL_FROM
    message["subject"] = str(IMEI)

    mail_body = MIMEText("")
    message.attach(mail_body)

    content_type, encoding = mimetypes.guess_type(msg_filename)

    if content_type is None or encoding is not None:
        content_type = 'application/octet-stream'
    main_type, sub_type = content_type.split('/', 1)

    file_attachment = open(msg_filename, 'rb')
    mail_attachment = MIMEBase(main_type, sub_type)
    mail_attachment.set_payload(file_attachment.read())
    encoders.encode_base64(mail_attachment)
    file_attachment.close()

    filename = os.path.basename(msg_filename)
    mail_attachment.add_header(
        'Content-Disposition', 'attachment', filename=filename)
    message.attach(mail_attachment)

    # Create the encoded message
    message_encoded = {'raw': base64.urlsafe_b64encode(
        message.as_bytes()).decode()}

    try:
        message = (service.users().messages().send(userId=MAIL_FROM, body=message_encoded)
                   .execute())
        click.echo('SUCCESS: Message sent, ID: %s' % message['id'])
        return message
    except errors.HttpError as error:
        click.echo('ERROR: %s' % error, err=True)


def create_msg_file(msg):
    delete_msg_file()
    msg_file = open(MSG_FILENAME_DEFAULT, "w+")
    msg_file.write(msg)
    msg_file.close()


def delete_msg_file():
    if os.path.exists(MSG_FILENAME_DEFAULT):
        os.remove(MSG_FILENAME_DEFAULT)
    else:
        click.echo("WARN: Default message file not found")
