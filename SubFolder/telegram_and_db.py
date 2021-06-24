import time
import requests
import sqlite3
import os
from SubFolder import dist_id, browser_header

global token
global chat_id
half_hour_check = time.time() + 1830  # used to check database for cleaning. Refer to check_in_db() docum for more.

basedir = os.path.dirname(os.path.abspath(__file__))
database = basedir + '\\centers.db'


def telegram_required():
    """Gets details of the telegram group and calls creates DB method.

    Get your token from botfather on Telegram and figure out the chat_id. Read Telegram Api Documentation for more on
    that. Save them in a txt file 'keys' in consecutive lines.
    Parameters:
    -----------
    token (string): Token of the Bot. Recieved from BotFather
    chat_id (string): Chat ID of the group.


    """
    global token
    global chat_id
    with open('SubFolder/keys.txt', 'r') as file:
        token = file.readline().strip('\n')
        chat_id = file.readline()

    create_db()


def create_db():
    """Creates a database in root directory.
    Creates a table 'center' if it doesn't exist with the following paramaters:

    Attributes:
    -----------
       date (text) : For when slots are available.
       center_id (real): Center ID
       name (text): Name of Center
       block_name (text): Block name of center
       pin (real): Pincode of center
       age_limit (real): Minimum age
       vaccine (text): Which Vaccine
       fee (real): Fee
       capacity (real): No. of slots
       time (text): Time when center was lasted updated/inserted into DB
       msg_id (real): Message ID of the Telegram message sent
       sent (text): If vaccines A. Sent and B. More than 10, then 'Y', else 'N'
    """

    con = sqlite3.connect(database)
    cur = con.cursor()
    # Create table
    table_create = '''CREATE TABLE IF NOT EXISTS center
                   (date text,
                   center_id real,
                   name text ,
                   block_name text,
                   pin real, 
                   age_limit real, 
                   vaccine text, 
                   fee real,
                   capacity real, 
                   time text, 
                   msg_id real,
                   sent text);'''
    cur.execute(table_create)
    print("Table created")
    con.close()


def check_in_db(center, txt):
    """ Checks database if center is present; Updates if present, inserts if not.
    Args:
    ----------
    'center'[JSON] has the details of the current center passed
    'txt'[str] is the message text to be sent


    Attributes:
    -----------
     'flag_exists' keeps track of center is in DB. Currently not used.
     'msg_id' (real): Message ID of the Telegram message sent
     'time_' (string) : Time when center was updated/inserted into DB
    """

    flag_exists = False
    msg_id = None
    conn = sqlite3.connect(database)
    exist = conn.execute("select * from center where center_id = ?;", (center["center_id"],)).fetchone()
    if exist is None:
        # send a message when more than 10 vaccines are available
        if center["available_capacity"] >= 10:
            msg_id = send_new_msg(center, txt)
            print("Doesn't exist in DB.Inserting into DB")
            insert_into_db(center, msg_id, conn)
            print("Inserted into DB")

        else:
            print("Less than 10 V's. No message sent.")

        flag_exists = False
    else:
        flag_exists = True
        print("Exists. Updating DB.")
        time_ = time.strftime("%H:%M:%S", time.localtime())
        # if message sent but less than 10 available
        if exist[11] == 'Y' and center["available_capacity"] < 10:
            # sets msg_sent to N, sends final message saying less than 10 vaccines available.
            conn.execute("UPDATE center SET date = ?, vaccine = ?, fee = ?, capacity = ?, time = ?, age_limit = ?, "
                         "sent = ? where center_id = ?;", (center["date"], center["vaccine"], center["fee"],
                                                           center["available_capacity"], time_, center["min_age_limit"],
                                                           'N', center["center_id"]))
            txt = f'Less than 10 vaccines left'
            final_msg(txt, exist[10])

        # if message sent
        elif exist[11] == 'Y':
            # updates date, vaccines, fee, capacity, age
            conn.execute("UPDATE center SET date = ?, vaccine = ?, fee = ?, capacity = ?, time = ?, age_limit = ?, "
                         "sent = ? where center_id = ?;", (center["date"], center["vaccine"], center["fee"],
                                                           center["available_capacity"], time_, center["min_age_limit"],
                                                           'Y', center["center_id"]))
        # if message not sent.
        elif exist[11] == 'N':
            # Sets sent msg to Y and updates other columns if more than 10 vaccines available
            if center["available_capacity"] >= 10:
                msg_id = send_new_msg(txt, center)
                conn.execute("UPDATE center SET date = ?, vaccine = ?, fee = ?, capacity = ?, time = ?, age_limit = ?, "
                             "sent = ?, msg_id = ? where center_id = ?;", (center["date"], center["vaccine"],
                                                                           center["fee"], center["available_capacity"],
                                                                           time_, center["min_age_limit"], 'Y', msg_id,
                                                                           center["center_id"]))
            else:
                print("Less than 10 V's. No message sent; No updations")
        conn.commit()
        print("Updated DB.")

    #  The following is used to check the database every 30 minutes. Check cleaning_db() docum for more.

    conn.close()


