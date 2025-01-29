from dotenv import dotenv_values

# Esto debe ser corrido desde la raíz
config = dotenv_values(".env")  # config = {"USER": "foo", "EMAIL": "foo@example.org"}
print (config)
# import sendgrid
# import os
# from sendgrid.helpers.mail import *

# sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API)
# from_email = Email("francisco@soyfocus.com")
# to_email = To("francisco@soyfocus.com")
# subject = "Sending with SendGrid is Fun"
# content = Content("text/plain", "and easy to do anywhere, even with Python")
# mail = Mail(from_email, to_email, subject, content)
# response = sg.client.mail.send.post(request_body=mail.get())
# print(response.status_code)
# print(response.body)
# print(response.headers)