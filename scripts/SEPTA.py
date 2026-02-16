import requests

def queryRoute(origin):
    # Limited functionality. Origin assumes destination and direction.
    # Media/Wawa Line is hard-coded. Pulls 20 most-recent results, then
    # filters for the first Media/Wawa train in the direction requested.
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
    results = []
    for direction in data.values():
        for ns in direction:
            for entry in ns[direc]:
                if entry["origin"] == 'Wawa' or entry["destination"] == 'Wawa' or entry["origin"] == "Media" or entry["destination"] == "Media":
                    results.append(entry)
                    scheduled   = entry["sched_time"][11:16]
                    status      = entry["status"]
                    dest        = entry["destination"]
                    if status == "On Time":
                        result = f"TRAIN TO {destination}\n{scheduled} ON TIME "
                    else:
                        result = f"TRAIN TO {destination}\n{scheduled} {status} LATE "
                    break # One entry is enough.
    return results, result

if __name__ == "__main__":
    results, result = queryRoute("Swarthmore")
    # print(results)
    print(result)

