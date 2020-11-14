# pylama:ignore=E722,E303,E302,E305
import subprocess
import os
import re
import sys
import random
import threading
import socket
import time
import errno
import configparser
from http.server import BaseHTTPRequestHandler, HTTPServer
from multiprocessing import Process

import LocastService
import SSDPServer
from templates import templates





def clean_exit():
    sys.stderr.flush()
    sys.stdout.flush()
    os._exit(0)





# from https://stackoverflow.com/a/43880536
def is_docker():
    path = "/proc/self/cgroup"
    if not os.path.isfile(path):
        return False
    with open(path) as f:
        for line in f:
            if re.match("\d+:[\w=]+:/docker(-[ce]e)?/\w+", line):
                return True
        return False





# with help from https://www.acmesystems.it/python_http
# and https://stackoverflow.com/questions/21631799/how-can-i-pass-parameters-to-a-requesthandler
class PlexHttpHandler(BaseHTTPRequestHandler):

    # using class variables since this should only be set once
    host_address = ""
    host_port = ""
    uuid = ""
    reporting_model = ""
    reporting_firmware_name = ""
    reporting_firmware_ver = ""
    tuner_count = 3
    templates = {}
    station_scan = False
    station_list = {}
    local_locast = None
    bytes_per_read = 1024000

    def do_GET(self):
        base_url = self.host_address + ':' + self.host_port

        # paths and logic mostly pulled from telly:routes.go: https://github.com/tellytv/telly
        if (self.path == '/') or (self.path == '/device.xml'):
            self.send_response(200)
            self.send_header('Content-type', 'application/xml')
            self.end_headers()
            self.wfile.write(self.templates['xmlDiscover'].format(self.reporting_model, self.uuid, base_url).encode('utf-8'))

        elif self.path == '/discover.json':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(self.templates['jsonDiscover'].format(self.reporting_model,
                                                                   self.reporting_firmware_name,
                                                                   self.tuner_count,
                                                                   self.reporting_firmware_ver,
                                                                   self.uuid,
                                                                   base_url).encode('utf-8'))

        elif self.path == '/lineup_status.json':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            if self.station_scan:
                self.wfile.write(self.templates['jsonLineupStatus'].encode('utf-8'))
            else:
                self.wfile.write(self.templates['jsonLineupComplete'].encode('utf-8'))

        elif self.path == '/lineup.json':  # TODO
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            returnJSON = ''
            for index, station_item in enumerate(self.station_list):
                returnJSON = returnJSON + self.templates['jsonLineupItem'].format(station_item['channel'], station_item['name'], base_url + '/watch/' + str(station_item['id']))
                if (index + 1) != len(self.station_list):
                    returnJSON = returnJSON + ','

            returnJSON = "[" + returnJSON + "]"
            self.wfile.write(returnJSON.encode('utf-8'))

        elif self.path == '/lineup.xml':  # TODO
            self.send_response(200)
            self.send_header('Content-type', 'application/xml')
            self.end_headers()
            returnXML = ''
            for station_item in self.station_list:
                returnXML = returnXML + self.templates['xmlLineupItem'].format(station_item['channel'], station_item['name'], base_url + '/watch/' + str(station_item['id']))
            returnXML = "<Lineup>" + returnXML + "</Lineup>"
            self.wfile.write(returnXML.encode('utf-8'))

        elif self.path.startswith('/watch'):
            channelId = self.path.replace('/watch/', '')
            channelUri = self.local_locast.get_station_stream_uri(channelId)

            self.send_response(200)
            self.send_header('Content-type', 'video/mpeg; codecs="avc1.4D401E')
            self.end_headers()

            ffmpeg_proc = subprocess.Popen(["ffmpeg", "-i", channelUri, "-user_agent", "'Mozilla/5.0'", "-codec", "copy", "-f", "mpegts", "pipe:1"], stdout=subprocess.PIPE)


            # get initial videodata. if that works, then keep grabbing it
            videoData = ffmpeg_proc.stdout.read(self.bytes_per_read)

            while True:
                if not videoData:
                    break
                else:
                    # from https://stackoverflow.com/questions/9932332
                    try:
                        self.wfile.write(videoData)
                        time.sleep(0.1)
                    except IOError as e:
                        # Check we hit a broken pipe when trying to write back to the client
                        if e.errno == errno.EPIPE:
                            # Send SIGTERM to shutdown ffmpeg
                            ffmpeg_proc.terminate()
                            # ffmpeg writes a bit of data out to stderr after it terminates,
                            # need to read any hanging data to prevent a zombie process.
                            ffmpeg_proc.communicate()
                            break
                        else:
                            raise


                videoData = ffmpeg_proc.stdout.read(self.bytes_per_read)

            ffmpeg_proc.terminate()
            ffmpeg_proc.communicate()



        # elif self.path == '/epg.xml':
        #     self.send_response(200)
        #     self.send_header('Content-type','application/xml')
        #     self.end_headers()

        elif self.path == '/debug.json':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

        else:
            print("Unknown request to " + self.path)
            self.send_response(501)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.templates['htmlError'].format('501 - Not Implemented').encode('utf-8'))

        return





    def do_POST(self):

        contentPath = self.path
        queryData = {}

        if self.headers.get('Content-Length') != '0':
            postdata = self.rfile.read(int(self.headers.get('Content-Length')))
            postdataElements = postdata.split('&')

            for postdataItem in postdataElements:
                postdataItemSplit = postdataItem.split('=')
                if len(postdataItemSplit) > 1:
                    queryData[postdataItemSplit[0]] = postdataItemSplit[1]

        if self.path.find('?') != -1:
            contentPath = self.path[0:self.path.find('?')]
            getdata = self.path[(self.path.find('?') + 1):]
            getdataElements = getdata.split('&')

            for getdataItem in getdataElements:
                getdataItemSplit = getdataItem.split('=')
                if len(getdataItemSplit) > 1:
                    queryData[getdataItemSplit[0]] = getdataItemSplit[1]


        if contentPath == '/lineup.post':
            if queryData['scan'] == 'start':
                self.station_scan = True

                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()

                self.station_list = locast.get_stations()
                self.station_scan = False

            elif queryData['scan'] == 'abort':
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
            else:
                print("Unknown scan command " + queryData['scan'])
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(self.templates['htmlError'].format(queryData['scan'] + ' is not a valid scan command').encode('utf-8'))

        else:
            print("Unknown request to " + contentPath)

        return





