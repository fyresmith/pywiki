from trycourier import Courier
import os
from dotenv import load_dotenv

load_dotenv()


def send_message(first, last, email_address, message):
    client = Courier(auth_token=os.getenv('COURIER_API_TOKEN'))

    resp = client.send_message(
        message={
            "to": {
                "email": os.getenv('OPERATOR_ADDRESS'),
            },
            "template": os.getenv('SEND_EMAIL_TEMPLATE_ID'),
            "data": {
                "first": f"{first}",
                "last": f"{last}",
                "emailAddress": f"{email_address}",
                "message": f"{message}",
            },
            "routing": {
                "method": "single",
                "channels": ["email"],
            },
        }
    )

    return resp


def send_email(address: str, code: str):
    client = Courier(auth_token=os.getenv('COURIER_API_TOKEN'))

    resp = client.send_message(
        message={
            "to": {
                "email": f"{address}",
            },
            "template": os.getenv('COURIER_TEMPLATE_ID'),
            "data": {
                "code": f"{code}",
            },
            "routing": {
                "method": "single",
                "channels": ["email"],
            },
        }
    )

    return resp
