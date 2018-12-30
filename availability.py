import requests
import json
import csv
import os.path
import logging
import math
from dataclasses import dataclass
import googlemaps
from utils import haversine, SVY21
from secret import DATAMALL_APIKEY, GOOGLE_MAPS_APIKEY
from config import DATA_FOLDER

logger = logging.getLogger(__name__)

CARPARKS = {}


@dataclass
class Page:
    start: int
    end: int
    total: int = None

    def check_total(self):
        if self.total is None:
            raise Exception("cannot calculate quantities if total is not set")

    def has_next(self):
        self.check_total()
        return self.end < self.total

    def has_prev(self):
        self.check_total()
        return self.start > 0

    def next_page(self):
        self.check_total()
        return Page(self.end, min(self.total, self.end + self.end - self.start), self.total)

    def prev_page(self):
        self.check_total()
        return Page(max(0, self.start - (self.end - self.start)), self.start, self.total)

    def total_pages(self):
        self.check_total()
        interval = self.end - self.start
        return int(math.ceil(self.total / interval))

    def current_page(self):
        self.check_total()
        interval = self.end - self.start
        return int(math.ceil(self.start / interval)) + 1


@dataclass
class Position:
    latitude: float
    longitude: float


@dataclass
class Carpark:
    id: str  # CarparkID if hdb, Development if not hdb, carpark_number in hdb availability
    position: Position  # lat long
    address: str
    total_lots: int = 0
    available_lots: int = 0

    lot_type: str = None
    agency: str = None

    # lta static variables (mostly rates)
    lta_area: str = None
    lta_category: str = None
    weekdays_rate_1: str = None
    weekdays_rate_2: str = None
    saturday_rate: str = None
    sunday_publicholiday_rate: str = None

    # hdb variables
    car_park_type: str = None
    type_of_parking_system: str = None
    short_term_parking: str = None
    free_parking: str = None
    night_parking: bool = None
    car_park_decks: int = None
    gantry_height: float = None
    car_park_basement: bool = None

    def is_valid(self):
        return self.position is not None and self.address is not None


def fetch_carpark_avail_datagov(overwrite=True):
    r = requests.get(
        "https://api.data.gov.sg/v1/transport/carpark-availability")
    response = r.json()
    timestamp = "latest" if overwrite else response['items'][0]['timestamp']
    filename = os.path.join(DATA_FOLDER, "avail", "avail_datagov_{}.json".format(timestamp))

    logger.debug("retrieved {} objects from data.gov.sg".format(len(response['items'][0]['carpark_data'])))
    with open(filename, 'w') as outfile:
        json.dump(response['items'][0], outfile)


def fetch_carpark_avail_lta(overwrite=True):
    lta_url = "http://datamall2.mytransport.sg/ltaodataservice/CarParkAvailabilityv2"
    headers = {
        "AccountKey": DATAMALL_APIKEY,
        "accept": "application/json"
    }
    r = requests.get(lta_url, headers=headers)
    try:
        result = r.json()['value']
    except:
        logger.error(f"Parsing json {r.json}")
        return
    for i in [500, 1000, 1500, 2000]:
        r = requests.get("{}?$skip={}".format(lta_url, i), headers=headers)
        result += r.json()['value']

    timestamp = "latest" if overwrite else ""
    filename = os.path.join(DATA_FOLDER, "avail", "avail_lta_{}.json".format(timestamp))
    logger.debug("retrieved {} objects from LTA datamall".format(len(result)))
    with open(filename, 'w') as outfile:
        json.dump(result, outfile)


def fetch_carpark_avail_all(overwrite=True):
    logger.debug("Fetch carpark availability...")
    fetch_carpark_avail_datagov(overwrite)
    fetch_carpark_avail_lta(overwrite)
    global CARPARKS
    CARPARKS = combine_availabilities_and_static_data()


