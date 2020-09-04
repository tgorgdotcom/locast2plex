import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import m3u8


class LocastService:

    current_token = None
    current_location = None
    current_dma = None
    base_data_folder = None





    def __init__(self, base_folder, mock_location):
        self.base_data_folder = base_folder

        if not mock_location == None:
            self.current_location = mock_location



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

        try:
            loginReq = urllib.request.Request('https://api.locastnet.org/api/user/login', 
                                              ('{"username":"' + username + '","password":"' + password + '"}').encode("utf-8"),
                                              {'Content-Type': 'application/json'})

            loginOpn = urllib.request.urlopen(loginReq)
            loginRes = json.load(loginOpn)
            loginOpn.close()
        except urllib.error.URLError as urlError:
            print("Error during login: " + str(urlError.reason))
            return False
        except urllib.error.HTTPError as httpError:
            print("Error during login: " + str(httpError.reason))
            return False
        except:
            loginErr = sys.exc_info()[0]
            print("Error during login: " + loginErr.message)
            return False

        self.current_token = loginRes["token"]
        return True





    def validate_user(self):
        print("Validating User Info...")

        try:
            # get user info and make sure we donated
            userReq = urllib.request.Request('https://api.locastnet.org/api/user/me', 
                                    headers={'Content-Type': 'application/json', 'authorization': 'Bearer ' + self.current_token})

            userOpn = urllib.request.urlopen(userReq)
            userRes = json.load(userOpn)
            userOpn.close()
        except urllib.error.URLError as urlError:
            print("Error during user info request: " + str(urlError.reason))
            return False
        except urllib.error.HTTPError as httpError:
            print("Error during user info request: " + str(httpError.reason))
            return False
        except:
            userInfoErr = sys.exc_info()[0]
            print("Error during user info request: " + userInfoErr.message)
            return False


        print("User Info obtained.")
        print("User didDonate: " + str(userRes['didDonate']))

        # Check if donated
        if not userRes['didDonate']:
            print("Error!  User must donate for this to work.")
            return False

        print("User donationExpire: " + str(userRes['donationExpire'] / 1000))

        # Check if donation has expired
        if ((userRes['donationExpire'] / 1000) < int(time.time())):
            print("Error!  User's donation ad-free period has expired.")
            return False


        # Check for user's location
        print("Getting user location...")

        if self.current_location is None:
            try:
                # get current location
                geoReq = urllib.request.Request('https://get.geojs.io/v1/ip/geo.json')
                geoOpn = urllib.request.urlopen(geoReq)
                geoRes = json.load(geoOpn)
                geoOpn.close()
            except urllib.error.URLError as urlError:
                print("Error during geo IP acquisition: " + str(urlError.reason))
                return False
            except urllib.error.HTTPError as httpError:
                print("Error during geo IP acquisition: " + str(httpError.reason))
                return False
            except:
                geoIpErr = sys.exc_info()[0]
                print("Error during geo IP acquisition: " + geoIpErr.message)
                return False
            print("User location obtained as " + geoRes['latitude'] + '/' + geoRes['longitude'])
            self.current_location = geoRes


        # See if we have a market available to the user
        if self.current_dma is None:
            print("Getting user's media market (DMA)...")

            try:
                # https://api.locastnet.org/api/watch/dma/40.543034399999996/-75.42280769999999
                # returns dma - local market
                dmaReq = urllib.request.Request('https://api.locastnet.org/api/watch/dma/' + 
                                            self.current_location['latitude'] + '/' + 
                                            self.current_location['longitude'], 
                                        headers={'Content-Type': 'application/json'})

                dmaOpn = urllib.request.urlopen(dmaReq)
                dmaRes = json.load(dmaOpn)
                dmaOpn.close()
            except urllib.error.URLError as urlError:
                print("Error when getting the users's DMA: " + str(urlError.reason))
                return False
            except urllib.error.HTTPError as httpError:
                print("Error when getting the users's DMA: " + str(httpError.reason))
                return False
            except:
                dmaErr = sys.exc_info()[0]
                print("Error when getting the users's DMA: " + dmaErr.message)
                return False

            print("DMA found as " + dmaRes['DMA'] + ": " + dmaRes['name'])

            if (dmaRes['active'] == False):
                print("DMA not available in Locast yet.  Exiting...")
                return False

            self.current_dma = dmaRes['DMA']


        return True






    def get_stations(self):

        # TODO: check if we dont return any results

        print("Getting list of stations based on DMA...")

        try:
            # https://api.locastnet.org/api/watch/epg/504
            # get stations
            stationsReq = urllib.request.Request('https://api.locastnet.org/api/watch/epg/' + str(self.current_dma), 
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

        with open(self.base_data_folder + "tv_stations.json", "r") as fcc_station_file_obj:
            fcc_stations = json.load(fcc_station_file_obj)
            with open("fcc_dma_markets.json", "r") as fcc_dma_file_obj:
                dma_mapping = json.load(fcc_dma_file_obj)

            try:
                fcc_market = dma_mapping[str(self.current_dma)]
            except KeyError:
                print("No DMA to FCC mapping found.  Poke the developer to get it into locast2plex.")
                return False



        with open(self.base_data_folder + 'known_stations.json', "r") as known_stations_file_obj:
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
                if ks_result != None:
                    stationsRes[index]['channel'] = ks_result['channel']
                    skip_sub_id = ks_result['skip_sub']


                # then check "name"
                if (not 'channel' in stationsRes[index]):
                    ks_result = self.find_known_station(locast_station, 'name', known_stations)
                    if ks_result != None:
                        stationsRes[index]['channel'] = ks_result['channel']
                        skip_sub_id = ks_result['skip_sub']


                # if we couldn't find anything look through fcc list for a match.
                # first by searching the callsign found in the "callsign" field
                if (not 'channel' in stationsRes[index]) and callsign_result['verified']:
                    result = self.find_fcc_station(callsign_result['callsign'], fcc_market, fcc_stations)
                    if result != None:
                        stationsRes[index]['channel'] = result['channel']
                        skip_sub_id = result['analog']

                
                # if we still couldn't find it, see if there's a match via the
                # "name" field
                if (not 'channel' in stationsRes[index]) and alt_callsign_result['verified']:
                    result = self.find_fcc_station(alt_callsign_result['callsign'], fcc_market, fcc_stations)
                    if result != None:
                        stationsRes[index]['channel'] = result['channel']
                        skip_sub_id = result['analog']

                            
                # locast usually adds a number in it's callsign (in either field).  that
                # number is the subchannel
                if (not skip_sub_id) and ('channel' in stationsRes[index]):
                    if callsign_result['verified'] and (callsign_result['subchannel'] != None):
                        stationsRes[index]['channel'] = stationsRes[index]['channel'] + '.' + callsign_result['subchannel']
                    elif alt_callsign_result['verified'] and (alt_callsign_result['subchannel'] != None):
                        stationsRes[index]['channel'] = stationsRes[index]['channel'] + '.' + alt_callsign_result['subchannel']
                    else:
                        stationsRes[index]['channel'] = stationsRes[index]['channel'] + '.1'


                # mark stations that did not get a channel, but outside of the normal range.
                # the user will have to weed these out in Plex...
                if (not 'channel' in stationsRes[index]):
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
        if ( ((compare_string[0] == 'K') or (compare_string[0] == 'W')) and 
             ((len(compare_string) == 3) or (len(compare_string) == 4)) ):
            verified = True

        return {
            "verified": verified,
            "station_type": station_type,
            "subchannel": subchannel,
            "callsign": compare_string
        }





    def find_known_station(self, station, searchBy, known_stations):

        for known_station in known_stations:
            if ( (known_station[searchBy] == station[searchBy]) and 
                 (known_station['dma'] == station['dma']) ):

                returnChannel = known_station['rootChannel']

                if known_station['subChannel'] != None:
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
                                                self.current_location['latitude'] + '/' + 
                                                self.current_location['longitude'], 
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
                if bestStream == None:
                    bestStream = videoStream

                elif ((videoStream.stream_info.resolution[0] > bestStream.stream_info.resolution[0]) and 
                    (videoStream.stream_info.resolution[1] > bestStream.stream_info.resolution[1])):
                    bestStream = videoStream

                elif ((videoStream.stream_info.resolution[0] == bestStream.stream_info.resolution[0]) and 
                    (videoStream.stream_info.resolution[1] == bestStream.stream_info.resolution[1]) and
                    (videoStream.stream_info.bandwidth > bestStream.stream_info.bandwidth)):
                    bestStream = videoStream
        

            if bestStream != None:
                print(station_id + " will use " +
                        str(bestStream.stream_info.resolution[0]) + "x" + str(bestStream.stream_info.resolution[1]) + 
                        " resolution at " + str(bestStream.stream_info.bandwidth) + "bps")

                return bestStream.absolute_uri

        else:
            print("No variant streams found for this station.  Assuming single stream only.")
            return videoUrlRes['streamUrl']

