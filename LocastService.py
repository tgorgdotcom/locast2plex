# pylama:ignore=E722,E303
import json
import sys
from datetime import datetime
import urllib.error
import urllib.parse
import urllib.request
import pathlib

import m3u8

from L2PTools import handle_url_except
from dma_markets import get_dma_info
import Facilities


class LocastService:

    location = {
                "latitude": None,
                "longitude": None,
                "DMA": None,
                "city": None,
                "active": False
                }

    current_token = None
    base_data_folder = None
    json_data_folder = None

    tv_facilities = None
    known_stations = None


    def __init__(self, script_dir, config, location):
        self.base_data_folder = pathlib.Path(script_dir).joinpath('data')
        self.json_data_folder = pathlib.Path(self.base_data_folder).joinpath('json')
        self.facility_cache_folder = pathlib.Path(config.config["locast2plex"]["cache_dir"]).joinpath('facilities')
        self.mock_location = config.config["location"]["mock_location"]
        self.zipcode = config.config["location"]["override_zipcode"]

        #  Json files
        self.tv_facilities = pathlib.Path(self.facility_cache_folder).joinpath('tv_facilities.json')
        self.known_stations = pathlib.Path(self.json_data_folder).joinpath('known_stations.json')

        self.location = location


    @handle_url_except
    def login(self, username, password):

        # check environment vars
        if (username is None):
            print("Usernanme not specified in config.ini.  Exiting...")
            return False

        if (password is None):
            print("Password not specified in config.ini.  Exiting...")
            return False

        # login
        print("Logging into Locast using username " + username + "...")

        # https://api.locastnet.org/api/user/login
        # POST
        # {"username":"thomas_vg1@hotmail.com","password":"xxxxxxxx"}


        loginReq = urllib.request.Request('https://api.locastnet.org/api/user/login',
                                          ('{"username":"' + username + '","password":"' + password + '"}').encode("utf-8"),
                                          {'Content-Type': 'application/json'})

        loginOpn = urllib.request.urlopen(loginReq)
        loginRes = json.load(loginOpn)
        loginOpn.close()

        self.current_token = loginRes["token"]
        return True


    @handle_url_except
    def validate_user(self):
        print("Validating User Info...")

        # get user info and make sure we donated
        userReq = urllib.request.Request('https://api.locastnet.org/api/user/me',
                                         headers={'Content-Type': 'application/json',
                                                  'authorization': 'Bearer ' + self.current_token})

        userOpn = urllib.request.urlopen(userReq)
        userRes = json.load(userOpn)
        userOpn.close()

        print("User Info obtained.")
        print("User didDonate: {}".format(userRes['didDonate']))
        # Check if the user has donated, and we got an actual expiration date.
        if userRes['didDonate'] and userRes['donationExpire']:
            # Check if donation has expired.
            donateExp = datetime.fromtimestamp(userRes['donationExpire'] / 1000)
            print("User donationExpire: {}".format(donateExp))
            if datetime.now() > donateExp:
                print("Error!  User's donation ad-free period has expired.")
                return False
        else:
            print("Error!  User must donate for this to work.")
            return False

        return True


    def get_stations(self, config):

        # TODO: check if we dont return any results

        print("Getting list of stations based on DMA...")

        try:
            # https://api.locastnet.org/api/watch/epg/504
            # get stations
            stationsReq = urllib.request.Request('https://api.locastnet.org/api/watch/epg/' + str(self.location["DMA"]),
                                                 headers={'Content-Type': 'application/json',
                                                          'authorization': 'Bearer ' + self.current_token})

            stationsOpn = urllib.request.urlopen(stationsReq)
            stationsRes = json.load(stationsOpn)
            stationsOpn.close()

        except urllib.error.URLError as urlError:
            print("Error when getting the list of stations: " + str(urlError.reason))
            return False
        except urllib.error.HTTPError as httpError:
            print("Error when getting the list of stations: " + str(httpError.reason))
            return False
        except:
            stationErr = sys.exc_info()[0]
            print("Error when getting the list of stations: " + stationErr.message)
            return False

        # get the actual channel number by comparing the callsign with
        # the FCC facilities list
        print("Loading FCC Stations list...")
        Facilities.get_facilities(config)

        with open(self.tv_facilities, "r") as fcc_station_file_obj:
            fcc_stations = json.load(fcc_station_file_obj)
        fcc_stations = fcc_stations["fcc_station_list"]

        fcc_market = get_dma_info(str(self.location["DMA"]))
        if not len(fcc_market):
            print("No DMA to FCC mapping found.  Poke the developer to get it into locast2plex.")
            return False


        with open(self.known_stations, "r") as known_stations_file_obj:
            known_stations = json.load(known_stations_file_obj)


        noneChannel = 1000


        for index, locast_station in enumerate(stationsRes):

            # check if this is a [channel] [station name] result in the callsign
            # whether the first char is a number (checking for result like "2.1 CBS")
            try:
                # if number, get the channel and name -- we're done!
                # Check if the the callsign has a float (x.x) value. Save as a
                # string though, to preserve any trailing 0s as on reported
                # on https://github.com/tgorgdotcom/locast2plex/issues/42

                assert(float(locast_station['callSign'].split()[0]))
                stationsRes[index]['channel'] = locast_station['callSign'].split()[0]

            except ValueError:

                # result like "WDPN" or "CBS" in the callsign field, or the callsign in the name field
                # then we'll search the callsign in a few different lists to get the station channel
                # note: callsign field usually has the most recent data if it contains an actual callsign
                skip_sub_id = False

                # callsign from "callsign" field
                callsign_result = self.detect_callsign(locast_station['callSign'])

                # callsign from "name" field - usually in "[callsign][TYPE][subchannel]" format
                # example: WABCDT2
                alt_callsign_result = self.detect_callsign(locast_station['name'])


                # check the known station json that we maintain whenever locast's
                # reported station is iffy
                # first look via "callsign" value
                ks_result = self.find_known_station(locast_station, 'callSign', known_stations)
                if ks_result is not None:
                    stationsRes[index]['channel'] = ks_result['channel']
                    skip_sub_id = ks_result['skip_sub']


                # then check "name"
                if ('channel' not in stationsRes[index]):
                    ks_result = self.find_known_station(locast_station, 'name', known_stations)
                    if ks_result is not None:
                        stationsRes[index]['channel'] = ks_result['channel']
                        skip_sub_id = ks_result['skip_sub']


                # if we couldn't find anything look through fcc list for a match.
                # first by searching the callsign found in the "callsign" field
                if ('channel' not in stationsRes[index]) and callsign_result['verified']:
                    for city_item in fcc_market:
                        result = self.find_fcc_station(callsign_result['callsign'], fcc_market[city_item]["city"], fcc_stations)
                        if result is not None:
                            stationsRes[index]['channel'] = result['channel']
                            skip_sub_id = result['analog']
                            break


                # if we still couldn't find it, see if there's a match via the
                # "name" field
                if ('channel' not in stationsRes[index]) and alt_callsign_result['verified']:
                    for city_item in fcc_market:
                        result = self.find_fcc_station(alt_callsign_result['callsign'], fcc_market[city_item]["city"], fcc_stations)
                        if result is not None:
                            stationsRes[index]['channel'] = result['channel']
                            skip_sub_id = result['analog']
                            break


                # locast usually adds a number in it's callsign (in either field).  that
                # number is the subchannel
                if (not skip_sub_id) and ('channel' in stationsRes[index]):
                    if callsign_result['verified'] and (callsign_result['subchannel'] is not None):
                        stationsRes[index]['channel'] = stationsRes[index]['channel'] + '.' + callsign_result['subchannel']
                    elif alt_callsign_result['verified'] and (alt_callsign_result['subchannel'] is not None):
                        stationsRes[index]['channel'] = stationsRes[index]['channel'] + '.' + alt_callsign_result['subchannel']
                    else:
                        stationsRes[index]['channel'] = stationsRes[index]['channel'] + '.1'


                # mark stations that did not get a channel, but outside of the normal range.
                # the user will have to weed these out in Plex...
                if ('channel' not in stationsRes[index]):
                    stationsRes[index]['channel'] = str(noneChannel)
                    noneChannel = noneChannel + 1


        return stationsRes


    def detect_callsign(self, compare_string):
        verified = False
        station_type = None
        subchannel = None
        backIndex = -1

        while compare_string[backIndex].isnumeric():
            backIndex = backIndex - 1

        # if there is a number, backIndex will be > 1
        if backIndex != -1:
            subchannel = compare_string[(backIndex + 1):]
            compare_string = compare_string[:(backIndex + 1)]
        else:
            compare_string = compare_string

        if len(compare_string) > 4:
            station_type = compare_string[-2:]
            compare_string = compare_string[:-2]

        # verify if text from "callsign" is an actual callsign
        if (((compare_string[0] == 'K')
           or (compare_string[0] == 'W')) and ((len(compare_string) == 3)
           or (len(compare_string) == 4))):
            verified = True

        return {
            "verified": verified,
            "station_type": station_type,
            "subchannel": subchannel,
            "callsign": compare_string
        }





    def find_known_station(self, station, searchBy, known_stations):

        for known_station in known_stations:
            if ((known_station[searchBy] == station[searchBy])
               and (known_station['dma'] == station['dma'])):

                returnChannel = known_station['rootChannel']

                if known_station['subChannel'] is not None:
                    return {
                        "channel": returnChannel + '.' + known_station['subChannel'],
                        "skip_sub": True
                    }

                elif known_station['analog']:
                    return {
                        "channel": returnChannel,
                        "skip_sub": True
                    }

                return {
                    "channel": returnChannel,
                    "skip_sub": False
                }

        return None





    def find_fcc_station(self, callsign, market, fcc_stations):
        for fcc_station in fcc_stations:
            # go through each possible station
            if (fcc_station['nielsen_dma'] == market):
                # split fcc callsign away from it's dash, if one exists, then compare
                compare_callsign = fcc_station['fac_callsign'].split('-')[0]
                if compare_callsign == callsign:
                    # if we have a callsign match, add the channel
                    if fcc_station['tv_virtual_channel'] != "":
                        return {
                            "channel": fcc_station['tv_virtual_channel'],
                            "analog": False
                        }
                    else:
                        # if we find this to be analog, don't apply subchannel
                        return {
                            "channel": fcc_station['fac_channel'],
                            "analog": True
                        }

        return None

    def get_station_stream_uri(self, station_id):
        print("Getting station info for " + station_id + "...")

        try:
            videoUrlReq = urllib.request.Request('https://api.locastnet.org/api/watch/station/' +
                                                 str(station_id) + '/' +
                                                 self.location['latitude'] + '/' +
                                                 self.location['longitude'],
                                                 headers={'Content-Type': 'application/json',
                                                          'authorization': 'Bearer ' + self.current_token})
            videoUrlOpn = urllib.request.urlopen(videoUrlReq)
            videoUrlRes = json.load(videoUrlOpn)
            videoUrlOpn.close()
        except urllib.error.URLError as urlError:
            print("Error when getting the video URL: " + str(urlError.reason))
            return False
        except urllib.error.HTTPError as httpError:
            print("Error when getting the video URL: " + str(httpError.reason))
            return False
        except:
            videoUrlReqErr = sys.exc_info()[0]
            print("Error when getting the video URL: " + videoUrlReqErr.message)
            return False

        print("Determining best video stream for " + station_id + "...")

        bestStream = None

        # find the heighest stream url resolution and save it to the list
        videoUrlM3u = m3u8.load(videoUrlRes['streamUrl'])



        print("Found " + str(len(videoUrlM3u.playlists)) + " Playlists")

        if len(videoUrlM3u.playlists) > 0:
            for videoStream in videoUrlM3u.playlists:
                if bestStream is None:
                    bestStream = videoStream

                elif ((videoStream.stream_info.resolution[0] > bestStream.stream_info.resolution[0]) and
                      (videoStream.stream_info.resolution[1] > bestStream.stream_info.resolution[1])):
                    bestStream = videoStream

                elif ((videoStream.stream_info.resolution[0] == bestStream.stream_info.resolution[0]) and
                      (videoStream.stream_info.resolution[1] == bestStream.stream_info.resolution[1]) and
                      (videoStream.stream_info.bandwidth > bestStream.stream_info.bandwidth)):
                    bestStream = videoStream


            if bestStream is not None:
                print(station_id + " will use " +
                      str(bestStream.stream_info.resolution[0]) + "x" + str(bestStream.stream_info.resolution[1]) +
                      " resolution at " + str(bestStream.stream_info.bandwidth) + "bps")

                return bestStream.absolute_uri

        else:
            print("No variant streams found for this station.  Assuming single stream only.")
            return videoUrlRes['streamUrl']
