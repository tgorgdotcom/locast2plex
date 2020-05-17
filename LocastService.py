import json, urllib2, time, os, sys
import m3u8



class LocastService:

    current_token = None
    current_location = None
    current_dma = None
    fcc_station_file_path = None



    def __init__(self, station_file_path):
        self.fcc_station_file_path = station_file_path



    def login(self, username, password):

        # login
        print("Logging into Locast using username " + username + "...")

        # https://api.locastnet.org/api/user/login
        # POST
        # {"username":"thomas_vg1@hotmail.com","password":"xxxxxxxx"}

        try:
            loginReq = urllib2.Request('https://api.locastnet.org/api/user/login', 
                                        '{"username":"' + username + '","password":"' + password + '"}',
                                        {'Content-Type': 'application/json'})

            loginOpn = urllib2.urlopen(loginReq)
            loginRes = json.load(loginOpn)
            loginOpn.close()
        except urllib2.URLError as urlError:
            print("Error during login: " + str(urlError.reason))
            return False
        except urllib2.HTTPError as httpError:
            print("Error during login: " + str(httpError.reason))
            return False
        except:
            loginErr = sys.exc_info()[0]
            print("Error during login: " + loginErr.message)
            return False

        print("Logon token is " + loginRes["token"])
        self.current_token = loginRes["token"]
        return True





    def validate_user(self):
        print("Validating User Info...")

        try:
            # get user info and make sure we donated
            userReq = urllib2.Request('https://api.locastnet.org/api/user/me', 
                                    headers={'Content-Type': 'application/json', 'authorization': 'Bearer ' + self.current_token})

            userOpn = urllib2.urlopen(userReq)
            userRes = json.load(userOpn)
            userOpn.close()
        except urllib2.URLError as urlError:
            print("Error during user info request: " + str(urlError.reason))
            return False
        except urllib2.HTTPError as httpError:
            print("Error during user info request: " + str(httpError.reason))
            return False
        except:
            userInfoErr = sys.exc_info()[0]
            print("Error during user info request: " + userInfoErr.message)
            return False


        print("User Info obtained.")
        print("User didDonate: " + str(userRes['didDonate']))
        print("User donationExpire: " + str(userRes['donationExpire'] / 1000))


        # Check if donated
        if not userRes['didDonate']:
            print("Error!  User must donate for this to work.")
            return False
        # Check if donation has expired
        elif ((userRes['donationExpire'] / 1000) < int(time.time())):
            print("Error!  User's donation ad-free period has expired.")
            return False


        # Check for user's location
        print("Getting user location...")

        if self.current_location is None:
            try:
                # get current location
                geoReq = urllib2.Request('https://get.geojs.io/v1/ip/geo.json')
                geoOpn = urllib2.urlopen(geoReq)
                geoRes = json.load(geoOpn)
                geoOpn.close()
            except urllib2.URLError as urlError:
                print("Error during geo IP acquisition: " + str(urlError.reason))
                return False
            except urllib2.HTTPError as httpError:
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
                dmaReq = urllib2.Request('https://api.locastnet.org/api/watch/dma/' + 
                                            self.current_location['latitude'] + '/' + 
                                            self.current_location['longitude'], 
                                        headers={'Content-Type': 'application/json'})

                dmaOpn = urllib2.urlopen(dmaReq)
                dmaRes = json.load(dmaOpn)
                dmaOpn.close()
            except urllib2.URLError as urlError:
                print("Error when getting the users's DMA: " + str(urlError.reason))
                return False
            except urllib2.HTTPError as httpError:
                print("Error when getting the users's DMA: " + str(httpError.reason))
                return False
            except:
                dmaErr = sys.exc_info()[0]
                print("Error when getting the users's DMA: " + dmaErr.message)
                return False

            print("DMA found as " + dmaRes['DMA'])
            self.current_dma = dmaRes['DMA']


        return True






    def get_stations(self):

        # TODO: check if we dont return any results

        print("Getting list of stations based on DMA...")

        try:
            # https://api.locastnet.org/api/watch/epg/504
            # get stations
            stationsReq = urllib2.Request('https://api.locastnet.org/api/watch/epg/' + str(self.current_dma), 
                                        headers={'Content-Type': 'application/json',
                                                'authorization': 'Bearer ' + self.current_token})

            stationsOpn = urllib2.urlopen(stationsReq)
            stationsRes = json.load(stationsOpn)
            stationsOpn.close()

        except urllib2.URLError as urlError:
            print("Error when getting the list of stations: " + str(urlError.reason))
            return False
        except urllib2.HTTPError as httpError:
            print("Error when getting the list of stations: " + str(httpError.reason))
            return False
        except:
            stationErr = sys.exc_info()[0]
            print("Error when getting the list of stations: " + stationErr.message)
            return False

        # get the actual channel number by comparing the callsign with
        # the FCC facilities list
        print("Loading FCC Stations list...")

        with open(self.fcc_station_file_path, "r") as fcc_station_file_obj:
            fcc_stations = json.load(fcc_station_file_obj)
            with open("fcc_dma_markets.json", "r") as fcc_dma_file_obj:
                dma_mapping = json.load(fcc_dma_file_obj)
            fcc_market = dma_mapping[str(self.current_dma)]


        for fcc_station in fcc_stations:
            # go through each possible station
            if (fcc_station['nielsen_dma'] == fcc_market) or (fcc_station['nielsen_dma'] == ""):
                for index, locast_station in enumerate(stationsRes):
                    # if we have a callsign match, add the channel
                    if fcc_station['fac_callsign'].startswith(locast_station['callSign'][0:3]):
                        skip_sub_id = False
                        if fcc_station['tv_virtual_channel'] != "":
                            stationsRes[index]['channel'] = fcc_station['tv_virtual_channel']
                        else:
                            stationsRes[index]['channel'] = fcc_station['fac_channel']
                            skip_sub_id = True
                        
                        # locast usually adds a number after subchannels in it's callsign.  get the 
                        # numeric value and append it to the channel value
                        # TODO: don't add a substation if it's an analog channel
                        if not skip_sub_id:
                            if (len(locast_station['callSign']) > 4):
                                stationsRes[index]['channel'] = stationsRes[index]['channel'] + '.' + locast_station['callSign'][4:]
                            else:
                                stationsRes[index]['channel'] = stationsRes[index]['channel'] + '.1'

        
        # mark stations that did not get a channel, but outside of the normal range.
        # the user will have to weed these out in Plex...
        noneChannel = 1000

        for index, locast_station in enumerate(stationsRes):
            if locast_station['channel'] == None:
                stationsRes[index]['channel'] = str(noneChannel)
                noneChannel = noneChannel + 1

        return stationsRes





    def get_station_stream_uri(self, station_id):
        print("Getting station info for " + station_id + "...")

        try:
            videoUrlReq = urllib2.Request('https://api.locastnet.org/api/watch/station/' + 
                                                str(station_id) + '/' + 
                                                self.current_location['latitude'] + '/' + 
                                                self.current_location['longitude'], 
                                            headers={'Content-Type': 'application/json',
                                                    'authorization': 'Bearer ' + self.current_token})
            videoUrlOpn = urllib2.urlopen(videoUrlReq)
            videoUrlRes = json.load(videoUrlOpn)
            videoUrlOpn.close()
        except urllib2.URLError as urlError:
            print("Error when getting the video URL: " + str(urlError.reason))
            return False
        except urllib2.HTTPError as httpError:
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
            print("No streams found for this station.  Skipping...")
            return False

