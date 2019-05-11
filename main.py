import base64
import json
import mimetypes
import datetime
from pytz import timezone
from email import message_from_string
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
SCOPES = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.modify']
SECRETS_FILENAME = "credentials.json"
SECRETS_FILENAME_ENCRYPTED = "credentials.json.gpg"
IMEI = None

MSG_FILENAME_DEFAULT = "msg.sbd"

MAIL_TO_SEND = "data@sbd.iridium.com"
MAIL_FROM = "tjreverb@gmail.com"

MAIL_RECEIVE = "sbdservice@sbd.iridium.com"
MAIL_RECEIVE_SUBJECT = "SBD Msg From Unit: "


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
    global IMEI, MAIL_RECEIVE_SUBJECT
    IMEI = get_imei()
    MAIL_RECEIVE_SUBJECT += str(IMEI)
    click.secho("IMEI: " + str(IMEI) , fg="green")


@main.command()
@click.option("-m", "--msg", "use_msg", is_flag=True)
@click.option("-f", "--file", "use_file", is_flag=True)
@click.argument("body")
def send(use_msg, use_file, body):
    service = get_service()

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


@main.command()
@click.option("-n", "num_msgs", default=1)
def receive(num_msgs):
    service = get_service()
    query = "from:" + MAIL_RECEIVE + " " \
            + "subject:" + MAIL_RECEIVE_SUBJECT + " " \
            + "has:attachment"
    messages = receive_msg_list(service, MAIL_FROM, num_msgs, query)

    for message in messages:
        msg_body = str(receive_msg_body(service, MAIL_FROM, message["id"]))
        msg_decoded = receive_msg_attach(service, MAIL_FROM, message["id"], "")
        if msg_decoded is not None or msg_decoded:
            click.secho(get_msg_send_date(msg_body).strftime("%c"), fg="cyan")
            click.echo(msg_decoded)
            click.echo()


def receive_msg_list(service, user_id, max_results, query=''):
    """List all Messages of the user's mailbox matching the query.

    Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address. The special value "me"
        can be used to indicate the authenticated user.
        query: String used to filter messages returned.
        Eg.- 'from:user@some_domain.com' for Messages from a particular sender.

    Returns:
        List of Messages that match the criteria of the query. Note that the
        returned list contains Message IDs, you must use get with the
        appropriate ID to get the details of a Message.
    """

    try:
        response = service.users().messages().list(userId=user_id,
                                                   q=query,
                                                   maxResults=max_results).execute()
        messages = []

        if 'messages' in response:
            messages.extend(response['messages'])

        while 'nextPageToken' in response:
            page_token = response['nextPageToken']
            response = service.users().messages().list(userId=user_id, q=query,
                                                 pageToken=page_token).execute()
            messages.extend(response['messages'])

        return messages[:max_results]

    except errors.HttpError as error:
            click.echo('ERROR: %s' % error, err=True)


def receive_msg_body(service, user_id, msg_id):
    """Get a Message and use it to create a MIME Message.

    Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address. The special value "me"
        can be used to indicate the authenticated user.
        msg_id: The ID of the Message required.

    Returns:
        A MIME Message, consisting of data from Message.
    """

    try:
        message = service.users().messages().get(userId=user_id, id=msg_id,
                                                 format='raw').execute()

        msg_str = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))

        mime_msg = message_from_string(msg_str.decode())

        return mime_msg

    except errors.HttpError as error:
            click.echo('ERROR: %s' % error, err=True)


def receive_msg_attach(service, user_id, msg_id, store_dir="msg", save=False):
    """Get and store attachment from Message with given id.

    Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address. The special value "me"
        can be used to indicate the authenticated user.
        msg_id: ID of Message containing attachment.
        store_dir: The directory used to store attachments.
    """
    try:
        message = service.users().messages().get(userId=user_id, id=msg_id).execute()

        for part in message['payload']['parts']:
            if part['filename']:
                if 'data' in part['body']:
                    attach_data = part['body']['data']
                else:
                    attach_id = part['body']['attachmentId']
                    attach = service.users().messages().attachments().get(userId=user_id, messageId=msg_id,
                                                                       id=attach_id).execute()
                    attach_data = attach['data']

                file_data = base64.urlsafe_b64decode(attach_data
                                                     .encode('UTF-8'))

                file_decoded_msg = file_data.decode()

                if save:
                    file_local_path = ''.join([store_dir, part['filename']])

                    f = open(file_local_path, 'w')
                    f.write(file_decoded_msg)
                    f.close()

                return file_decoded_msg

    except errors.HttpError as error:
            click.echo('ERROR: %s' % error, err=True)


def get_msg_send_date(msg_body) -> datetime.datetime:
    date = ""
    for line in msg_body.split("\n"):
        if "Time of Session" in line:
            date = line.strip()

    date_string = date.replace("Time of Session (UTC): ", "")
    date_format = '%c'

    try:
        date_parsed = datetime.datetime.strptime(date_string, date_format)

        date_parsed_tz = date_parsed.replace(tzinfo=timezone("UTC")).astimezone(timezone("US/Eastern"))

        return date_parsed_tz
    except ValueError:
        click.echo("WARN: Unable to parse message date")
        return

