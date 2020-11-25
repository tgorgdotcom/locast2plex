import subprocess
import threading
import time
import errno
import socket
import urllib
import pathlib
from io import StringIO
from http.server import BaseHTTPRequestHandler, HTTPServer

import lib.stations as stations
import lib.epg2xml as epg2xml
import lib.channels_m3u as channels_m3u
from lib.templates import templates


# with help from https://www.acmesystems.it/python_http
# and https://stackoverflow.com/questions/21631799/how-can-i-pass-parameters-to-a-requesthandler
class PlexHttpHandler(BaseHTTPRequestHandler):

    # using class variables since this should only be set once
    config = None
    hdhr_station_scan = False
    rmg_station_scans = []
    local_locast = None
    location = None
        

    def do_GET(self):
        base_url = self.config['main']['plex_accessible_ip'] + ':' + self.config['main']['plex_accessible_port']

        contentPath = self.path
        queryData = {}

        if self.path.find('?') != -1:
            contentPath = self.path[0:self.path.find('?')]
            getdata = self.path[(self.path.find('?') + 1):]
            getdataElements = getdata.split('&')

            for getdataItem in getdataElements:
                getdataItemSplit = getdataItem.split('=')
                if len(getdataItemSplit) > 1:
                    queryData[getdataItemSplit[0]] = getdataItemSplit[1]

        # paths and logic mostly pulled from telly:routes.go: https://github.com/tellytv/telly
        if (contentPath == '/') and (not self.config['main']['use_old_plex_interface']):
            self.do_response(200, 
                             'application/xml', 
                             templates['xmlRmgIdentification'].format(self.config['main']['reporting_friendly_name']))
        
        elif (contentPath == '/') or (contentPath == '/device.xml'):
            templateName = 'xmlDiscover'

            if self.config['main']['use_old_plex_interface']:
                templateName = 'xmlDiscoverOld'

            self.do_response(200, 
                             'application/xml', 
                             templates[templateName].format(self.config['main']['reporting_friendly_name'],
                                                             self.config['main']['reporting_model'], 
                                                             self.config['main']['uuid'], 
                                                             base_url))

        elif contentPath == '/discover.json':
            self.do_response(200, 
                             'application/json', 
                             templates['jsonDiscover'].format(self.config['main']['reporting_friendly_name'],
                                                              self.config['main']['reporting_model'],
                                                              self.config['main']['reporting_firmware_name'],
                                                              self.config['main']['tuner_count'],
                                                              self.config['main']['reporting_firmware_ver'],
                                                              self.config['main']['uuid'],
                                                              base_url))

        elif contentPath == '/lineup_status.json':
            if self.hdhr_station_scan:
                returnJSON = templates['jsonLineupStatus']
            else:
                returnJSON = templates['jsonLineupComplete'].replace("Antenna", self.config['main']['tuner_type'])
                
            self.do_response(200, 'application/json', returnJSON)

        elif contentPath == '/lineup.json':  # TODO
            station_list = stations.get_dma_stations_and_channels(self.config, self.location)

            returnJSON = ''
            for index, list_key in enumerate(station_list):
                sid = str(list_key)
                returnJSON = returnJSON + templates['jsonLineupItem'].format(station_list[sid]['channel'], station_list[sid]['friendlyName'], base_url + '/watch/' + sid)
                if (index + 1) != len(station_list):
                    returnJSON = returnJSON + ','

            returnJSON = "[" + returnJSON + "]"
            self.do_response(200, 'application/json', returnJSON)

        elif contentPath == '/lineup.xml':  # TODO
            station_list = stations.get_dma_stations_and_channels(self.config, self.location)

            returnXML = ''
            for list_key in station_list:
                sid = str(list_key)
                returnXML = returnXML + templates['xmlLineupItem'].format(station_list[sid]['channel'], station_list[sid]['friendlyName'], base_url + '/watch/' + sid)
            returnXML = "<Lineup>" + returnXML + "</Lineup>"

            self.do_response(200, 'application/xml', returnXML)

        elif contentPath.startswith('/watch'):
            self.do_tuning(contentPath.replace('/watch/', ''))

        elif contentPath.startswith('/auto/v'):
            self.do_tuning(contentPath.replace('/auto/v', ''))

        elif ((contentPath.startswith('/devices/' + self.config['main']['uuid'] + '/media/')) and 
              (not self.config['main']['use_old_plex_interface'])):
            
            channel_no = contentPath.replace('/devices/' + self.config['main']['uuid'] + '/media/', '')
            channel_no = urllib.parse.unquote(channel_no).replace('id://', '').replace('/', '')

            station_list = stations.get_dma_stations_and_channels(self.config, self.location)

            for sid in station_list:
                if station_list[sid]['channel'] == channel_no:
                    break

            self.do_tuning(sid)

        elif contentPath == '/xmltv.xml':
            self.do_response(200, 'application/xml', epg2xml.get_epg(self.config, self.location))

        elif contentPath == '/channels.m3u':
            self.do_response(200, 'application/vnd.apple.mpegurl', channels_m3u.get_channels_m3u(self.config, self.location, base_url))

        elif contentPath == '/debug.json':
            self.do_response(200, 'application/json')

        elif ((contentPath == '/devices/' + self.config['main']['uuid']) and 
              (not self.config['main']['use_old_plex_interface'])):
            tuner_list = ""

            for index, scan_status in enumerate(self.rmg_station_scans):

                if scan_status == 'Idle':
                    tuner_list = tuner_list + templates['xmlRmgTunerIdle'].format(str(index))

                elif scan_status == 'Scan':
                    tuner_list = tuner_list + templates['xmlRmgTunerScanning'].format(str(index))

                else:
                    # otherwise, we're streaming, and the value will be the channel triplet
                    formatted_xml = templates['xmlRmgTunerStreaming'].format(str(index), scan_status)
                    tuner_list = tuner_list + formatted_xml

            self.do_response(200, 
                             'application/xml', 
                             templates['xmlRmgDeviceIdentity'].format(self.config['main']['uuid'],
                                                                      self.config['main']['reporting_friendly_name'],
                                                                      self.config['main']['reporting_model'], 
                                                                      self.config['main']['tuner_count'],
                                                                      base_url,
                                                                      tuner_list))

        elif((contentPath == '/devices/' + self.config['main']['uuid'] + '/channels') and 
             (not self.config['main']['use_old_plex_interface'])):
            station_list = stations.get_dma_stations_and_channels(self.config, self.location)

            channelXML = ''

            for index, list_key in enumerate(station_list):
                sid = str(list_key)
                tmpXML = templates['xmlRmgDeviceChannelItem'].format(station_list[sid]['channel'],
                                                                     station_list[sid]['friendlyName'])

                channelXML = channelXML + tmpXML

            self.do_response(200, 'application/xml', templates['xmlRmgDeviceChannels'].format(index + 1, channelXML))

        elif ((contentPath == '/devices/' + self.config['main']['uuid'] + '/scanners') and
              (not self.config['main']['use_old_plex_interface'])):
            self.do_response(200, 'application/xml', templates['xmlRmgScanProviders'].format(self.location['city']))

        else:
            print("Unknown request to " + contentPath)
            self.do_response(501, 'text/html', templates['htmlError'].format('501 - Not Implemented'))

        return


    def do_POST(self):
        base_url = self.config['main']['plex_accessible_ip'] + ':' + self.config['main']['plex_accessible_port']

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
                self.hdhr_station_scan = True

                for index, scan_status in enumerate(self.rmg_station_scans):
                    if scan_status == 'Idle':
                        self.rmg_station_scans[index] = "Scan"

                self.do_response(200, 'text/html')

                # putting this here after the response on purpose
                stations.refresh_dma_stations_and_channels(self.config, self.locast, self.location)

                self.hdhr_station_scan = False

                for index, scan_status in enumerate(self.rmg_station_scans):
                    if scan_status == 'Scan':
                        self.rmg_station_scans[index] = "Idle"

            elif queryData['scan'] == 'abort':
                self.do_response(200, 'text/html')

                self.hdhr_station_scan = False

                for index, scan_status in enumerate(self.rmg_station_scans):
                    if scan_status == 'Scan':
                        self.rmg_station_scans[index] = "Idle"

            else:
                print("Unknown scan command " + queryData['scan'])
                self.do_response(400, 'text/html', templates['htmlError'].format(queryData['scan'] + ' is not a valid scan command'))

        elif ((contentPath.startswith('/devices/discover') or contentPath.startswith('/devices/probe')) and 
              (not self.config['main']['use_old_plex_interface'])):

            self.do_response(200, 
                             'application/xml', 
                             templates['xmlRmgDeviceDiscover'].format(self.config['main']['uuid'],
                                                                      self.config['main']['reporting_friendly_name'],
                                                                      self.config['main']['reporting_model'], 
                                                                      self.config['main']['tuner_count'],
                                                                      base_url))
        
        elif ((contentPath == '/devices/' + self.config['main']['uuid'] + '/scan') and 
              (not self.config['main']['use_old_plex_interface'])):
            self.hdhr_station_scan = True

            for index, scan_status in enumerate(self.rmg_station_scans):
                if scan_status == 'Idle':
                    self.rmg_station_scans[index] = "Scan"

            self.do_response(200, 
                             'application/xml', 
                             templates['xmlRmgScanStatus'])

            
            # putting this here after the response on purpose
            stations.refresh_dma_stations_and_channels(self.config, self.local_locast, self.location)

            self.hdhr_station_scan = False

            for index, scan_status in enumerate(self.rmg_station_scans):
                if scan_status == 'Scan':
                    self.rmg_station_scans[index] = "Idle"

        else:
            print("Unknown request to " + contentPath)

        return


    def do_DELETE(self):
        base_url = self.config['main']['plex_accessible_ip'] + ':' + self.config['main']['plex_accessible_port']

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

        if ((contentPath == '/devices/' + self.config['main']['uuid'] + '/scan') and 
            (not self.config['main']['use_old_plex_interface'])):
            self.hdhr_station_scan = False

            for index, scan_status in enumerate(self.rmg_station_scans):
                if scan_status == 'Scan':
                    self.rmg_station_scans[index] = "Idle"


    def do_tuning(self, sid):
        channelUri = self.local_locast.get_station_stream_uri(sid)
        station_list = stations.get_dma_stations_and_channels(self.config, self.location)
        tuner_found = False

        # keep track of how many tuners we can use at a time
        for index, scan_status in enumerate(self.rmg_station_scans):

            # the first idle tuner gets it
            if scan_status == 'Idle':
                self.rmg_station_scans[index] = station_list[sid]['channel']
                tuner_found = True
                break

        if tuner_found:
            self.send_response(200)
            self.send_header('Content-type', 'video/mpeg; codecs="avc1.4D401E')
            self.end_headers()

            ffmpeg_command = [self.config['main']['ffmpeg_path'],
                                "-i", channelUri,
                                "-c:v", "copy",
                                "-c:a", "copy",
                                "-f", "mpegts",
                                "-nostats", "-hide_banner",
                                "-loglevel", "warning",
                                "pipe:1"]

            ffmpeg_proc = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE)

            # get initial videodata. if that works, then keep grabbing it
            videoData = ffmpeg_proc.stdout.read(int(self.config['main']['bytes_per_read']))

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
                        if e.errno in [errno.EPIPE, errno.ECONNABORTED, errno.ECONNRESET, errno.ECONNREFUSED]:
                            break
                        else:
                            raise

                videoData = ffmpeg_proc.stdout.read(int(self.config['main']['bytes_per_read']))


            # Send SIGTERM to shutdown ffmpeg
            ffmpeg_proc.terminate()
            try:
                # ffmpeg writes a bit of data out to stderr after it terminates,
                # need to read any hanging data to prevent a zombie process.
                ffmpeg_proc.communicate()
            except ValueError:
                print("Connection Closed")

            self.rmg_station_scans[index] = 'Idle'

        else:
            self.send_response(400, 'All tuners already in use.')
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            reply_str = templates['htmlError'].format('All tuners already in use.')
            self.wfile.write(reply_str.encode('utf-8'))


    def do_response(self, code, mime, reply_str):
        self.send_response(code)
        self.send_header('Content-type', mime)
        self.end_headers()

        if reply_str:
            self.wfile.write(reply_str.encode('utf-8'))



