import requests
import json
import csv
import os.path
from dataclasses import dataclass
from secret import DATAMALL_APIKEY

DATA_FOLDER = "data"


@dataclass
class Position:
    longitude: float
    latitude: float


@dataclass
class Carpark:
    carpark_number: str
    total_lots: int
    lots_available: int
    lot_type: str
    address: str
    x_coord: float
    y_coord: float
    car_park_type: str
    type_of_parking_system: str
    short_term_parking: str
    free_parking: str
    night_parking: bool
    car_park_decks: int
    gantry_height: float
    car_park_basement: bool


def fetch_carpark_avail_datagov(overwrite=True):
    r = requests.get(
        "https://api.data.gov.sg/v1/transport/carpark-availability")
    response = r.json()
    timestamp = "latest" if overwrite else response['items'][0]['timestamp']
    filename = os.path.join(DATA_FOLDER, "avail", "avail_datagov_{}.json".format(timestamp))
    print(len(response['items'][0]['carpark_data']))
    with open(filename, 'w') as outfile:
        json.dump(response['items'][0], outfile)


def fetch_carpark_avail_lta(overwrite=True):
    headers = {
        "AccountKey": DATAMALL_APIKEY,
        "accept": "application/json"
    }
    r = requests.get(
        "http://datamall2.mytransport.sg/ltaodataservice/CarParkAvailabilityv2", headers=headers)
    response = r.json()
    timestamp = "latest" if overwrite else response['items'][0]['timestamp']
    filename = os.path.join(DATA_FOLDER, "avail", "avail_lta_{}.json".format(timestamp))
    print(len(response['value']))
    with open(filename, 'w') as outfile:
        json.dump(response['value'], outfile)


def fetch_carpark_avail_all(overwrite=True):
    fetch_carpark_avail_datagov(overwrite)
    fetch_carpark_avail_lta(overwrite)


def get_available_lots(latitude, longitude, radius=3):
    # e.g. latitude / longitude: 1.328172 / 103.842334
    # radius in km
    # if radius is none, return all carparks with their availability

    with open("data/hdb-carpark-information.csv") as f:
        reader = csv.DictReader(f)
        carpark_static_hdb = list(reader)
    with open("data/CarParkRates.csv") as f:
        reader = csv.DictReader(f)
        carpark_static_malls = list(reader)
    with open("data/avail/avail_datagov_latest.json") as f:
        latest_avail_hdb = json.load(f)['carpark_data']
    with open("data/avail/avail_lta_latest.json") as f:
        latest_avail_assorted = json.load(f)

    print(len(carpark_static))
    print(carpark_static[0])
    print(len(latest_avail))
    print(latest_avail[0])
    return [] # return a list of carparks
