import time
import requests
import sqlite3
import os
from SubFolder import dist_id, browser_header
from dateutil.parser import parse
from datetime import date as dt

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
    """ Checks database if center is present; Updates if present.
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
    exist = conn.execute("select * from center where center_id = ? and age_limit = ? and date = ?;",
                         (center["center_id"], center["min_age_limit"], center["date"])).fetchone()
    if not exist:
        # send a message when more than 10 vaccines are available
        if center["available_capacity"] >= 10:
            msg_id = send_new_msg(center, txt)
            print("Doesn't exist in DB.Inserting into DB")
            insert_into_db(center, msg_id, conn)
            print("Inserted into DB")

        else:
            print("Less than 10 V's. No message sent. No insertion into DB.")

        flag_exists = False
    else:
        flag_exists = True
        print("Exists. Updating DB.")
        time_ = time.strftime("%H:%M:%S", time.localtime())
        # if message sent but less than 10 available
        if exist[11] == 'Y' and center["available_capacity"] < 10:
            # sets msg_sent to N, sends final message saying less than 10 vaccines available.
            conn.execute("UPDATE center SET vaccine = ?, fee = ?, capacity = ?, time = ?, "
                         "sent = ? where center_id = ? and age_limit = ?;", (center["vaccine"], center["fee"],
                                                                             center["available_capacity"], time_,
                                                                             'N', center["center_id"],
                                                                             center["min_age_limit"]))
            txt = f'Less than 10 vaccines left'
            replyto_msg(txt, exist[10])

        # if message not sent.
        elif exist[11] == 'N':
            # Sets sent msg to Y and updates other columns if more than 10 vaccines available
            if center["available_capacity"] >= 10:
                msg_id = send_new_msg(center, txt)
                conn.execute("UPDATE center SET vaccine = ?, fee = ?, capacity = ?, time = ?, "
                             "sent = ?, msg_id = ? where center_id = ? and age_limit = ?;",
                             (center["vaccine"], center["fee"], center["available_capacity"], time_, 'Y', msg_id,
                              center["center_id"], center["min_age_limit"]))
            else:
                print("Less than 10 V's. No message sent; No updations.")

        # if message sent
        elif exist[11] == 'Y':
            # updates date, vaccines, fee, capacity, age
            conn.execute("UPDATE center SET vaccine = ?, fee = ?, capacity = ?, time = ?, "
                         "sent = ? where center_id = ? and age_limit = ?;",
                         (center["vaccine"], center["fee"], center["available_capacity"], time_, 'Y',
                          center["center_id"], center["min_age_limit"]))

        conn.commit()
        print("Updated DB.")
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
        half_hour_check = current_time + 1800  # current time + 1/2 an hour
        conn = sqlite3.connect(database)
        ligne_centers = []
        ligne_dates = []
        exist = conn.execute("select * from center where sent = ?;", ('Y',)).fetchall()
        if not exist:
            # No centers where sent_msg == 'Y'. Exit method.
            print("Empty query")
            return
        for row in exist:
            print("DB cleaning.")
            # DB returned centers being appended to a list
            ligne_centers.append(list(row))
            if row[0] not in ligne_dates:
                # Unique dates of the centers being appended to a list
                ligne_dates.append(row[0])
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
                    '''
                    What the next loop does:
                    For all the centers, check if the data still holds True. If it doesn't, update the DB.
                    As each center is checked, remove it from the list 'ligne_center'.
                    '''
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
                            Checks the center_id (along with age limit) and tries to get a match with the center_id of 
                            the center from DB. If slots are same, no changes required. Else update the DB, 
                            send final msg.
                            """
                            center_id = center[1]
                            slots = center[8]
                            msg_id = center[10]
                            j = 0
                            while j < len(resp_cen):  # looping through API result to get the center
                                if resp_cen[j].get("center_id") == center[1] and \
                                        resp_cen[j].get("min_age_limit") == center[5] and \
                                        resp_cen[j].get("date") == center[0]:  # if center_id, age limit and date match

                                    if resp_cen[j].get("available_capacity") == slots or \
                                            resp_cen[j].get("available_capacity") >= 1:
                                        # If slots are still available, no changes to be made
                                        print(f"Data intergrety good for {resp_cen[j].get('name')}")
                                        ligne_centers.pop(i)
                                        resp_cen.pop(j)
                                        break
                                    else:
                                        # If slots are mismatched, ie not available status - then,
                                        # set fee & capacity = 0, sent to 'N'.
                                        time_ = time.strftime("%H:%M:%S", time.localtime())
                                        conn.execute(
                                            "UPDATE center SET fee = ?, capacity = ?, time = ?, sent = ? where "
                                            "center_id = ?;", (0, 0, time_, 'N', center_id))
                                        conn.commit()
                                        txt = "Vaccines for this center is no longer available."
                                        replyto_msg(txt, msg_id)
                                        ligne_centers.pop(i)
                                        resp_cen.pop(j)
                                        break
                                else:
                                    j += 1  # increment loop
                        i += 1

                    # if centers aren't in the API response the following gets executed. This is important to update the
                    # DB. Again, sometimes centers just dissapear off the API result.
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
                        replyto_msg(txt, msg_id)
                        ligne_centers.pop(k)
                        continue
        # cleaning DB where the dates are yesterdays
        exist = conn.execute("select * from center").fetchone()
        if not exist:
            print("Clean DB")
        else:
            today = dt.today().strftime('%d-%m-%Y')
            if parse(exist[0]) < parse(today):
                conn.execute("DELETE from center WHERE date = ?;", (exist[0],))
                conn.commit()
        conn.close()
        print("DB cleaning over.")


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


def send_new_msg(center, txt):
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


def replyto_msg(txt, msg_id):
    """Can be either update or last final message for a center.

    Sent when 1. Age limit has been changed or
              2. Vaccines <= 10 or
              3. When vaccines no longer available.

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
