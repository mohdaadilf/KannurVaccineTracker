import requests
import datetime
import time

#  IMP
#  get your token from botfather on Telegram and figure out the chat_id (Can be by sending a message in the created
#  group and looking at the https://api.telegram.org/bot{token}/getUpdates page. Save them in a txt file 'keys' in
#  consecutive lines

with open('keys.txt', 'r') as file:
    token = file.readline().strip('\n')
    chat_id = file.readline()

# max age
age = 45

# Print details flag
print_flag = 'Y'

# Number of days to check ahead
numdays = 7

# district ID
dist_id = "297"

# header required due to changes to API

# header = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko)'
#               'Chrome/39.0.2171.95 Safari/537.36'}
browser_header = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                'Chrome/56.0.2924.76 Safari/537.36'}

#  for i in range(2):

while True:
    #  Getting the dates
    base = datetime.datetime.today()
    date_list = [base + datetime.timedelta(days=x) for x in range(numdays)]
    date_str = [x.strftime("%d-%m-%Y") for x in date_list]
    # print(base,"\n", date_list, "\n", date_str)
    # For timing the loop
    program_starts = time.time()
    for INP_DATE in date_str:
        #  URL for testing -
        #  URL = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/findByDistrict?district_id=512&date=
        #  31-03-2021"

        # API to get planned vaccination sessions on a specific date in a given district. Reading API documentation
        # recommended
        URL = f"https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/findByDistrict?district_id={dist_id}&" \
              f"date={INP_DATE}"
        response = requests.get(URL, headers=browser_header)
        print(f'Response code: {response.status_code}')
        if response.ok:
            resp_json = response.json()
            # print(json.dumps(resp_json, indent = 1))
            # flag = False
            # read documentation to understand following if/else tree
            if resp_json["sessions"]:
                print("Available on: {}".format(INP_DATE))
                if print_flag == 'y' or print_flag == 'Y':
                    for center in resp_json["sessions"]:  # printing each center
                        if center["min_age_limit"] <= age:
                            print("\t", "Name:", center["name"])
                            print("\t", "Block Name:", center["block_name"])
                            print("\t", "Pin Code:", center["pincode"])
                            #   print("\t", "Center:", center)
                            print("\t", "Min Age:", center['min_age_limit'])
                            print("\t Free/Paid: ", center["fee_type"])
                            if center['fee_type'] != "Free":
                                print("\t", "Amount:", center["fee"])
                            else:
                                center["fee"] = '-'
                            print("\t Available Capacity: ", center["available_capacity"])
                            if center["vaccine"] != '':
                                print("\t Vaccine: ", center["vaccine"])
                            else:
                                center["vaccine"] = '-'
                            print("\n\n")

                            # Creating text to send to telegram
                            txt = f'Available on: {INP_DATE}\nName: {center["name"]}\nBlock ' \
                                  f'Name: {center["block_name"]}\nPinCode: {center["pincode"]}\n' \
                                  f'Min Age: {center["min_age_limit"]}\nFree/Paid: {center["fee_type"]}\n' \
                                  f'Amount: {center["fee"]}\nAvailable Capacity: {center["available_capacity"]}\n' \
                                  f'Vaccine: {center["vaccine"]}'
                            to_url = 'https://api.telegram.org/bot{}/sendMessage?chat_id={}&text={}&parse_mode=HTML'. \
                                format(token, chat_id, txt)
                            resp = requests.get(to_url)
                            print('Sent')
            else:
                print("No available slots on {}".format(INP_DATE))
    time.sleep(25)  # Using 7 requests (for 7 days) in 1 second. 100 requests per 5 minutes allowed. You do the math.
    #  timing the loop
    now = time.time()
    print("It has been {} seconds since the loop started".format(now - program_starts))

