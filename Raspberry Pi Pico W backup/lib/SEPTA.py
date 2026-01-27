import adafruit_requests

def queryRoute(origin):
    # Limited functionality. Origin assumes destination and direction.
    if origin == "Jefferson":
        origin_station  = "Market%20East"
        direction       = "S"
        direc           = "Southbound"
        destination     = "SWAT"
    elif origin == "Swarthmore":
        origin_station  = "Swarthmore"
        direction       = "N"
        direc           = "Northbound"
        destination     = "PHILA"
    SEPTA_url= f"https://www3.septa.org/api/Arrivals/index.php?station={origin_station}&results=20&direction={direction}"
    response = requests.get(SEPTA_url)
    data = response.json()
    for direction in data.values():
        for ns in direction:
            for entry in ns["Northbound"]:
                if entry["origin"] == 'Wawa' or entry["destination"] == 'Wawa' or entry["origin"] == "Media" or entry["destination"] == "Media":
                    scheduled   = entry["sched_time"][11:16]
                    status      = entry["status"]
                    dest        = entry["destination"]
                    if status == "On Time":
                        result = f"TRAIN TO PHILA\n{scheduled} ON TIME "
                    else:
                        result = f"TRAIN TO PHILA\n{scheduled} {status} LATE"
                    break
    response.close()
    return result