# mostly from https://github.com/ZeWaren/python-upnp-ssdp-example
# and https://stackoverflow.com/questions/46210672/python-2-7-streaming-http-server-supporting-multiple-connections-on-one-port
class PlexHttpServer(threading.Thread):

    def __init__(self, serverSocket, config, templates, station_list, locast_service):
        threading.Thread.__init__(self)

        PlexHttpHandler.host_address = config["host"][0]
        PlexHttpHandler.host_port = config["host"][1]
        PlexHttpHandler.uuid = config["uuid"]
        PlexHttpHandler.tuner_count = config["tuner_count"]
        PlexHttpHandler.bytes_per_read = config["bytes_per_read"]
        PlexHttpHandler.templates = templates
        PlexHttpHandler.station_list = station_list
        PlexHttpHandler.local_locast = locast_service
        PlexHttpHandler.reporting_model = config["reporting_model"]
        PlexHttpHandler.reporting_firmware_name = config["reporting_firmware_name"]
        PlexHttpHandler.reporting_firmware_ver = config["reporting_firmware_ver"]

        self.listen_address = config["listen"][0]
        self.listen_port = config["listen"][1]
        self.socket = serverSocket
        self.daemon = True
        self.start()

    def run(self):
        httpd = HTTPServer((self.listen_address, int(self.listen_port)), PlexHttpHandler, False)
        httpd.socket = self.socket
        httpd.server_bind = self.server_close = lambda self: None

        httpd.serve_forever()





# mostly from https://github.com/ZeWaren/python-upnp-ssdp-example
def ssdpServerProcess(address, port, uuid):
    ssdp = SSDPServer.SSDPServer()
    ssdp.register('local',
                  'uuid:' + uuid + '::upnp:rootdevice',
                  'upnp:rootdevice',
                  'http://' + address + ':' + port + '/device.xml')
    try:
        ssdp.run()
    except KeyboardInterrupt:
        pass





