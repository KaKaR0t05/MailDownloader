import imaplib
import email
import os
import logging
from datetime import datetime
import time

GMAIL_IMAP_SERVER = 'imap.gmail.com'
UNREAD_EMAIL_CRITERIA = 'UNSEEN'
MAX_RETRIES = 3  
RETRY_DELAY = 5  


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EmailDownloader:
    def __init__(self, email_user, email_pass, base_dir, senders_dict):
        """Initialize the EmailDownloader with user credentials and settings."""
        self.email_user = email_user
        self.email_pass = email_pass
        self.base_dir = base_dir
        self.senders_dict = senders_dict
        self.mail = None
        self.attachments_dir = None

    def connect(self):
        retries = 0
        while retries < MAX_RETRIES:
            try:
                self.mail = imaplib.IMAP4_SSL(GMAIL_IMAP_SERVER)
                self.mail.login(self.email_user, self.email_pass)
                logging.info(f"Connected to Gmail as {self.email_user}.")
                return  # Exit the method once connected successfully
            except imaplib.IMAP4.error as error:
                retries += 1
                logging.error(f"Failed to connect to Gmail (Attempt {retries}/{MAX_RETRIES}): {error}")
                if retries < MAX_RETRIES:
                    logging.info(f"Retrying connection in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
        logging.error(f"Failed to connect after {MAX_RETRIES} attempts.")
        self.mail = None

    def create_attachments_directory(self):
        today_date = datetime.now().strftime('%Y-%m-%d')
        self.attachments_dir = os.path.join(self.base_dir, today_date)

        if not os.path.isdir(self.attachments_dir):
            try:
                os.makedirs(self.attachments_dir)
                logging.info(f"Created directory: {self.attachments_dir}")
            except Exception as error:
                logging.error(f"Error creating directory {self.attachments_dir}: {error}")
                self.attachments_dir = None

    def download_attachments(self):
        if self.mail is None:
            logging.error("Mail connection is not established. Exiting.")
            return

        retries = 0
        while retries < MAX_RETRIES:
            try:
                self.mail.select('inbox')
                result, data = self.mail.search(None, UNREAD_EMAIL_CRITERIA)
                email_ids = data[0].split()

                for email_id in email_ids:
                    self.process_email(email_id)
                return  # Exit if download is successful
            except (imaplib.IMAP4.abort, imaplib.IMAP4.error) as error:
                retries += 1
                logging.error(f"Error while downloading attachments (Attempt {retries}/{MAX_RETRIES}): {error}")
                if retries < MAX_RETRIES:
                    logging.info(f"Retrying download in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
        logging.error(f"Failed to download attachments after {MAX_RETRIES} attempts.")

    def process_email(self, email_id):
        try:
            result, msg_data = self.mail.fetch(email_id, '(RFC822)')
            if result != 'OK':
                logging.error(f"Failed to fetch email ID {email_id}.")
                return

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            sender_email = msg['From']

            if sender_email in self.senders_dict:
                self.save_attachments(msg, sender_email)
                # Mark the email as read after processing
                self.mail.store(email_id, '+FLAGS', '\\Seen')
            else:
                logging.info(f'Email from {sender_email} is not in the specified senders.')
        except Exception as error:
            logging.error(f"Error processing email ID {email_id}: {error}")

    def save_attachments(self, msg, sender_email):
        if msg.is_multipart():
            for part in msg.walk():
                if self.is_attachment(part):
                    self.save_attachment(part, sender_email)

    def is_attachment(self, part):
        return part.get_content_maintype() != 'multipart' and part.get('Content-Disposition') is not None

    def save_attachment(self, part, sender_email):
        filename = part.get_filename()
        if filename:
            filepath = os.path.join(self.attachments_dir, filename)

            try:
                with open(filepath, 'wb') as file:
                    file.write(part.get_payload(decode=True))
                logging.info(f'Downloaded: {filename} from {sender_email}')
            except Exception as error:
                logging.error(f"Error saving attachment {filename}: {error}")

    def logout(self):
        if self.mail:
            self.mail.logout()
            logging.info(f"Logged out from {self.email_user}.")

def main():
    email_accounts = [
        {
            'email_user': 'example@gmai.com',
            'email_pass': 'password',
            'base_dir': 'Your Base Directory',
            'senders_dict': {
                'example1@example.com': 'Example Sender 1',
                'example2@example.com': 'Example Sender 2',
            }
        },
        {
            'email_user': 'example2@gmail.com',
            'email_pass': 'password',
            'base_dir':   'BASE_DIR_2',
            'senders_dict': {
                'example3@example.com': 'Example Sender 3',
                'example4@example.com': 'Example Sender 4',
            }
        }
    ]

    for account in email_accounts:
        downloader = EmailDownloader(
            email_user=account['email_user'],
            email_pass=account['email_pass'],
            base_dir=account['base_dir'],
            senders_dict=account['senders_dict']
        )

        downloader.connect()
        downloader.create_attachments_directory()

        if downloader.attachments_dir:  
            downloader.download_attachments()

        downloader.logout()  

if __name__ == '__main__':
    main()
