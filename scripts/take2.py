import requests,json
from datetime import datetime,timedelta
from dataclasses import dataclass
from time import sleep

FROM_SWARTHMORE_url = "https://api.septa.org/api/Arrivals/index.php?station=Swarthmore&results=30&direction=N"
TO_SWARTHMORE_url = "https://api.septa.org/api/Arrivals/index.php?station=Swarthmore&results=30&direction=S"

FROM_SWARTHMORE_FILE = "from_swarthmore.txt"
TO_SWARTHMORE_FILE = "to_swarthmore_test.txt"

@dataclass
class TrainInstance:
    num:    int
    sch:    datetime
    delay:  float

def write(train_instance,filename):
    # Takes an object of type TrainInstance and appends it to the text file given
    with open(filename, "a") as file:
     t = train_instance
     file.write(f"{t.num} \t {t.sch.strftime("%Y-%m-%d %H:%M:%S")} \t {t.delay}\n")

def empty_board(to_from):
    if to_from == "to":
        url = TO_SWARTHMORE_url
    elif to_from == "from":
        url = FROM_SWARTHMORE_url
    data = requests.get(url).json()
    for departures_list in data.values():
     for direction_block in departures_list:
      return len(direction_block) == 0
     
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
            print(f"--> API returned {result}")
            if result == "On Time":
              return 0
            elif "min" in result:
              return int(result.split()[0]) # first element of list of broken-up parts by space
            else:
              return 0

todays_trains_to_Swat = []
todays_trains_from_Swat = []
def populate_schedule(trains_list,to_from):
    if to_from == "to":
        url = TO_SWARTHMORE_url
    elif to_from == "from":
        url = FROM_SWARTHMORE_url
    data = requests.get(url).json()
    # Create TrainInstance for each train today.
    for departures_list in data.values():
     for direction_block in departures_list:
      for direction, trains in direction_block.items():
       for train in trains:
        trains_list.append(TrainInstance(num=int(train.get('train_id')),
                                           sch=datetime.strptime(train.get('sched_time'),"%Y-%m-%d %H:%M:%S.%f"),
                                           delay=None))
    

# Monitor the API
global k
k = 0
while True:
    sleep(60)
    if not empty_board("to"):
        if len(todays_trains_to_Swat) == 0:
         # needs to be inside loop to account for possibility that no trains are on board when
         populate_schedule(todays_trains_to_Swat,"to")
        time_until_arrival = todays_trains_to_Swat[k].sch - datetime.now().replace(microsecond=0)
        print(f"Time: {datetime.now().strftime("%H:%M:%S")}.")
        print(f"Train {todays_trains_to_Swat[k].num} "
              f"scheduled at Swarthmore at "
              f"{todays_trains_to_Swat[k].sch.strftime("%H:%M")}")
        print(f"Time until arrival is {time_until_arrival}")
        if timedelta(minutes=1) < time_until_arrival < timedelta(minutes=5):
            # Starting from 5 minutes before and until 1 minute before,, ping the server just to print.
            current_delay = get_delay(todays_trains_to_Swat[k].num,"to")
            print(f"Train {todays_trains_to_Swat[k].num} is delayed by {current_delay} minutes")
        if time_until_arrival < timedelta(minutes=1):
            print(f"We are within 01 minute of the scheduled time of train {todays_trains_to_Swat[k].num} arriving at Swat.")
            todays_trains_to_Swat[k].delay = get_delay(todays_trains_to_Swat[k].num,"to")
            print(f"==> Recorded train {todays_trains_to_Swat[k].num} as having a delay of {todays_trains_to_Swat[k].delay} minutes")
            write(todays_trains_to_Swat[k],TO_SWARTHMORE_FILE)
            k = k + 1
        if k == len(todays_trains_to_Swat):
            break
    else:
        print("No trains on the board right now.")
