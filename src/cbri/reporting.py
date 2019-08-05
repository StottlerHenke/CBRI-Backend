import smtplib
import logging
import datetime
from email.mime.text import MIMEText

from cbri.version import get_version
from cbri.settings import CBRI_EMAIL, CBRI_PASSWORD, CBRI_SMTP, CBRI_FRONT_END, config_file_dir

"""
Responsible for notifying the user via logging and email.
"""

# Get an instance of a logger
logger = logging.getLogger('cbri')
logger.info(get_version())
logger.info("Using config file: " + config_file_dir)


def log_to_repo(repo, log_msg : str, exception=False):
    """Log repo-specific information to the repo itself for console-style reporting"""
    if exception:
        logger.exception(log_msg)
    else:
        logger.info(log_msg)

    date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    repo.log = repo.log + "\n" + date_str + log_msg
    repo.save()


class UserNotification:
    """ Send the user an email when certain events occur """

    def __init__(self):
        self.server = None

    def create_server(self):
        """ Create a connection to the server. Be sure to shutdown when finished. """
        try:
            self.server = smtplib.SMTP_SSL(CBRI_SMTP, 465)
            self.server.ehlo()
        except Exception as err:
            raise RuntimeError("Unable to connect to SMTP: " + CBRI_SMTP + " Port: " + str(465))

        try:
            self.server.login(CBRI_EMAIL, CBRI_PASSWORD)
        except Exception as err:
            raise RuntimeError("Unable to login to SMTP for CBRI admin: " + CBRI_EMAIL + " " + str(err))

    def close_server(self):
        if(self.server):
            self.server.close()

    def send_repo_create_failed_email(self, recipient: str, project_name: str, error: str):
        """ Send an email to the given user that repo has been updated """

        msg = "The initial repository failed to be created for " + project_name + \
              " due to: " + error
        self.send_email("CBRI", recipient, "CBRI: ERROR - Failed to create repository", msg)
        logger.warning("Repository create failed email sent to: " + recipient + " " + project_name + ": " + msg)


    def send_repo_create_email(self, recipient: str, project_name: str, project_id: str):
        """ Send an email to the given user that repo has been updated """

        msg = "The initial repository has been created for " + project_name + \
              " and can be found at: " + CBRI_FRONT_END + "/project/" + project_id
        self.send_email("CBRI", recipient, "CBRI: Repository created", msg)
        logger.info("Repository create email sent to: " + recipient + " " + project_name + ": " + msg)


    def send_repo_update_failed_email(self, recipient: str, project_name: str, error: str):
        """ Send an email to the given user that repo has been updated """

        msg = "The repository " + project_name + \
              " failed to be updated due to: " + error
        self.send_email("CBRI", recipient, "CBRI: ERROR - Failed to update repository", msg)
        logger.warning("Repository update failed email sent to: " + recipient + " " + project_name + ": " + msg)


    def send_repo_update_email(self, recipient: str, project_name: str, project_id: str):
        """ Send an email to the given user that repo has been updated """

        msg = "The repository " + project_name + \
              " has been updated and can be found at: " + CBRI_FRONT_END + "/project/" + project_id
        self.send_email("CBRI", recipient, "CBRI: Repository updated", msg)
        logger.info("Repository update email sent to: " + recipient + " " + project_name + ": " + msg)


    def send_email(self, sender: str, recipient: str, subject: str, message: str ):
        """ Construct and send an email """
        # Construct a message
        msg = MIMEText(message)
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = recipient

        # Send the message via the given SMTP server.
        cached_error = None
        try:
            self.create_server()
            self.server.send_message(msg)
        except RuntimeError as err:
            cached_error = err
        finally:
            self.close_server()

        if cached_error:
            raise cached_error