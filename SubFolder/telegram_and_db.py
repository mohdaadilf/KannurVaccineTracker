import sqlite3
from time import time, strftime, localtime
from requests import get
from requests.exceptions import ConnectionError, Timeout, RequestException, HTTPError
from sqlite3 import connect
from SubFolder import dist_id, browser_header
from dateutil.parser import parse
from datetime import date as dt
from os.path import dirname, abspath

global token
global chat_id
half_hour_check = time()  # used to check database for cleaning. Refer to check_in_db() docum for more.

basedir = dirname(abspath(__file__))
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

    con = connect(database)
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


def check_in_db(center: dict, txt: str):
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
    conn = connect(database)
    exist = conn.execute("select * from center where center_id = ? and age_limit = ? and vaccine = ? and date = ?;",
                         (center["center_id"], center["min_age_limit"], center["vaccine"], center["date"])).fetchone()
    if not exist:
        # send a message when more than 10 vaccines are available
        if center["available_capacity"] >= 10:
            msg_id = send_new_msg(txt)
            print("Doesn't exist in DB.Inserting into DB")
            insert_into_db(center, msg_id, conn)
            print("Inserted into DB")

        else:
            print("Less than 10 V's. No message sent. No insertion into DB.")
    else:
        print("Exists. Updating DB.")
        time_ = strftime("%H:%M:%S", localtime())
        # if message sent but less than 10 available
        if exist[11] == 'Y' and center["available_capacity"] < 10:
            # sets msg_sent to N, sends final message saying less than 10 vaccines available.
            conn.execute("UPDATE center SET fee = ?, capacity = ?, time = ?, "
                         "sent = ? where center_id = ? and age_limit = ? and date = ?;", (center["fee"],
                                                                                          center["available_capacity"],
                                                                                          time_, 'N',
                                                                                          center["center_id"],
                                                                                          center["min_age_limit"],
                                                                                          center["date"]))
            txt = f'Less than 10 vaccines left for {center["name"]}'
            replyto_msg(txt, exist[10])

        # if message not sent.
        elif exist[11] == 'N':
            # Sets sent msg to Y and updates other columns if more than 10 vaccines available
            if center["available_capacity"] >= 10:
                msg_id = send_new_msg(txt)
                conn.execute("UPDATE center SET fee = ?, capacity = ?, time = ?, "
                             "sent = ?, msg_id = ? where center_id = ? and age_limit = ? and date = ?;",
                             (center["fee"], center["available_capacity"], time_, 'Y', msg_id,
                              center["center_id"], center["min_age_limit"], center["date"]))
            else:
                print("Less than 10 V's. No message sent; No updations.")

        # if message sent
        elif exist[11] == 'Y':
            # updates date, vaccines, fee, capacity, age
            conn.execute("UPDATE center SET fee = ?, capacity = ?, time = ?, "
                         "sent = ? where center_id = ? and age_limit = ? and date = ?;",
                         (center["fee"], center["available_capacity"], time_, 'Y',
                          center["center_id"], center["min_age_limit"], center["date"]))

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
    'ligne_centers' is for centers in DB which has 'sent_msg' as 'Y'
    'ligne_dates' is for unique dates.
    :return: Empty if No centers where sent_msg == 'Y'
    """
    global half_hour_check
    current_time = time()  # get current time
    print(f"Time: {current_time}, {half_hour_check}")
    if current_time > half_hour_check:
        current_time = time()
        half_hour_check = current_time + 1800  # current time + 1/2 an hour
        conn = connect(database)
        ligne_centers = []
        ligne_dates = []
        exist = conn.execute("select * from center where sent = ?;", ('Y',)).fetchall()
        if not exist:
            # No centers where sent_msg == 'Y'. Exit method.
            print("Empty query")
            return
        for row in exist:
            print(f"DB cleaning. {row}")
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
                response = get(url, headers=browser_header)
                response.raise_for_status()
            except HTTPError as errh:
                print("Http Error_2:", errh)
                print(errh.response.text)
            except ConnectionError as errc:
                print("Error Connecting_2:", errc)
            except Timeout as errt:
                print("Timeout Error_2:", errt)
            except RequestException as err:
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
                        flag_exists = False
                        # for each center in db
                        if center[0] != date:
                            # Center isn't giving slots on said date? Then just continue and check next center.
                            i += 1
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
                            vacc = center[6]
                            j = 0
                            while j < len(resp_cen):  # looping through API result to get the center
                                api_center = resp_cen[j].get("center_id")
                                api_age = resp_cen[j].get("min_age_limit")
                                api_date = resp_cen[j].get("date")
                                api_vaccine = resp_cen[j].get("vaccine")
                                if api_center == center[1] and api_age == center[5] and api_date == center[0] and \
                                        api_vaccine == vacc:
                                    # if center_id, age limit and date match
                                    api_slots = resp_cen[j].get("available_capacity")
                                    if api_slots == slots or api_slots >= 1:
                                        # If slots are still available, no changes to be made
                                        print(f"Data intergrety good for {resp_cen[j].get('name')}")
                                        ligne_centers.pop(i)
                                        resp_cen.pop(j)
                                        flag_exists = True
                                        break
                                    else:
                                        # If slots are mismatched, ie not available status - then,
                                        # set fee & capacity = 0, sent to 'N'.
                                        print("API result missmatch")
                                        time_ = strftime("%H:%M:%S", localtime())
                                        conn.execute("UPDATE center SET fee = ?, capacity = ?, time = ?, sent = ? "
                                                     "where center_id = ? and age_limit = ? and date = ?;", (0, 0,
                                                                                                             time_,
                                                                                                             'N',
                                                                                                             center_id,
                                                                                                             api_age,
                                                                                                             date))
                                        conn.commit()
                                        txt = f"Vaccines for center {center[2]} is no longer available."
                                        replyto_msg(txt, msg_id)
                                        ligne_centers.pop(i)
                                        resp_cen.pop(j)
                                        flag_exists = True
                                        break
                                else:
                                    j += 1  # increment loop
                        if flag_exists is False:
                            i += 1

        # If centers aren't in the API response the following gets executed. Again, sometimes centers just dissapear off
        # the API result. The following is important to update the DB.
        k = 0
        while k < len(ligne_centers):
            print("Not in API result")
            center = ligne_centers[k]
            center_id = center[1]
            msg_id = center[10]
            time_ = strftime("%H:%M:%S", localtime())
            conn.execute(
                "UPDATE center SET fee = ?, capacity = ?, time = ?, sent = ? where "
                "center_id = ?;", (0, 0, time_, 'N', center_id))
            conn.commit()
            txt = f"Vaccines for center {center[2]} is no longer available."
            replyto_msg(txt, msg_id)
            ligne_centers.pop(k)
            continue

        # cleaning DB where the dates are yesterdays
        exist = conn.execute("select * from center").fetchall()
        if not exist:
            print("Clean DB")
        else:
            #  This section can be improved.
            today = dt.today().strftime('%d-%m-%Y')
            yest_parsed = parse(exist[0][0])
            date = exist[0][0]
            toda_parsed = parse(today)
            if yest_parsed < toda_parsed:
                conn.execute("DELETE from center WHERE date = ?;", (date,))
                conn.commit()
        conn.close()
        print("DB cleaning over.")


def insert_into_db(center: dict, msg_id: int, conn: sqlite3.Connection):
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
    time_ = strftime("%H:%M:%S", localtime())
    val = (center["date"], center["center_id"], center["name"], center["block_name"], center["pincode"],
           center["min_age_limit"], center["vaccine"], center["fee"], center["available_capacity"], time_, msg_id, 'Y')

    conn.execute('INSERT INTO center (date, center_id, name, block_name,pin,age_limit,vaccine,fee,capacity,time,msg_id,'
                 'sent) VALUES (?,?,?,?,?,?,?,?,?,?,?,?);', val)
    conn.commit()


def send_new_msg(txt: str) -> int:
    """Sends a new message to the Telegram Group
    Sends text message when availability of vaccine >= 10
    Parameters:
    -----------
    :param txt: Text that to be sent
    :return: Message ID of the message sent
    """

    message_id = None
    to_url = 'https://api.telegram.org/bot{}/sendMessage?chat_id={}&text={}&parse_mode=HTML'.format(token, chat_id, txt)
    try:
        resp = get(to_url)
        print("Telegram message have been sent\n")
        json = resp.json()
        message_id = json["result"]["message_id"]
    except ConnectionError as e:
        print(f'Connection error: {e}')
        print("Telegram message have not been sent.")
    except Timeout as e:
        print(f'Timeout error {e}')
        print("Telegram message have not been sent.")
    except RequestException as err:
        print("Oops: Something Else", err)
        print("Telegram message have not been sent.")
    except KeyError as e:
        print(f'Key error {e}')
    finally:
        return message_id


def replyto_msg(txt: str, msg_id: int) -> int:
    """Can be either update or last final message for a center.

    Sent when 1. Age limit has been changed or
              2. Vaccines <= 10 or
              3. When vaccines no longer available.

    Paramets:
    ---------
    :param txt: Text to be sent
    :param msg_id: Message ID of the original message so as to reply to that message.
    """
    message_id = None
    to_url = 'https://api.telegram.org/bot{}/sendMessage?chat_id={}&text={}&reply_to_message_id={}&parse_mode=' \
             'HTML'.format(token, chat_id, txt, msg_id)
    try:
        resp = get(to_url)
        print("Telegram message have been sent.")
        json = resp.json()
        message_id = json["result"]["message_id"]
    except ConnectionError as e:
        print(f'Connection error: {e}')
        print("Telegram message have not been sent.")
    except Timeout as e:
        print(f'Timeout error {e}')
        print("Telegram message have not been sent.")
    except RequestException as err:
        print("Oops: Something Else", err)
        print("Telegram message have not been sent.")
    except KeyError as e:
        print(f'Key error {e}')
    finally:
        return message_id
