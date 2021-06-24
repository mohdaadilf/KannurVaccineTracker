# Intro
Initially made into a bot (not deployed on any cloud yet) to find Vaccine Centres in Kannur, Kerala for people under the Age 45 (and above 18). This CANNOT book slots automatically. Only use this to check for slots.
* Made using the cowin-api [Click here  for Api Setu Site](https://apisetu.gov.in/public/marketplace/api/cowin)
* Updates might not be real time as documentation mentions "data can be cached and may be up to 30 minutes old".	
* Won't send a message if availability of Vaccine < 10 (No point doing that)

* Sends message using telegram. **If you want to configure to your own requirements, you must have your own Telegram token and other data to send message to telegram**. If you simply want to run the program, refer to [Configuring Telegram Bot](#configuring-telegram-bot) or just remove line 78, 86, 96  in main.py (shown below):
```python
send_new_msg(txt, center)
```
```python
cleaning_db()
```
```python
telegram_required()
```

### Configuring Telegram bot
[Refer to this video]( https://www.youtube.com/watch?v=JBb4-Zeezss).
Though the video is a bit long, it does a good job of explaining what needs to be done in order to configure the telegram bot.
### Modifying for other districts
* The code can also be modified to check availability in any other district. The code can be modified to check availability of Covid-19 Vaccine for any district in India. To see all district codes, [click on this link to view csv containing District ID's](https://github.com/bhattbhavesh91/cowin-vaccination-slot-availability/blob/main/district_mapping%20v1.csv) . On finding your required district, copy paste it into line number 22 in main.py
* For example:
```python
dist_id = "INSERT_DISTRICT_ID HERE"
```
(ie)
```python
dist_id = "512"
```
* Fin.
##### Additional Info
* Working Telegram channel: 
https://t.me/KannurVaccineTracer
* Since this is an early build, a lot of random, unwanted code is lying around that may or may not be helpful. Examples include timing the loop and commented code which might come into help whilst creating a bot.
* [Additional documentation help](https://api.covid19india.org/)
* [Credit goes this repo for all the main work!](https://github.com/bhattbhavesh91/cowin-vaccination-slot-availability)
* I've tried to document the code as much as I can. Lemme know if you need any other help.
* Click here 👇🏻 if you want to get me a cup of coffee :))

<a href="https://www.buymeacoffee.com/mohdaadilf" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/guidelines/download-assets-sm-1.svg" alt="Buy Me A Coffee" style="height: 50px !important;width: 174px !important !important; !important;" ></a>

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fgithub.com%2Fmohdaadilf%2FKannurVaccineTracker&count_bg=%23319E8E&title_bg=%23000000&icon=&icon_color=%23E7E7E7&title=Visitors%3A&edge_flat=false)](https://hits.seeyoufarm.com)