def cleaning_db():
    """Cleans DB because of issues such as caching, removal of centers without reaching less than 10 vaccines etc. Runs
    only every half an hour.

    Sometimes, center's just disappear and that needs to be cleaned up. This disappearing can be due to cache issues or
    some other arbitrary reason.
    This method takes all the centers in DB where sent_msg == 'Y' and checks for data integrity.
    This part of the program is pretty complicated. Here is gist of what happens.
    First, take all the centers in the DB where 'sent_msg' = Y. One by them, put them in a list.
    Also put unique dates in another list as different centers has different dates of slots.
    Now, for each date, send a request to COWIN using API and cross check slot capacity set in DB with that in the API.
    ---
    Parameters:
    ----------
    ligne stands for row in French.
    'ligne_centers' is for centers in DB which has 'sent_msg' to 'Y'
    'ligne_dates' is for unique dates.
    :return: Empty if No centers where sent_msg == 'Y'
    """
    global half_hour_check
    current_time = time.time()  # get current time
    print(f"Time: {current_time}, {half_hour_check}")
    if current_time > half_hour_check:
        current_time = time.time()
        half_hour_check = current_time + 1800  # current + 1/2 an hour
        conn = sqlite3.connect(database)
        ligne_centers = []
        ligne_dates = []
        exist = conn.execute("select * from center where sent = ?;", ('Y',)).fetchall()
        if not exist:
            # No centers where sent_msg == 'Y'. Exit method.
            return 'Empty query.'
        for row in exist:
            # DB returned centers being appended to a list
            ligne_centers.append(list(row))
            if row[0] not in ligne_dates:
                # Unique dates of the centers being appended to a list
                ligne_dates.extend(row[0])
        for date in ligne_dates:
            # for each date, get the response.
            try:
                url = f"https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/findByDistrict?district_id=" \
                      f"{dist_id}&date={date}"
                response = requests.get(url, headers=browser_header)
                response.raise_for_status()
            except requests.exceptions.HTTPError as errh:
                print("Http Error_2:", errh)
            except requests.exceptions.ConnectionError as errc:
                print("Error Connecting_2:", errc)
            except requests.exceptions.Timeout as errt:
                print("Timeout Error_2:", errt)
            except requests.exceptions.RequestException as err:
                print("Oops: Something Else_2", err)
            else:
                if response.ok:
                    # response has data
                    resp_json = response.json()
                    resp_cen = resp_json["sessions"]
                    i = 0
                    while i < len(ligne_centers):
                        center = ligne_centers[i]
                        # for each center in db
                        if center[0] != date:
                            # Center isn't giving slots on said date? Then just continue and check next center.
                            continue
                        else:
                            """
                            Here, the first for loop goes through all the centers received with the COWIN API.
                            Checks the center_id and tries to get a match with the center_id of the center from DB.
                            If slots are same, no changes required. Else update the DB, send final msg.
                            """
                            center_id = center[1]
                            slots = center[8]
                            msg_id = center[10]
                            j = 0
                            while j < len(resp_cen):
                                if resp_cen[j].get("center_id") == center[1]:
                                    if resp_cen[j].get("available_capacity") == slots:
                                        # If slots are equal, no changes to be made
                                        print(f"Data intergrety good for {resp_cen[j].get('name')}")
                                        ligne_centers.pop(i)
                                        resp_cen.pop(j)
                                        continue
                                    else:
                                        # If slots are mismatched, set fee & capacity = 0, sent to 'N'.
                                        time_ = time.strftime("%H:%M:%S", time.localtime())
                                        conn.execute(
                                            "UPDATE center SET fee = ?, capacity = ?, time = ?, sent = ? where "
                                            "center_id = ?;", (0, 0, time_, 'N', center_id))
                                        conn.commit()
                                        txt = "Vaccines for this center is no longer available."
                                        final_msg(txt, msg_id)
                                        ligne_centers.pop(i)
                                        resp_cen.pop(j)
                                        continue
                                else:
                                    j += 1  # increment loop
                        i += 1

                    # if centers aren't in the API response the following gets executed. This is important to update the
                    # DB.
                    k = 0
                    while k < len(ligne_centers):
                        center = ligne_centers[k]
                        center_id = center[1]
                        msg_id = center[10]
                        time_ = time.strftime("%H:%M:%S", time.localtime())
                        conn.execute(
                            "UPDATE center SET fee = ?, capacity = ?, time = ?, sent = ? where "
                            "center_id = ?;", (0, 0, time_, 'N', center_id))
                        conn.commit()
                        txt = "Vaccines for this center is no longer available."
                        final_msg(txt, msg_id)
                        ligne_centers.pop(k)
                        continue
        conn.close()


