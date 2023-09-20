import time
import schedule
import requests

def do_constantly():
    resp = requests.get(url="http://frontend-internal:5001/checkout")
    print(resp.status_code)

schedule.every(7).seconds.do(do_constantly)

while True:
    schedule.run_pending()
    time.sleep(.5)