def combine_availabilities_and_static_data():
    with open(os.path.join(DATA_FOLDER, "hdb-carpark-information.csv")) as f:
        reader = csv.DictReader(f)
        carpark_static_hdb = list(reader)
    with open(os.path.join(DATA_FOLDER, "carpark-rates.csv")) as f:
        reader = csv.DictReader(f)
        carpark_static_lta = list(reader)
    with open(os.path.join(DATA_FOLDER, "avail/avail_datagov_latest.json")) as f:
        latest_avail_hdb = json.load(f)['carpark_data']
    with open(os.path.join(DATA_FOLDER, "avail/avail_lta_latest.json")) as f:
        latest_avail_lta = json.load(f)

    carparks = {}
    for carpark in carpark_static_hdb:
        lat, lon = SVY21.computeLatLon(float(carpark['x_coord']), float(carpark['y_coord']))
        cp = Carpark(
            id=carpark['car_park_no'].upper(),
            position=Position(lat, lon),
            address=carpark['address'],
            agency='HDB',
            car_park_type=carpark['car_park_type'],
            type_of_parking_system=carpark['type_of_parking_system'],
            short_term_parking=carpark['short_term_parking'],
            free_parking=carpark['free_parking'],
            night_parking=carpark['night_parking'],
            car_park_decks=int(carpark['car_park_decks']),
            gantry_height=float(carpark['gantry_height']),
            car_park_basement=True if carpark['car_park_basement'] == 'Y' else False
        )

        carparks[carpark['car_park_no']] = cp

    for carpark in carpark_static_lta:
        cp = Carpark(
            id=carpark['carpark'],
            position=None,
            address=carpark['carpark'],
            agency='LTA',
            lta_category=carpark['category'],
            weekdays_rate_1=carpark['weekdays_rate_1'],
            weekdays_rate_2=carpark['weekdays_rate_2'],
            saturday_rate=carpark['saturday_rate'],
            sunday_publicholiday_rate=carpark['sunday_publicholiday_rate']
        )

        carparks[carpark['carpark']] = cp

    for avail in latest_avail_lta:
        carpark_id = avail['CarParkID'] if avail['Agency'] == 'HDB' else avail['Development']
        if carpark_id not in carparks:
            cp = Carpark(
                id=carpark_id,
                position=None,
                address=avail['Development']
            )
            carparks[carpark_id] = cp
        else:
            cp = carparks[carpark_id]

        if avail['Location'].strip():
            cp.position = Position(*[float(x) for x in avail['Location'].strip().split()])
        cp.available_lots = int(avail['AvailableLots'])
        cp.lot_type = avail['LotType']
        cp.agency = avail['Agency']
        cp.lta_area = avail['Area']

    for avail in latest_avail_hdb:
        info = avail['carpark_info'][0]
        carpark_id = avail['carpark_number']
        if carpark_id not in carparks:
            pass  # no point adding carparks if we don't know their address
            # cp = Carpark(
            #     id=carpark_id,
            #     position=None,
            #     address=""
            # )
            # carparks[carpark_id] = cp
        else:
            cp = carparks[carpark_id]
        cp.total_lots = int(info['total_lots'])
        cp.available_lots = int(info['lots_available'])
        cp.lot_type = info['lot_type']

    return carparks


def get_available_carparks(position, radius=3, limit=5):
    # e.g. latitude / longitude: 1.328172 / 103.842334
    # radius in km
    # if radius is none, return all carparks with their availability
    carparks = list(CARPARKS.values())
    logger.info(f"{len(carparks)} carparks in total")

    carparks = [carpark for carpark in carparks if carpark.is_valid() and carpark.available_lots is not None and carpark.available_lots > 0]
    logger.info(f"{len(carparks)} carparks are valid")

    if position is None or radius is None:
        logger.info("position or radius is None, no filtering is done")
        result = carparks
    else:
        available_carparks = [carpark for carpark in carparks if haversine(carpark.position.latitude, carpark.position.longitude, position.latitude, position.longitude) < radius]
        result = sorted(available_carparks, key=lambda x: haversine(x.position.latitude, x.position.longitude, position.latitude, position.longitude))
        logger.info(f"{len(result)} carparks are available and within radius of {radius}km")
    if limit:
        return result[:min(limit, len(result))]
    else:
        return result


def get_available_carparks_page(position, radius=3, limit=5, page=None):
    carparks = get_available_carparks(position, radius, limit)
    if len(carparks) == 0:
        raise NoCarparksFoundError
    page.total = len(carparks)
    if page.start >= page.end or page.start < 0 or page.start > len(carparks) or page.end < 0 or page.end > len(carparks):
        raise Exception(f"Invalid page numbers, start: {page.start}, end: {page.end}, total: {len(carparks)}")
    return carparks[page.start:page.end], page


def retrieve_carpark_by_id(carpark_id):
    return CARPARKS[carpark_id]


def gmaps_search_to_latlon(search_term):
    gmaps = googlemaps.Client(key=GOOGLE_MAPS_APIKEY)
    logger.info(f"Searching GMaps for {search_term} Singapore")
    result = gmaps.geocode(search_term + " Singapore")[0]
    location = result['geometry']['location']
    logger.info(f"Retrieved coordinates lat: {location['lat']}, lon: {location['lng']}")
    return Position(location['lat'], location['lng']), result['formatted_address']


def get_available_carparks_fuzzy(search_term, radius=3, limit=5):
    position, _ = gmaps_search_to_latlon(search_term)
    return get_available_carparks(position, radius, limit)


class NoCarparksFoundError(Exception):
    pass
