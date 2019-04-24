import django

from cbri.reporting import UserNotification

class ReportingTest(django.test.TestCase):
    """ Test sending an email """

    def test_send_email(self):
        self.assertTrue(False) #Fix the information below to run the test
        address = 'changeme@somewhere.com'
        print('Sending email to: ' + address + ". This takes awhile.")
        un = UserNotification();
        un.send_email('CBRI', address, 'a subject', 'a message')
        print('Email sent')