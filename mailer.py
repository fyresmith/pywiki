from trycourier import Courier


def send_email(address: str, code: str):
    client = Courier(auth_token="pk_prod_5S9QWJR497MV11GYQWBCGC5Y8K9H")

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
