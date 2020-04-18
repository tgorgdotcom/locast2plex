import json, urllib2, subprocess, time, os, sys
import m3u8
from nbstreamreader import NonBlockingStreamReader as NBSR


# set to directory of script
os.chdir(os.path.dirname(os.path.abspath(__file__)))


DEBUG_MODE = os.getenv('debug', False)
CONFIG_LOCAST_USERNAME = os.getenv('username', '')
CONFIG_LOCAST_PASSWORD = os.getenv('password', '')
CONFIG_LISTEN_ADDY = os.getenv("listen_addy", '127.0.0.1')
CURRENT_VERSION = "0.2.3"



print("Locast2Plex v" + CURRENT_VERSION)
if DEBUG_MODE:
    print("DEBUG MODE ACTIVE")


# check environment vars
if (CONFIG_LOCAST_USERNAME == ''):
    print("Usernanme not specified.  Exiting...")
    exit()

if (CONFIG_LOCAST_PASSWORD == ''):
    print("Password not specified.  Exiting...")
    exit()

# make sure we don't just let any value be set for this...
if (DEBUG_MODE != False):
    DEBUG_MODE = True


# TODO: Validate IP


telly_proc = None
telly_stream = None
current_token = None
current_location = None
current_dma = None
current_station_list = None
current_stream_urls = {}





def locast_login():
    global current_token
    
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

    return True






def generate_m3u():
    global current_location, current_dma, current_station_list, current_stream_urls

    print("Opening/Creating locastChannels.m3u8...")

    # video list
    outputFile = open("locastChannels.m3u8", "w")

    outputFile.write("#EXTM3U\n")
    outputFile.write("#EXT-X-VERSION:3\n")



    print("Getting user location...")

    if current_location is None:
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
        current_location = geoRes


    # TODO: Save this so we don't have to keep looking hitting the api

    if current_dma is None:
        print("Getting user's media market (DMA)...")

        try:
            # https://api.locastnet.org/api/watch/dma/40.543034399999996/-75.42280769999999
            # returns dma - local market
            dmaReq = urllib2.Request('https://api.locastnet.org/api/watch/dma/' + current_location['latitude'] + '/' + current_location['longitude'], 
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
        current_dma = dmaRes['DMA']


    # TODO: check if we dont return any results



    if current_station_list is None:
        print("Getting list of stations based on DMA...")

        try:
            # https://api.locastnet.org/api/watch/epg/504
            # get stations
            stationsReq = urllib2.Request('https://api.locastnet.org/api/watch/epg/' + current_dma, 
                                         headers={'Content-Type': 'application/json',
                                                  'authorization': 'Bearer ' + current_token})

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

        current_station_list = stationsRes

    # TODO: Convert epg to xml




    # get station video URLS
    for station in current_station_list:

        print("Getting station info for " + station['name'] + "...")

        try:
            videoUrlReq = urllib2.Request('https://api.locastnet.org/api/watch/station/' + 
                                                str(station['id']) + '/' + 
                                                current_location['latitude'] + '/' + 
                                                current_location['longitude'], 
                                          headers={'Content-Type': 'application/json',
                                                   'authorization': 'Bearer ' + current_token})
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

        current_stream_urls[station['name']] = bestStream.absolute_uri

    outputFile.close()
    return True




def run_telly():
    global telly_proc, telly_stream

    # run Telly
    print("Running Telly.  Configured to run on IP " + CONFIG_LISTEN_ADDY + "...")

    # ./telly -b 192.168.29.222:6077
    telly_proc = subprocess.Popen(["./telly", "-b", CONFIG_LISTEN_ADDY + ":6077"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    telly_stream = NBSR(telly_proc.stdout)




def clean_exit():
    sys.stderr.flush()
    sys.stdout.flush()
    os._exit(0)




if (not locast_login()) or (not validate_user()) or (not generate_m3u()):
    print("Exiting...")
    clean_exit()
else:
    run_telly()



telly_video_processing = False
restart_telly = False
quit_app = False


# check every 1.5 hours
check_time = int(time.time()) + (240 if DEBUG_MODE else 5400)

while True:

    # check if telly is still running.  if not, exit the script as well
    if not (telly_proc.poll() is None):
        print("Telly process failed.  Exiting...")
        clean_exit()

    # if we're supposed to restart telly, and we're not processing video anymore, restart telly
    if (not telly_video_processing) and restart_telly:
        telly_proc.terminate()
        run_telly()
        restart_telly = False

    # if we're supposed to quit completely, then exit
    if (not telly_video_processing) and quit_app:
        telly_proc.terminate()
        clean_exit()


    # get the telly output, forwarding it to stdout, and checking to see if we're running a stream
    try:
        output_line = telly_stream.readline(0.1)

        if not output_line is None:
            print(output_line),
            if "Serving channel number" in output_line:
                telly_video_processing = True
            elif "Stopped streaming" in output_line:
                telly_video_processing = False
            # TODO: check if we're processing a stream via ffmpeg
    except:
        pass
        

    
    if (int(time.time()) > check_time):

        print("Check time triggered and video is not processing - running checks...")

        # check on the user.  if something's wrong (donation, etc), then exit
        if not validate_user():
            print("Will check if a login fixes the issue...")
            if not locast_login(): # try logging in again, to be sure
                quit_app = True
            else:
                print("Login OK!  Lets see if we can validate now...")
                if not validate_user():  # if login worked, try validation one last time
                    quit_app = True


        # check if the stream urls changed.  if so, reset the telly process if there's no processing being done
        print("Checking for new stream URLS...")

        old_stream_list = current_stream_urls.copy()
        
        if generate_m3u():
            if cmp(current_stream_urls, old_stream_list) != 0:
                print("NEW URLS DETECTED.  RESTARTING TELLY...")
                restart_telly = True
            else:
                print("URLS are the same, nothing to worry about...")
        else:
            quit_app = True

        check_time = int(time.time()) + (240 if DEBUG_MODE else 5400)
        
        