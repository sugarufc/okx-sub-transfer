import os
import time
import hmac
import hashlib
import base64
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone
import json

# Цвета терминала
RED = '\033[91m'
GREEN = '\033[92m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'

load_dotenv()

API_KEY = os.getenv("OKX_API_KEY")
API_SECRET = os.getenv("OKX_API_SECRET")
PASSPHRASE = os.getenv("OKX_PASSPHRASE")
BASE_URL = 'https://www.okx.com'
LOG_FILE = "transfers.log"


def get_timestamp():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def sign(message, secret_key):
    return base64.b64encode(
        hmac.new(secret_key.encode(), message.encode(),
                 hashlib.sha256).digest()
    ).decode()


def headers(method, endpoint, body=''):
    timestamp = get_timestamp()
    message = f'{timestamp}{method}{endpoint}{body}'
    signature = sign(message, API_SECRET)
    return {
        'OK-ACCESS-KEY': API_KEY,
        'OK-ACCESS-SIGN': signature,
        'OK-ACCESS-TIMESTAMP': timestamp,
        'OK-ACCESS-PASSPHRASE': PASSPHRASE,
        'Content-Type': 'application/json'
    }


def get_sub_accounts():
    url = '/api/v5/users/subaccount/list'
    r = requests.get(BASE_URL + url, headers=headers('GET', url))
    return r.json().get('data', [])


def get_all_balances(sub_uid):
    url = f'/api/v5/asset/subaccount/balances?subAcct={sub_uid}'
    r = requests.get(BASE_URL + url, headers=headers('GET', url))
    return r.json().get('data', [])


def transfer_to_main(sub_uid, currency, amount):
    url = '/api/v5/asset/transfer'
    data = {
        "ccy": currency,
        "amt": amount,
        "from": "6",
        "to": "6",
        "subAcct": sub_uid,
        "type": "2"
    }
    json_data = json.dumps(data)
    r = requests.post(BASE_URL + url, headers=headers('POST',
                      url, json_data), data=json_data)
    return r.json()


def log_transfer(message):
    with open(LOG_FILE, "a") as log:
        log.write(f"{datetime.now().isoformat()} | {message}\n")


def main():
    subs = get_sub_accounts()
    # print(f"[DEBUG] Subaccounts: {[sub['subAcct'] for sub in subs]}")

    for sub in subs:
        sub_uid = sub['subAcct']
        balances = get_all_balances(sub_uid)

        has_transfer = False

        for asset in balances:
            try:
                currency = asset['ccy']
                balance = float(asset['bal'])
                if balance > 0:
                    has_transfer = True
                    print(
                        f"{GREEN}[INFO] Transferring {balance} {currency} from {sub_uid}{RESET}")
                    result = transfer_to_main(sub_uid, currency, str(balance))
                    log_transfer(
                        f"Transferred {balance} {currency} from {sub_uid} | Result: {result}")
                    if result.get('code') == '0':
                        tx_data = result['data'][0]
                        print(
                            f"{BLUE}[✅] Transfer {tx_data['amt']} {tx_data['ccy']} from {sub_uid} — SUCCESS {RESET}")
                    else:
                        print(
                            f"{RED}[ERROR] Ошибка при переводе с {sub_uid}: {result}{RESET}")

            except Exception as e:
                error_message = f"[ERROR] Failed to transfer {asset.get('ccy', '')} from {sub_uid}: {e}"
                log_transfer(error_message)
                print(f"{RED}{BOLD}{error_message}{RESET}")

        if not has_transfer:
            msg = f"[EMPTY] No transferable assets in {sub_uid}"
            print(f"{RED}{msg}{RESET}")
            log_transfer(msg)


if __name__ == "__main__":
    main()
