import requests
import json
import os.path
from dataclasses import dataclass

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


def fetch_carpark_avail(overwrite=True):
    r = requests.get(
        "https://api.data.gov.sg/v1/transport/carpark-availability")
    response = r.json()
    timestamp = "latest" if overwrite else response['items'][0]['timestamp']
    filename = os.path.join(DATA_FOLDER, "avail", "avail_{}.json".format(timestamp))
    with open(filename, 'w') as outfile:
        json.dump(response['items'][0], outfile)


def get_available_lots(latitude, longitude, radius=3):
    # e.g. latitude / longitude: 1.328172 / 103.842334
    # radius in km
    # if radius is none, return all carparks
    return [] # returns a list of carparks
