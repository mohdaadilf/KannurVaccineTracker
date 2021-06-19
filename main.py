import requests
import datetime
import time
from requests import exceptions
from telegram_bits import telegram_required, send_new_msg, check_sent
import csv
import shutil

def cowin_required():
    global age
    global numdays
    global dist_id
    global browser_header

    # max age
    age = 45

    # Number of days to check ahead
    numdays = 3

    # district ID

    dist_id = "297"

    # header required due to changes to API
    # header = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko)'
    #               'Chrome/39.0.2171.95 Safari/537.36'}
    browser_header = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                    'Chrome/56.0.2924.76 Safari/537.36', 'Cache-Control': 'no-cache'}


def main_loop():
    #  for i in range(2):
    # For timing the loop
    i = 0
    loop_starts = time.time()
    while True:
        print(i, time.strftime("%H:%M:%S", time.localtime()))
        #  Getting the dates
        base = datetime.datetime.today()
        date_list = [base + datetime.timedelta(days=x) for x in range(numdays)]
        date_str = [x.strftime("%d-%m-%Y") for x in date_list]
        # print(base,"\n", date_list, "\n", date_str)
        for INP_DATE in date_str:
            #  Dummy URL for testing -
            #  URL = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/findByDistrict?district_id=512&date=
            #  31-03-2021"

            # API to get planned vaccination sessions on a specific date in a given district. Reading API documentation
            # recommended
            try:
                URL = f"https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/findByDistrict?district_id=" \
                      f"{dist_id}&date={INP_DATE}"
                response = requests.get(URL, headers=browser_header)
                response.raise_for_status()
                with open ("result.csv", 'a+') as f:
                    f.write(f'{str(i)} {INP_DATE} {response.text}\n')
                #  print(f"Result: {INP_DATE}-{response.text}")
            except requests.exceptions.HTTPError as errh:
                print("Http Error:", errh)
            except requests.exceptions.ConnectionError as errc:
                print("Error Connecting:", errc)
            except requests.exceptions.Timeout as errt:
                print("Timeout Error:", errt)
            except requests.exceptions.RequestException as err:
                print("Oops: Something Else", err)
            else:
                # will now only been displayed when you DO have a 200
                print(f'{INP_DATE} Response code: {response.status_code}')
                if response.ok:
                    resp_json = response.json()
                    # read cowin documentation to understand following if/else tree
                    if resp_json["sessions"]:
                        for center in resp_json["sessions"]:  # printing each center
                            if center["min_age_limit"] <= age and center["available_capacity"] > 1:
                                # Creating text to send to telegram
                                if center["vaccine"] == '':
                                    center["vaccine"] = '-'
                                if center['fee_type'] == "Free":
                                    center["fee"] = 0
                                txt = f'Available on:  <b>{INP_DATE}</b>\nName: {center["name"]}\nBlock ' \
                                      f'Name: {center["block_name"]}\nPinCode: {center["pincode"]}\n' \
                                      f'Min Age: {center["min_age_limit"]}\nFree/Paid: {center["fee_type"]}\n' \
                                      f'Amount: {center["fee"]}\nAvailable Capacity: {center["available_capacity"]}\n' \
                                      f'\t\tDose 1: {center["available_capacity_dose1"]}\n' \
                                      f'\t\tDose 2: {center["available_capacity_dose2"]}\n' \
                                      f'Vaccine: {center["vaccine"]}\n\nhttps://selfregistration.cowin.gov.in/'
                                print(txt)
                                #
                                #  check_sent(txt, center, INP_DATE)
                                send_new_msg(txt, center)
                    else:
                        print("No available slots on {}".format(INP_DATE))
                else:
                    print("Response not obtained from site.")
        # time.sleep(25)  # Using 7 requests (for 7 days) in 1 second. 100 requests per 5 minutes allowed. You do the
        # math.
        time.sleep(300)  # Checking for slots every 5 minutes.
        #  timing the loop
        now = time.time()
        print("It has been {} seconds since the loop started\n".format(now - loop_starts))
        i += 1


if __name__ == "__main__":
    telegram_required()
    cowin_required()
    main_loop()
