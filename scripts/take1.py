import requests,numpy,json,schedule
from datetime import datetime,timedelta
from dataclasses import dataclass
from time import sleep

FROM_SWARTHMORE_url = "https://api.septa.org/api/Arrivals/index.php?station=Swarthmore&results=30&direction=N"
TO_SWARTHMORE_url = "https://api.septa.org/api/Arrivals/index.php?station=Swarthmore&results=30&direction=S"

FROM_SWARTHMORE_FILE = "from_swarthmore.txt"
TO_SWARTHMORE_FILE = "to_swarthmore_test.txt"

MORNING = "04:00"


data_from   = requests.get(FROM_SWARTHMORE_url).json()
data_to     = requests.get(TO_SWARTHMORE_url).json()

print("Center-City bound trains on the board today:")
for departures_list in data_from.values():
 for direction_block in departures_list:
  for direction, trains in direction_block.items():
   for train in trains:
    print(f"Train {train.get('train_id')} at {train.get('sched_time')[11:16]} from {train.get('origin')} "
          f"to {train.get('destination')} | Status: {train.get('status')}")


print("Swarthmore-bound trains on the board today:")
for departures_list in data_to.values():
 for direction_block in departures_list:
  for direction, trains in direction_block.items():
   for train in trains:
    print(f"Train {train.get('train_id')} at {train.get('sched_time')[11:16]} from {train.get('origin')} to {train.get('destination')} | Status: {train.get('status')}")

@dataclass
class TrainInstance:
    num:    int
    sch:    datetime
    delay:  float

# Create TrainInstance for each train today.
todays_trains_to_Swat = []
for departures_list in data_to.values():
 for direction_block in departures_list:
  for direction, trains in direction_block.items():
   for train in trains:
    todays_trains_to_Swat.append(TrainInstance(num=train.get('train_id'),
                                       sch=datetime.strptime(train.get('sched_time'),"%Y-%m-%d %H:%M:%S.%f"),
                                       delay=0.0))

# Create TrainInstance for each train today.
todays_trains_from_Swat = []
for departures_list in data_from.values():
 for direction_block in departures_list:
  for direction, trains in direction_block.items():
   for train in trains:
    todays_trains_from_Swat.append(TrainInstance(
                                        num=train.get('train_id'),
                                        sch=datetime.strptime(train.get('sched_time'),"%Y-%m-%d %H:%M:%S.%f"),
                                        delay=0.0))

def write(train_instance,filename):
    # Takes an object of type TrainInstance and appends it to the text file given
    with open(filename, "a") as file:
     t = train_instance
     file.write(f"{t.num} \t {t.sch.strftime("%Y-%m-%d %H:%M:%S")} \t {t.delay}\n")

# After you're done for the day, write to text file
##for item in todays_trains_from_Swat:
##    write(item,FROM_SWARTHMORE_FILE)
##for item in todays_trains_to_Swat:
##    write(item,TO_SWARTHMORE_FILE)

def get_delay(train_num,to_from):
    # Read SEPTA API for train number `train_num` and record the delay amount.
    if to_from == "to":
        url = TO_SWARTHMORE_url
    elif to_from == "from":
        url = FROM_SWARTHMORE_url
    data = requests.get(url).json()
    for departures_list in data.values():
     for direction_block in departures_list:
      for direction, trains in direction_block.items():
       for train in trains:
        if int(train.get('train_id')) == train_num:
         result = train.get('status')
         print(f"Result is {result}")
         if result == "On Time":
          return 0
         elif "min" in result:
          return int(result.split()[0]) # first element of list of broken-up parts by space
         else:
          return 0

global k
k = 0
while True:
    sleep(60)
    print(f"Time: {datetime.now().strftime("%H:%M:%S")}.")
    print(f"Train {todays_trains_to_Swat[k].num} "
          f"scheduled at Swarthmore at "
          f"{todays_trains_to_Swat[k].sch.strftime("%H:%M")}")
    print("No train to check right now.")
    if datetime.now().replace(second=0,microsecond=0) == todays_trains_to_Swat[k].sch - timedelta(minutes=1):
        print(f"We are within 01 minute of the scheduled time of train {todays_trains_to_Swat[k].num} arriving at Swat.")
        todays_trains_to_Swat[k].delay = get_delay(todays_trains_to_Swat[k].num,"to")
        print(f"Recorded train {todays_trains_to_Swat[k].num} as having a delay of {todays_trains_to_Swat[k].delay} minutes")
        write(todays_trains_to_Swat[k],TO_SWARTHMORE_FILE)
        k = k + 1
    if k == len(todays_trains_to_Swat):
        break

while True:
    sleep(60)
    print(f"Time: {datetime.now().strftime("%H:%M:%S")}.")
    print(f"Train {todays_trains_to_Swat[k].num} "
          f"scheduled at Swarthmore at "
          f"{todays_trains_to_Swat[k].sch.strftime("%H:%M")}")
    print("No train to check right now.")
    if (datetime.now().replace(second=0,microsecond=0) - todays_trains_to_Swat[k].sch) < timedelta(minutes=5):
        # Starting from 5 minutes before, ping the server.
        current_delay = get_delay(todays_trains_to_Swat[k].num,"to")
        print(f"Train {todays_trains_to_Swat[k].num} is delayed by {current_delay} minutes")
    if datetime.now().replace(second=0,microsecond=0) == todays_trains_to_Swat[k].sch - timedelta(minutes=1):
        print(f"We are within 01 minute of the scheduled time of train {todays_trains_to_Swat[k].num} arriving at Swat.")
        todays_trains_to_Swat[k].delay = get_delay(todays_trains_to_Swat[k].num,"to")
        print(f"Recorded train {todays_trains_to_Swat[k].num} as having a delay of {todays_trains_to_Swat[k].delay} minutes")
        write(todays_trains_to_Swat[k],TO_SWARTHMORE_FILE)
        k = k + 1
    if k == len(todays_trains_to_Swat):
        break
        
    
