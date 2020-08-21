import subprocess, os, sys, random, threading, socket, time, errno, SocketServer
import SSDPServer
import LocastService
from templates import templates
from functools import partial
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from multiprocessing import Process





def clean_exit():
    sys.stderr.flush()
    sys.stdout.flush()
    os._exit(0)


        

# with help from https://www.acmesystems.it/python_http
# and https://stackoverflow.com/questions/21631799/how-can-i-pass-parameters-to-a-requesthandler
class PlexHttpHandler(BaseHTTPRequestHandler):

    # using class variables since this should only be set once
    address = ""
    port = ""
    uuid = ""
    templates = {}
    station_scan = False
    station_list = {}
    local_locast = None

    def do_GET(self): 
        base_url = self.address + ':' + self.port

        # paths and logic mostly pulled from telly:routes.go: https://github.com/tellytv/telly
        if (self.path == '/') or (self.path == '/device.xml'):
            self.send_response(200)
            self.send_header('Content-type','application/xml')
            self.end_headers()
            self.wfile.write(self.templates['xmlDiscover'].format(self.uuid, base_url))

        elif self.path == '/discover.json':
            self.send_response(200)
            self.send_header('Content-type','application/json')
            self.end_headers()
            self.wfile.write(self.templates['jsonDiscover'].format(self.uuid, base_url))

        elif self.path == '/lineup_status.json':
            self.send_response(200)
            self.send_header('Content-type','application/json')
            self.end_headers()
            if self.station_scan:
                self.wfile.write(self.templates['jsonLineupStatus'])
            else:
                self.wfile.write(self.templates['jsonLineupComplete'])
            
        elif self.path == '/lineup.json': # TODO
            self.send_response(200)
            self.send_header('Content-type','application/json')
            self.end_headers()

            returnJSON = ''
            for index, station_item in enumerate(self.station_list):
                returnJSON = returnJSON + self.templates['jsonLineupItem'].format(station_item['channel'], station_item['name'], base_url + '/watch/' + str(station_item['id']))
                if (index + 1) != len(self.station_list):
                    returnJSON = returnJSON + ','

            returnJSON = "[" + returnJSON + "]"
            self.wfile.write(returnJSON)

        elif self.path == '/lineup.xml': # TODO 
            self.send_response(200)
            self.send_header('Content-type','application/xml')
            self.end_headers()
            returnXML = ''
            for station_item in self.station_list:
                returnXML = returnXML + self.templates['xmlLineupItem'].format(station_item['channel'], station_item['name'], base_url + '/watch/' + str(station_item['id']))
            returnXML = "<Lineup>" + returnXML + "</Lineup>"
            self.wfile.write(returnXML)

        elif self.path.startswith('/watch'):
            channelId = self.path.replace('/watch/', '')
            channelUri = self.local_locast.get_station_stream_uri(channelId)

            self.send_response(200)
            self.send_header('Content-type','video/mpeg; codecs="avc1.4D401E')
            self.end_headers()

            ffmpeg_proc = subprocess.Popen(["ffmpeg", "-i", channelUri, "-codec", "copy", "-f", "mpegts", "pipe:1"], stdout=subprocess.PIPE)

            
            # get initial videodata. if that works, then keep grabbing it
            videoData = ffmpeg_proc.stdout.read(1024000)

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
                        

                videoData = ffmpeg_proc.stdout.read(1024000)

            ffmpeg_proc.terminate()
            ffmpeg_proc.communicate()
            


        # elif self.path == '/epg.xml':
        #     self.send_response(200)
        #     self.send_header('Content-type','application/xml')
        #     self.end_headers()

        elif self.path == '/debug.json':
            self.send_response(200)
            self.send_header('Content-type','application/json')
            self.end_headers()

        else:
            print("Unknown request to " + self.path)
            self.send_response(501)
            self.send_header('Content-type','text/html')
            self.end_headers()
            self.wfile.write(self.templates['htmlError'].format('501 - Not Implemented'))
        
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
                self.send_header('Content-type','text/html')
                self.end_headers()

                self.station_list = locast.get_stations()
                self.station_scan = False
                
            elif queryData['scan'] == 'abort':
                self.send_response(200)
                self.send_header('Content-type','text/html')
                self.end_headers()
            else:
                print("Unknown scan command " + queryData['scan'])
                self.send_response(400)
                self.send_header('Content-type','text/html')
                self.end_headers()
                self.wfile.write(self.templates['htmlError'].format(queryData['scan'] + ' is not a valid scan command'))

        else:
            print("Unknown request to " + contentPath)

        return






