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
            "template": "A1YMTTEFBE4F7AHNT2Y4AT3HS4JK",
            "data": {
                "code": f"{code}",
            },
            "routing": {
                "method": "single",
                "channels": ["email"],
            },
        }
    )
