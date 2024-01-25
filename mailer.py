from trycourier import Courier
import os
from dotenv import load_dotenv

load_dotenv()


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
