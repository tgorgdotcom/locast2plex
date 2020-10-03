import subprocess
import threading
import time
import errno
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
import pathlib

from templates import templates


# with help from https://www.acmesystems.it/python_http
# and https://stackoverflow.com/questions/21631799/how-can-i-pass-parameters-to-a-requesthandler
class PlexHttpHandler(BaseHTTPRequestHandler):

    # using class variables since this should only be set once
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
        base_url = self.headers['Host']

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
                jsonlineupcomplete = self.templates['jsonLineupComplete'].replace("Antenna", self.tuner_type)
                self.wfile.write(jsonlineupcomplete.encode('utf-8'))

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

            ffmpetg_command = [self.ffpmeg_path,
                               "-i", channelUri,
                               "-c:v", "copy",
                               "-c:a", "copy",
                               "-f", "mpegts",
                               "-nostats", "-hide_banner",
                               "-loglevel", "warning",
                               "pipe:1"
                               ]

            ffmpeg_proc = subprocess.Popen(ffmpetg_command, stdout=subprocess.PIPE)

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
            try:
                ffmpeg_proc.communicate()
            except ValueError:
                print("Connection Closed")

        elif self.path == '/xmltv.xml':
            self.send_response(200)
            self.send_header('Content-type', 'application/xml')
            self.end_headers()

            dmafile = pathlib.Path(self.cache_dir).joinpath(str(self.location["DMA"]) + ".xml")
            with open(dmafile, 'rb') as file:
                self.wfile.write(file.read())

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

                self.station_list = self.local_locast.get_stations()
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

    def __init__(self, serverSocket, config, templates, station_list, locast_service, location):
        threading.Thread.__init__(self)

        PlexHttpHandler.uuid = config.config["main"]["uuid"]

        PlexHttpHandler.tuner_count = int(config.config["locast2plex"]["tuner_count"])
        self.listen_address = config.config["locast2plex"]["listen_address"]
        self.listen_port = config.config["locast2plex"]["listen_port"]

        PlexHttpHandler.ffpmeg_path = config.config["ffmpeg"]["ffmpeg_path"]
        PlexHttpHandler.bytes_per_read = int(config.config["ffmpeg"]["bytes_per_read"])

        PlexHttpHandler.reporting_model = config.config["dev"]["reporting_model"]
        PlexHttpHandler.reporting_firmware_name = config.config["dev"]["reporting_firmware_name"]
        PlexHttpHandler.reporting_firmware_ver = config.config["dev"]["reporting_firmware_ver"]
        PlexHttpHandler.tuner_type = config.config["dev"]["tuner_type"]

        PlexHttpHandler.templates = templates
        PlexHttpHandler.station_list = station_list
        PlexHttpHandler.local_locast = locast_service

        PlexHttpHandler.cache_dir = config.config["locast2plex"]["cache_dir"]
        PlexHttpHandler.location = location

        self.socket = serverSocket

        self.daemon = True
        self.start()

    def run(self):
        httpd = HTTPServer((self.listen_address, int(self.listen_port)), PlexHttpHandler, False)
        httpd.socket = self.socket
        httpd.server_bind = self.server_close = lambda self: None

        httpd.serve_forever()


def hdhrinterface_start(config, locast, station_list, location):
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serverSocket.bind((config.config["locast2plex"]['listen_address'],
                      int(config.config["locast2plex"]['listen_port'])))
    serverSocket.listen(int(config.config["locast2plex"]["concurrent_listeners"]))

    print("Now listening for requests.")
    for i in range(int(config.config["locast2plex"]["concurrent_listeners"])):
        PlexHttpServer(serverSocket, config, templates, station_list, locast, location)
