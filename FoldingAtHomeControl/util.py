import json
import random
import string


def json_dump_payload(payload: dict) -> str:
    return json.dumps(payload).replace(" ", "")


def get_random_chars(num: int) -> str:
    return "".join(
        random.SystemRandom().choice(string.ascii_uppercase + string.digits)
        for _ in range(num)
    )
