import os
import random
import configparser
import pathlib

from L2PTools import clean_exit


class locast2plexConfig():

    config_file = None
    config_handler = configparser.ConfigParser()
    script_dir = None

    config = {
                "main": {
                        'uuid': None,
                        },
                "locast2plex": {
                                "listen_address": "0.0.0.0",
                                "listen_port": "6077",
                                'tuner_count': '3',
                                'concurrent_listeners': '10',  # to convert
                                "cache_dir": None,
                                },
                "locast": {
                            "username": None,
                            "password": None,
                            'epg_update_frequency': 43200,
                            'epg_update_days': 7,
                            },
                "location": {
                            'override_latitude': None,
                            'override_longitude': None,
                            'mock_location': None,
                            'override_zipcode': None,
                            },
                "ffmpeg": {
                            'ffmpeg_path': None,
                            'bytes_per_read': '1152000',
                            },
                "dev": {
                        'reporting_model': 'HDHR3-US',
                        'reporting_firmware_name': 'hdhomerun3_atsc',
                        'reporting_firmware_ver': '20150826',
                        'tuner_type': "Antenna",
                        'fcc_delay': 43200,
                        }
    }

    def __init__(self, script_dir, opersystem, args):
        self.get_config_path(script_dir, args)
        self.import_config()
        self.config_adjustments(opersystem, script_dir)

    def get_config_path(self, script_dir, args):
        if args.cfg:
            self.config_file = pathlib.Path(str(args.cfg))
        else:
            for x in ['config/config.ini', 'config.ini']:
                poss_config = pathlib.Path(script_dir).joinpath(x)
                print(poss_config)
                if os.path.exists(poss_config):
                    self.config_file = poss_config
                    break
        if not self.config_file or not os.path.exists(self.config_file):
            print("Config file missing, Exiting...")
            clean_exit()
        print("Loading Configuration File: " + str(self.config_file))

    def import_config(self):
        self.config_handler.read(self.config_file)
        for each_section in self.config_handler.sections():
            for (each_key, each_val) in self.config_handler.items(each_section):
                self.config[each_section.lower()][each_key.lower()] = each_val

    def write(self, section, key, value):
        self.config[section][key] = value
        self.config_handler.set(section, key, value)

        with open(self.config_file, 'w') as config_file:
            self.config_handler.write(config_file)

    def config_adjustments(self, opersystem, script_dir):

        if not self.config["locast"]["username"] or not self.config["locast"]["password"]:
            print("Locast Login Credentials Missing. Exiting...")
            clean_exit()

        # Tuner Count Cannot be greater than 3
        try:
            TUNER_COUNT = int(self.config["locast2plex"]["tuner_count"])
            if not 1 <= TUNER_COUNT <= 4:
                print("Tuner count set outside of 1-4 range.  Setting to default")
                self.config["locast2plex"]["tuner_count"] = 3
        except ValueError:
            print("tuner_count value is not valid.  Setting to default")
            self.config["locast2plex"]["tuner_count"] = 3
        print("Tuner count set to " + str(self.config["locast2plex"]["tuner_count"]))

        print("Server is set to run on  " +
              str(self.config["locast2plex"]["listen_address"]) + ":" +
              str(self.config["locast2plex"]["listen_port"]))

        # generate UUID here for when we are not using docker
        if self.config["main"]["uuid"] is None:
            print("No UUID found.  Generating one now...")
            # from https://pynative.com/python-generate-random-string/
            # create a string that wouldn't be a real device uuid for
            self.config["main"]["uuid"] = ''.join(random.choice("hijklmnopqrstuvwxyz") for i in range(8))
            self.write('main', 'uuid', self.config["main"]["uuid"])
        print("UUID set to: " + self.config["main"]["uuid"] + "...")

        if (self.config["location"]["override_latitude"] is not None) and (self.config["location"]["override_longitude"] is not None):
            self.config["location"]["mock_location"] = {
                "latitude": self.config["location"]["override_latitude"],
                "longitude": self.config["location"]["override_longitude"]
            }

        if not self.config["ffmpeg"]["ffmpeg_path"]:
            if opersystem in ["Windows"]:
                base_ffmpeg_dir = pathlib.Path(script_dir).joinpath('ffmpeg')
                self.config["ffmpeg"]["ffmpeg_path"] = pathlib.Path(base_ffmpeg_dir).joinpath('ffmpeg.exe')
            else:
                self.config["ffmpeg"]["ffmpeg_path"] = "ffmpeg"

        if not self.config["locast2plex"]["cache_dir"]:
            base_data_dir = pathlib.Path(script_dir).joinpath('data')
            self.config["locast2plex"]["cache_dir"] = pathlib.Path(base_data_dir).joinpath('cache')
        else:
            self.config["locast2plex"]["cache_dir"] = pathlib.Path(self.config["locast2plex"]["cache_dir"])
        if not self.config["locast2plex"]["cache_dir"].is_dir():
            print("Invalid Cache Directory. Exiting...")
            clean_exit()