# mostly from https://github.com/ZeWaren/python-upnp-ssdp-example
# and https://stackoverflow.com/questions/46210672/python-2-7-streaming-http-server-supporting-multiple-connections-on-one-port
class PlexHttpServer(threading.Thread):

    def __init__(self, serverSocket, config, locast_service, location):
        threading.Thread.__init__(self)

        PlexHttpHandler.config = config

        self.bind_ip = config["main"]["bind_ip"]
        self.bind_port = config["main"]["bind_port"]

        PlexHttpHandler.stations = stations
        PlexHttpHandler.local_locast = locast_service
        PlexHttpHandler.location = location

        # init station scans 
        tmp_rmg_scans = []

        for x in range(int(config['main']['tuner_count'])):
            tmp_rmg_scans.append('Idle')
        
        PlexHttpHandler.rmg_station_scans = tmp_rmg_scans

        self.socket = serverSocket

        self.daemon = True
        self.start()

    def run(self):
        httpd = HTTPServer((self.bind_ip, int(self.bind_port)), PlexHttpHandler, False)
        httpd.socket = self.socket
        httpd.server_bind = self.server_close = lambda self: None

        httpd.serve_forever()


def start(config, locast, location):
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serverSocket.bind((config["main"]['bind_ip'], int(config["main"]['bind_port'])))
    serverSocket.listen(int(config["main"]["concurrent_listeners"]))

    print("Now listening for requests.")
    for i in range(int(config["main"]["concurrent_listeners"])):
        PlexHttpServer(serverSocket, config, locast, location)
