import json, urllib2, subprocess, time, os, sys
import m3u8


# set to directory of script
os.chdir(os.path.dirname(os.path.abspath(__file__)))


CONFIG_LOCAST_USERNAME = os.getenv('username')
CONFIG_LOCAST_PASSWORD = os.getenv('password')
CONFIG_LISTEN_ADDY = os.getenv("listen_addy")
CURRENT_VERSION = "0.1.0"



print("Locast2Plex v" + CURRENT_VERSION)



telly_proc = None
current_token = None




def locast_login():
    # login
    print("Logging into Locast using username " + CONFIG_LOCAST_USERNAME + "...")

    # https://api.locastnet.org/api/user/login
    # POST
    # {"username":"thomas_vg1@hotmail.com","password":"xxxxxxxx"}

    try:
        loginReq = urllib2.Request('https://api.locastnet.org/api/user/login', 
                                '{"username":"' + CONFIG_LOCAST_USERNAME + '","password":"' + CONFIG_LOCAST_PASSWORD + '"}',
                                {'Content-Type': 'application/json'})

        loginOpn = urllib2.urlopen(loginReq)
        loginRes = json.load(loginOpn)
        loginOpn.close()
    except Exception as loginErr:
        print("Error during login: " + loginErr.message)
        return False

    current_token = loginRes["token"]
    return True





def validate_user():
    print("Validating User Info...")

    try:
        # get user info and make sure we donated
        userReq = urllib2.Request('https://api.locastnet.org/api/user/me', 
                                headers={'Content-Type': 'application/json', 'authorization': 'Bearer ' + current_token})

        userOpn = urllib2.urlopen(userReq)
        userRes = json.load(userOpn)
        userOpn.close()
    except Exception as userInfoErr:
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

    return True






def generate_m3u():
    print("Opening/Creating locastChannels.m3u8...")

    # video list
    outputFile = open("locastChannels.m3u8", "w")

    outputFile.write("#EXTM3U\n")
    outputFile.write("#EXT-X-VERSION:3\n")



    print("Getting user location...")

    try:
        # get current location
        geoReq = urllib2.Request('https://get.geojs.io/v1/ip/geo.json')
        geoOpn = urllib2.urlopen(geoReq)
        geoRes = json.load(geoOpn)
        geoOpn.close()
    except Exception as geoIpErr:
        print("Error during geo IP acquisition: " + geoIpErr.message)
        print("Exiting...")
        exit()


    # TODO: Save this so we don't have to keep looking hitting the api


    print("Getting user's media market (DMA)...")

    try:
        # https://api.locastnet.org/api/watch/dma/40.543034399999996/-75.42280769999999
        # returns dma - local market
        dmaReq = urllib2.Request('https://api.locastnet.org/api/watch/dma/' + geoRes['latitude'] + '/' + geoRes['longitude'], 
                                headers={'Content-Type': 'application/json'})

        dmaOpn = urllib2.urlopen(dmaReq)
        dmaRes = json.load(dmaOpn)
        dmaOpn.close()
    except Exception as dmaErr:
        print("Error when getting the users's DMA: " + dmaErr.message)
        print("Exiting...")
        exit()


    # TODO: check if we dont return any results



    print("Getting list of stations based on DMA...")

    try:
        # https://api.locastnet.org/api/watch/epg/504
        # get stations
        stationsReq = urllib2.Request('https://api.locastnet.org/api/watch/epg/' + dmaRes['DMA'], 
                                    headers={'Content-Type': 'application/json',
                                            'authorization': 'Bearer ' + current_token})

        stationsOpn = urllib2.urlopen(stationsReq)
        stationsRes = json.load(stationsOpn)
        stationsOpn.close()
    except Exception as stationErr:
        print("Error when getting the list of stations: " + stationErr.message)
        print("Exiting...")
        exit()




    # get station video URLS
    for station in stationsRes:

        print("Getting station info for " + station['name'] + "...")

        try:
            videoUrlReq = urllib2.Request('https://api.locastnet.org/api/watch/station/' + 
                                                str(station['id']) + '/' + 
                                                geoRes['latitude'] + '/' + 
                                                geoRes['longitude'], 
                                        headers={'Content-Type': 'application/json',
                                                    'authorization': 'Bearer ' + current_token})
            videoUrlOpn = urllib2.urlopen(videoUrlReq)
            videoUrlRes = json.load(videoUrlOpn)
            videoUrlOpn.close()
        except Exception as videoUrlReqErr:
            print("Error when getting the video URL: " + videoUrlReqErr.message)
            print("Exiting...")
            exit()

        print("Determining best video stream for " + station['name'] + "...")

        bestStream = None
        
        # find the heighest stream url resolution and save it to the list
        videoUrlM3u = m3u8.load(videoUrlRes['streamUrl'])
        
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

        print(station['name'] + " will use " + 
                str(bestStream.stream_info.resolution[0]) + "x" + str(bestStream.stream_info.resolution[1]) + 
                " resolution at " + str(bestStream.stream_info.bandwidth) + "bps")

        outputFile.write('#EXTINF:-1 tvg-id="' + station['name'] + '" tvg-name="' + station['name'] + '" tvg-logo="' + station['logoUrl'] + '" ,' + station['name'] + "\n")
        outputFile.write(bestStream.absolute_uri + "\n")

    outputFile.close()




def run_telly():
    # run Telly
    print("Running Telly.  Configured to run on IP " + CONFIG_LISTEN_ADDY + "...")

    # ./telly -b 192.168.29.222:6077
    telly_proc = subprocess.Popen(["./telly", "-b", CONFIG_LISTEN_ADDY + ":6077"])






def the_whole_shebang():
    if (not locast_login()) or (not validate_user()):
        print("Exiting...")
        exit()
    else:
        generate_m3u()
        run_telly()





the_whole_shebang()



while True:
    # check every 30 mins
    time.sleep(1800)

    # check on the user.  if something's wrong (hopefully only that user login expired)
    # then quit telly and restart the login
    if not validate_user():
        # make sure we're terminating a running process
        if telly_proc.poll() is None:
            telly_proc.terminate()

        the_whole_shebang()
        