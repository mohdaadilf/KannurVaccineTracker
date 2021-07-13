import requests
import datetime
import time
from SubFolder import age, numdays, dist_id, browser_header
from SubFolder.telegram_and_db import telegram_required, check_in_db, cleaning_db


def main_loop():
    def convert_sec(n):
        day = n // (24 * 3600)

        n = n % (24 * 3600)
        hour = n // 3600

        n %= 3600
        minutes = n // 60

        n %= 60
        seconds = n
        print(f"It has been {day} days {hour} hours {minutes} minutes {seconds} seconds since the loop started\n")

    # For timing the loop
    i = 1
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
                url = f"https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/findByDistrict?district_id=" \
                      f"{dist_id}&date={INP_DATE}"
                response = requests.get(url, headers=browser_header)
                response.raise_for_status()
                with open("miscellaneous/results.csv", 'a+') as f:  # This is not important. To save space remove these
                    f.write(f'{str(i)} {INP_DATE} {response.text}\n')  # two lines
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
                                txt = f'Available on:  <b>{INP_DATE}</b>\nName: {center["name"]}\nAddress: ' \
                                      f'{center["address"]}\nBlock Name: {center["block_name"]}\nPinCode: ' \
                                      f'{center["pincode"]}\nMin Age: {center["min_age_limit"]}\nFree/Paid: ' \
                                      f'{center["fee_type"]}\nAmount: {center["fee"]}\nAvailable Capacity: ' \
                                      f'{center["available_capacity"]}\n' \
                                      f'\t\tDose 1: {center["available_capacity_dose1"]}\n' \
                                      f'\t\tDose 2: {center["available_capacity_dose2"]}\n' \
                                      f'Vaccine: {center["vaccine"]}\n\nhttps://selfregistration.cowin.gov.in/'
                                print(txt)
                                check_in_db(center, txt)
                                # send_new_msg(txt, center)
                    else:
                        print("No available slots on {}".format(INP_DATE))
                else:
                    print("Response not obtained from site.")
        # time.sleep(25)  # Using 7 requests (for 7 days) in 1 second. 100 requests per 5 minutes allowed. You do the
        # math.
        cleaning_db()
        print("End:", i, time.strftime("%H:%M:%S", time.localtime()))
        time.sleep(300)  # Checking for slots every 5 minutes.
        #  timing the loop
        now = time.time()
        #  print("It has been {} seconds since the loop started\n".format(now - loop_starts))
        convert_sec(now - loop_starts)
        i += 1


if __name__ == "__main__":
    telegram_required()
    main_loop()
