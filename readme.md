# Intro
Initially made into a bot (yet to be deployed) to find Vaccine Centres in Kannur, Kerala for people under the Age 45 (and above 18). 
* Made using the cowin-api [Click here  for Api Setu Site](https://apisetu.gov.in/public/marketplace/api/cowin)
* Updates might not be real time as documentation mentions "data can be cached and may be up to 30 minutes old".	
* Sends message using telegram. **Must have your own Telegram token and data to send message to telegram**. Refer to [Configuring Telegram Bot](#configuring-telegram-bot) or just remove lines 5 to 11 as well as 88 to 97 (shown below):
[Not updated]
```python
#  IMP
#  get your token from botfather on Telegram and figure out the chat_id (Can be by sending a message in the created
#  group and looking at the https://api.telegram.org/bot{token}/getUpdates page.

with open('keys.txt', 'r') as file:
    token = file.readline().strip('\n')
    chat_id = file.readline()
```  

```python
# Creating text to send to telegram
txt = f'Name:{center["name"]}\nBlock Name:{center["block_name"]}\nPinCode:{center["pincode"]}\nMin Age:{center["min_age_limit"]}\nFree/Paid:{center["fee_type"]}\nAmount:{center["fee"]}\nAvailable Capacity:{center["available_capacity"]}\nVaccine:{center["vaccine"]}'
to_url = 'https://api.telegram.org/bot{}/sendMessage?chat_id={}&text={}&parse_mode=HTML'.format(token, chat_id, txt)
resp = requests.get(to_url)
print('Sent')
``` 
* Wont send a message if availability of Vaccine < 10 (No point doing that)

### Configuring Telegram bot
[Refer to this video]( https://www.youtube.com/watch?v=JBb4-Zeezss).
Thought the video is a bit long, it does a good job of explaining what needs to be done in order to configure the telegram bot.
### Modifying for other districts
* The code can also be modified to check availability in any other district. The code can be modified to check availability of Covid-19 Vaccine for any district in India. To see all district codes, [click on this link to view csv containing District ID's](https://github.com/bhattbhavesh91/cowin-vaccination-slot-availability/blob/main/district_mapping%20v1.csv) . On finding your required district, copy paste it into line number 23 in main.py
* Fin.
```python
dist_id = "INSERT_DISTRICT_ID HERE"
```
For example:
```python
dist_id = "512"
```
##### Additional Info
* Since this is an early build, a lot of random, unwanted code is lying around that may or may not be helpful. Examples include timing the loop and commented code which might come into help whilst creating a bot.
* [Additional documentation help](https://api.covid19india.org/)
* [Credit goes this repo for all the main work!](https://github.com/bhattbhavesh91/cowin-vaccination-slot-availability)