# Startup Logic
if __name__ == '__main__':

    # set to directory of script
    os.chdir(os.path.dirname(os.path.abspath(__file__)))


    config = {
        'locast_username': None,
        'locast_password': None,
        'override_latitude': None,
        'override_longitude': None,
        'override_zipcode': None,
        'bytes_per_read': '1152000',
        'plex_accessible_ip': '0.0.0.0',
        'plex_accessible_port': '6077',
        'tuner_count': '3',
        'uuid': None,
        'reporting_model': 'HDHR3-US',
        'reporting_firmware_name': 'hdhomerun3_atsc',
        'reporting_firmware_ver': '20150826',
        'concurrent_listeners': '10'  # to convert
    }

    config_handler = configparser.RawConfigParser()
    if os.path.exists('config/config.ini'):
        config_handler.read('config/config.ini')
    else:
        config_handler.read('config.ini')

    try:
        for option_name in config_handler.options("main"):
            config[option_name] = config_handler.get("main", option_name)
    except:
        pass

    LISTEN_ADDY = "0.0.0.0"
    LISTEN_PORT = "6077"
    CURRENT_VERSION = "0.5.3"
    DEVICE_UUID = config["uuid"]
    CONCURRENT_LISTENERS = int(config["concurrent_listeners"])
    TUNER_COUNT = int(config["tuner_count"])

    if (TUNER_COUNT > 4) or (TUNER_COUNT < 1):
        print("Tuner count set outside of 1-4 range.  Setting to default")
        TUNER_COUNT = 3

    LOCAST_USERNAME = config["locast_username"]
    LOCAST_PASSWORD = config["locast_password"]
    HOST_PORT = config["plex_accessible_port"]
    HOST_ADDY = config["plex_accessible_ip"]
    BYTES_PER_READ = int(config["bytes_per_read"])
    OVERRIDE_LATITUDE = config["override_latitude"]
    OVERRIDE_LONGITUDE = config["override_longitude"]
    OVERRIDE_ZIPCODE = config["override_zipcode"]
    REPORTING_MODEL = config["reporting_model"]
    REPORTING_FIRMWARE_NAME = config["reporting_firmware_name"]
    REPORTING_FIRMWARE_VER = config["reporting_firmware_ver"]

    # docker users only configure the outside port, but for those running in command line/terminal
    # these will be the same
    if not is_docker():
        LISTEN_PORT = HOST_PORT
        LISTEN_ADDY = HOST_ADDY


    print("Locast2Plex v" + CURRENT_VERSION)

    print("Tuner count set to " + str(TUNER_COUNT))

    # generate UUID here for when we are not using docker
    if DEVICE_UUID is None:
        print("No UUID found.  Generating one now...")
        # from https://pynative.com/python-generate-random-string/
        # create a string that wouldn't be a real device uuid for
        DEVICE_UUID = ''.join(random.choice("hijklmnopqrstuvwxyz") for i in range(8))
        config_handler.set('main', 'uuid', DEVICE_UUID)

        if os.path.exists('config/config.ini'):
            with open("config/config.ini", 'w') as config_file:
                config_handler.write(config_file)
        else:
            with open("config.ini", 'w') as config_file:
                config_handler.write(config_file)

    print("UUID set to: " + DEVICE_UUID + "...")


    ffmpeg_proc = None

    if (OVERRIDE_LATITUDE is not None) and (OVERRIDE_LONGITUDE is not None):
        mock_location = {
            "latitude": OVERRIDE_LATITUDE,
            "longitude": OVERRIDE_LONGITUDE
        }
    else:
        mock_location = None

    locast = LocastService.LocastService("./", mock_location, OVERRIDE_ZIPCODE)
    station_list = None


    if (not locast.login(LOCAST_USERNAME, LOCAST_PASSWORD)) or (not locast.validate_user()):
        print("Exiting...")
        clean_exit()
    else:
        station_list = locast.get_stations()

        try:
            print("Starting device server on " + config['plex_accessible_ip'] + ":" + config['plex_accessible_port'])
            serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            serverSocket.bind((LISTEN_ADDY, int(LISTEN_PORT)))
            serverSocket.listen(CONCURRENT_LISTENERS)

            config = {
                "host": (HOST_ADDY, HOST_PORT),
                "listen": (LISTEN_ADDY, LISTEN_PORT),
                "uuid": DEVICE_UUID,
                "tuner_count": TUNER_COUNT,
                "bytes_per_read": BYTES_PER_READ,
                "reporting_model": REPORTING_MODEL,
                "reporting_firmware_name": REPORTING_FIRMWARE_NAME,
                "reporting_firmware_ver": REPORTING_FIRMWARE_VER
            }

            for i in range(CONCURRENT_LISTENERS):
                PlexHttpServer(serverSocket, config, templates, station_list, locast)

            print("Starting SSDP server...")
            ssdpServer = Process(target=ssdpServerProcess, args=(HOST_ADDY, HOST_PORT, DEVICE_UUID))
            ssdpServer.daemon = True

            print("Locast2Plex is active and listening...")
            ssdpServer.start()

            # wait forever
            while True:
                time.sleep(3600)

        except KeyboardInterrupt:
            print('^C received, shutting down the server')
            clean_exit()