def insert_into_db(center, msg_id, conn):
    """Inserts a new center into DB

    Parameters:
    -----------
    :param center: Json string. Has details of a particular center
    :param msg_id: Message ID of the telegram message sent
    :param conn: Connection object passed so as to not open/close new ones.
    :return: Nothing

    Attributes:
    -----------
    'time_' (string) : Time when center was inserted into DB
    """
    time_ = time.strftime("%H:%M:%S", time.localtime())
    val = (center["date"], center["center_id"], center["name"], center["block_name"], center["pincode"],
           center["min_age_limit"], center["vaccine"], center["fee"], center["available_capacity"], time_, msg_id, 'Y')

    conn.execute('INSERT INTO center (date, center_id, name, block_name,pin,age_limit,vaccine,fee,capacity,time,msg_id,'
                 'sent) VALUES (?,?,?,?,?,?,?,?,?,?,?,?);', val)
    conn.commit()


def send_new_msg(txt, center):
    """Sends a new message to the Telegram Group
    Sends text message when availability of vaccine >= 10
    Parameters:
    -----------
    :param center: Json string. Has details of a particular center. Not currently used.
    :param txt: Text that to be sent
    :return: Message ID of the message sent
    """

    #    if center["available_capacity"] >= 10:
    to_url = 'https://api.telegram.org/bot{}/sendMessage?chat_id={}&text={}&parse_mode=HTML'.format(token, chat_id, txt)
    try:
        resp = requests.get(to_url)
    except Exception:  # too broad, yes
        print("Telegram message have not been sent\n")
    else:
        print("Telegram message have been sent\n")
        json = resp.json()
        message_id = json["result"]["message_id"]
        return message_id


def final_msg(txt, msg_id):
    """Last final message for a center. Sent when Vaccines <= 10 or when vaccines no longer available.

    Paramets:
    ---------
    :param txt: Text to be sent
    :param msg_id: Message ID of the original message so as to reply to that message.
    """

    to_url = 'https://api.telegram.org/bot{}/sendMessage?chat_id={}&text={}&reply_to_message_id={}&parse_mode=' \
             'HTML'.format(token, chat_id, txt, msg_id)
    try:
        resp = requests.get(to_url)
    except Exception:  # too broad, yes
        print("Telegram message have not been sent\n")
    else:
        print("Telegram message have been sent\n")
        json = resp.json()
        message_id = json["result"]["message_id"]
        return message_id
