import requests,numpy,json

SEPTA_url = "https://api.septa.org/api/Arrivals/index.php?station=Swarthmore&results=30&direction=N"
print(json.dumps(requests.get(SEPTA_url).json(),indent=4))
data = requests.get(SEPTA_url).json()

print("Trains on the board today:")
for departures_list in data.values():
 for direction_block in departures_list:
  for direction, trains in direction_block.items():
   for train in trains:
    print(f"Train {train.get('train_id')} at {train.get('sched_time')[11:16]} | Status: {train.get('status')}")
