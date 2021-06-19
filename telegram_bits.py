import requests

global token
global chat_id


def telegram_required():
    global token
    global chat_id
    #  IMP
    #  get your token from botfather on Telegram and figure out the chat_id (Can be by sending a message in the created
    #  group and looking at the https://api.telegram.org/bot{token}/getUpdates page. Save them in a txt file 'keys' in
    #  consecutive lines
    with open('keys.txt', 'r') as file:
        token = file.readline().strip('\n')
        chat_id = file.readline()


def send_new_msg(txt, center):
    # Sending text message when availability of vaccine >= 10
    if center["available_capacity"] >= 10:
        to_url = 'https://api.telegram.org/bot{}/sendMessage?chat_id={}&text={}&parse_mode=HTML'. \
            format(token, chat_id, txt)
        try:
            resp = requests.get(to_url)
        except Exception:  # too broad, yes
            print("Telegram message have not been sent")
        else:
            print("Telegram message have been sent")
            json = resp.json()
            message_id = json["result"]["message_id"]
            return message_id