# mostly from https://github.com/ZeWaren/python-upnp-ssdp-example
# and https://stackoverflow.com/questions/46210672/python-2-7-streaming-http-server-supporting-multiple-connections-on-one-port
class PlexHttpServer(threading.Thread):

    def __init__(self, serverSocket, config, templates, station_list, locast_service):
        threading.Thread.__init__(self)

        PlexHttpHandler.address = config["host"][0]
        PlexHttpHandler.port = config["host"][1]
        PlexHttpHandler.uuid = config["uuid"]
        PlexHttpHandler.templates = templates
        PlexHttpHandler.station_list = station_list
        PlexHttpHandler.local_locast = locast_service

        self.address = config["listen"][0]
        self.port = config["listen"][1]
        self.socket = serverSocket
        self.daemon = True
        self.start()

    def run(self):
        httpd = HTTPServer((self.address, int(self.port)), PlexHttpHandler, False)
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





################################### Startup Logic
if __name__ == '__main__':
    
    # set to directory of script
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    LISTEN_ADDY = "0.0.0.0"
    LISTEN_PORT = "6077"
    CURRENT_VERSION = "0.4.2"
    DEVICE_UUID = "12345678"
    CONCURRENT_LISTENERS = 10

    DEBUG_MODE = os.getenv('debug', False)
    CONFIG_LOCAST_USERNAME = os.getenv('username', '')
    CONFIG_LOCAST_PASSWORD = os.getenv('password', '')
    HOST_PORT = os.getenv("external_port", '6077')
    HOST_ADDY = os.getenv("external_addy", '0.0.0.0')

    for argument in sys.argv:
        if argument.startswith('-u:'):
            CONFIG_LOCAST_USERNAME = argument[3:]
        elif argument.startswith('-p:'):
            CONFIG_LOCAST_PASSWORD = argument[3:]
        elif argument.startswith('--debug'):
            DEBUG_MODE = True
        elif argument.startswith('--port:'):
            HOST_PORT = argument[7:]
        elif argument.startswith('--addy:'):
            HOST_ADDY = argument[7:]


    print("Locast2Plex v" + CURRENT_VERSION)
    if DEBUG_MODE:
        print("DEBUG MODE ACTIVE")


    # generate UUID here for when we are not using docker
    if not os.path.exists(os.path.curdir + '/service_uuid'):
        print("No UUID found.  Generating one now...")
        # from https://pynative.com/python-generate-random-string/
        # create a string that wouldn't be a real device uuid for 
        DEVICE_UUID = ''.join(random.choice("hijklmnopqrstuvwxyz") for i in range(8))
        with open("service_uuid", 'w') as uuid_file:
            uuid_file.write(DEVICE_UUID)

    else:
        print("UUID found.")
        with open("service_uuid", 'r') as uuid_file:
            DEVICE_UUID = uuid_file.read().replace('\n', '')

    print("UUID set to: " + DEVICE_UUID + "...")


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



    ffmpeg_proc = None
    
    mock_location = None
    #mock_location = {
    #    "latitude": "47.6062",
    #    "longitude": "-122.3321"
    #}
#
    locast = LocastService.LocastService("./", mock_location)
    station_list = None

    
    if (not locast.login(CONFIG_LOCAST_USERNAME, CONFIG_LOCAST_PASSWORD)) or (not locast.validate_user()):
        print("Exiting...")
        clean_exit()
    else:
        station_list = locast.get_stations()

        try:
            print("Starting device server on " + LISTEN_ADDY + ":" + LISTEN_PORT)
            serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            serverSocket.bind((LISTEN_ADDY, int(LISTEN_PORT)))
            serverSocket.listen(CONCURRENT_LISTENERS)

            config = {
                "host": (HOST_ADDY, HOST_PORT),
                "listen": (LISTEN_ADDY, LISTEN_PORT),
                "uuid": DEVICE_UUID
            }

            for i in range(CONCURRENT_LISTENERS):
                PlexHttpServer(serverSocket, config, templates, station_list, locast)

            print("Starting SSDP server...")
            ssdpServer = Process(target=ssdpServerProcess, args=(HOST_ADDY, HOST_PORT, DEVICE_UUID))
            ssdpServer.daemon = True
            ssdpServer.start()

            # wait forever
            while True:
                time.sleep(3600)

        except KeyboardInterrupt:
            print('^C received, shutting down the server')
            clean_exit()
