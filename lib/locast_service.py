# pylama:ignore=E722,E303
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import pathlib
from datetime import datetime

import lib.m3u8 as m3u8
import lib.stations as stations
from lib.l2p_tools import handle_url_except



class LocastService:

    location = {
                "latitude": None,
                "longitude": None,
                "DMA": None,
                "city": None,
                "active": False
               }

    current_token = None

    DEFAULT_USER_AGENT = 'Mozilla/5.0'


    def __init__(self, location):
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
                                          {'Content-Type': 'application/json', 'User-agent': self.DEFAULT_USER_AGENT})

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
                                                  'authorization': 'Bearer ' + self.current_token,
                                                  'User-agent': self.DEFAULT_USER_AGENT})

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



    def get_stations(self):

        # TODO: check if we dont return any results

        print("Getting list of stations based on DMA...")

        try:
            # https://api.locastnet.org/api/watch/epg/504
            # get stations
            stationsReq = urllib.request.Request('https://api.locastnet.org/api/watch/epg/' + str(self.location["DMA"]),
                                                    headers={'Content-Type': 'application/json',
                                                            'authorization': 'Bearer ' + self.current_token,
                                                            'User-agent': self.DEFAULT_USER_AGENT})

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

            if hasattr(stationErr, 'message'):
                print("Error when getting the list of stations: " + stationErr.message)
            elif hasattr(stationErr, 'reason'):
                print("Error when getting the list of stations: " + stationErr.reason)
            else:
                print("Error when getting the list of stations: " + str(stationErr))

            return False

        return stationsRes


    def get_station_stream_uri(self, station_id):
        print("Getting station info for " + station_id + "...")

        try:
            videoUrlReq = urllib.request.Request('https://api.locastnet.org/api/watch/station/' +
                                                 str(station_id) + '/' +
                                                 self.location['latitude'] + '/' +
                                                 self.location['longitude'],
                                                 headers={'Content-Type': 'application/json',
                                                          'authorization': 'Bearer ' + self.current_token,
                                                          'User-agent': self.DEFAULT_USER_AGENT})
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

            if hasattr(videoUrlReqErr, 'message'):
                print("Error when getting the video URL: " + videoUrlReqErr.message)
            elif hasattr(videoUrlReqErr, 'reason'):
                print("Error when getting the video URL: " + videoUrlReqErr.reason)
            else:
                print("Error when getting the video URL: " + str(videoUrlReqErr))

            return False

        print("Determining best video stream for " + station_id + "...")

        bestStream = None

        # find the heighest stream url resolution and save it to the list
        videoUrlM3u = m3u8.load(videoUrlRes['streamUrl'], headers={'authorization': 'Bearer ' + self.current_token,
                                                                   'User-agent': self.DEFAULT_USER_AGENT})



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
