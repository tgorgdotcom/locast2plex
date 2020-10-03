import time
import urllib
import zipfile
import os
import datetime
import json
import pathlib

from L2PTools import clean_exit


def facilitesServerProcess(config):
    try:
        while True:
            time.sleep(config.config["dev"]["fcc_delay"])
            mainfacilities(config)
    except KeyboardInterrupt:
        clean_exit()


def mainfacilities(config):
    get_facilities(config)


def get_online_file_time(facility_url):
    url_head = urllib.request.Request(facility_url, method='HEAD')
    resp = urllib.request.urlopen(url_head)
    online_file_time = resp.headers['last-modified'].replace(" GMT", "")
    online_file_time = datetime.datetime.strptime(online_file_time, '%a, %d %b %Y %H:%M:%S')
    online_file_time = online_file_time.replace(tzinfo=FixedOffset(-4, "GMT-4")).astimezone(datetime.timezone.utc)
    return online_file_time


def get_offline_file_time(facility_zip_dl_path):
    offline_file_time = datetime.datetime.utcfromtimestamp(os.path.getmtime(facility_zip_dl_path))
    offline_file_time = offline_file_time.replace(tzinfo=datetime.timezone.utc)
    return offline_file_time


def clear_database_cache(facility_zip_dl_path, fcc_unzipped_dat, fcc_cached_file):
    print("Clearing FCC database cache.")
    if os.path.exists(facility_zip_dl_path):
        os.remove(facility_zip_dl_path)
    if os.path.exists(fcc_unzipped_dat):
        os.remove(fcc_unzipped_dat)
    if os.path.exists(fcc_cached_file):
        os.remove(fcc_cached_file)


def fcc_db_format(fac_line):
    current_date = datetime.datetime.utcnow()

    clean_line = fac_line.strip()
    fac_line_split = clean_line.split('|')

    fac_template = {
                    "comm_city": "",
                    "comm_state": "",
                    "eeo_rpt_ind": "",
                    "fac_address1": "",
                    "fac_address2": "",
                    "fac_callsign": "",
                    "fac_channel": "",
                    "fac_city": "",
                    "fac_country": "",
                    "fac_frequency": "",
                    "fac_service": "",
                    "fac_state": "",
                    "fac_status_date": "",
                    "fac_type": "",
                    "facility_id": "",
                    "lic_expiration_date": "",
                    "fac_status": "",
                    "fac_zip1": "",
                    "fac_zip2": "",
                    "station_type": "",
                    "assoc_facility_id": "",
                    "callsign_eff_date": "",
                    "tsid_ntsc": "",
                    "tsid_dtv": "",
                    "digital_status": "",
                    "sat_tv": "",
                    "network_affil": "",
                    "nielsen_dma": "",
                    "tv_virtual_channel": "",
                    "last_change_date": "",
                    "end_of_record": "",
                    }
    formatteddict = {}
    key_num = 0
    for fcc_key in list(fac_template.keys()):
        insert_value = None
        if fac_line_split[key_num] != '':
            insert_value = fac_line_split[key_num]
        formatteddict[fcc_key] = insert_value
        key_num += 1

    # Check if expired
    if (not formatteddict['fac_status'] or formatteddict['fac_status'] != 'LICEN'
       or not formatteddict['lic_expiration_date']):
        return None

    fac_lic_expiration_date_split = formatteddict["lic_expiration_date"].split('/')
    fac_lic_expiration_date_datetime = datetime.datetime(int(fac_lic_expiration_date_split[2]),
                                                         int(fac_lic_expiration_date_split[0]),
                                                         int(fac_lic_expiration_date_split[1]),
                                                         23, 59, 59, 999999)
    if fac_lic_expiration_date_datetime < current_date:
        return None

    # Check if we have a correct signal type
    if formatteddict['fac_service'] not in ['DT', 'TX', 'TV', 'TB', 'LD', 'DC']:
        return None

    return formatteddict


def get_facilities(config):

    fcc_cache_dir = pathlib.Path(config.config["locast2plex"]["cache_dir"]).joinpath("facilities")
    if not fcc_cache_dir.is_dir():
        fcc_cache_dir.mkdir()

    facility_url = 'https://transition.fcc.gov/ftp/Bureaus/MB/Databases/cdbs/facility.zip'
    facility_zip_dl_path = pathlib.Path(fcc_cache_dir).joinpath("facility.zip")
    fcc_unzipped_dat = pathlib.Path(fcc_cache_dir).joinpath("facility.dat")
    fcc_cached_file = pathlib.Path(fcc_cache_dir).joinpath("tv_facilities.json")

    why_download = None

    if not os.path.exists(facility_zip_dl_path):
        why_download = "Facility facilities database cache missing."
    else:

        print("Checking FCC facilities database for updates.")

        offline_file_time = get_offline_file_time(facility_zip_dl_path)
        online_file_time = get_online_file_time(facility_url)

        if not offline_file_time <= online_file_time:
            print("Cached facilities database is current.")
        else:
            why_download = "Online facilities database is newer."

    if why_download:
        clear_database_cache(facility_zip_dl_path, fcc_unzipped_dat, fcc_cached_file)
        print(why_download + ' Downloading the latest FCC facilities database...')
        urllib.request.urlretrieve(facility_url, facility_zip_dl_path)

    if not os.path.exists(fcc_unzipped_dat):

        print('Unzipping FCC facilities database...')

        with zipfile.ZipFile(facility_zip_dl_path, 'r') as zip_ref:
            zip_ref.extractall(fcc_cache_dir)

    if not os.path.exists(fcc_cached_file) or why_download:
        print('Reading and formatting FCC database...')

        with open(fcc_unzipped_dat, "r") as fac_file:
            lines = fac_file.readlines()

        facility_list = []
        for fac_line in lines:
            formatteddict = fcc_db_format(fac_line)
            if formatteddict:
                facility_list.append(formatteddict)

        print('Found ' + str(len(facility_list)) + ' stations.')

        facility_json = {
                        "fcc_station_list": facility_list
                        }
        with open(fcc_cached_file, "w") as write_file:
            json.dump(facility_json, write_file, indent=4, sort_keys=True)


class FixedOffset(datetime.tzinfo):
    """Fixed UTC offset: `local = utc + offset`."""

    def __init__(self, offset, name):
        self.__offset = datetime.timedelta(hours=offset)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return datetime.timedelta(0)
