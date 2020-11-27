import os
import random
import configparser
import pathlib

from lib.l2p_tools import clean_exit, get_version_str


def get_config(script_dir, opersystem, args):
    return UserConfig(script_dir, opersystem, args).data


class UserConfig():

    config_file = None
    config_handler = configparser.ConfigParser(interpolation=None)
    script_dir = None

    data = {
        "main": {
            'uuid': None,
            "plex_accessible_ip": "0.0.0.0",
            "plex_accessible_port": "6077",
            'tuner_count': '3',
            'concurrent_listeners': '10',  # to convert
            "cache_dir": None,
            "locast_username": None,
            "locast_password": None,
            'disable_ssdp': False,
            'epg_update_frequency': 43200, # 12 hours
            'epg_update_days': 7,
            'override_latitude': None,
            'override_longitude': None,
            'override_zipcode': None,
            'mock_location': None,
            'ffmpeg_path': None, 
            'use_old_plex_interface': False,
            'bytes_per_read': '1152000',
            'reporting_model': 'l2p',
            'reporting_friendly_name': 'Locast2Plex',
            'reporting_firmware_name': 'locast2plex',
            'reporting_firmware_ver': 'v' + get_version_str(),
            'tuner_type': "Antenna",
            'fcc_delay': 1296000,  # 15 days
            'verbose': False
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
            clean_exit(1)
        print("Loading Configuration File: " + str(self.config_file))


    def import_config(self):
        self.config_handler.read(self.config_file)
        for each_section in self.config_handler.sections():
            for (each_key, each_val) in self.config_handler.items(each_section):
                self.data[each_section.lower()][each_key.lower()] = each_val


    def write(self, section, key, value):
        self.data[section][key] = value
        self.config_handler.set(section, key, value)

        with open(self.config_file, 'w') as config_file:
            self.config_handler.write(config_file)


    def config_adjustments(self, opersystem, script_dir):

        if not self.data["main"]["locast_username"] or not self.data["main"]["locast_password"]:
            print("Locast Login Credentials Missing. Exiting...")
            clean_exit(1)

        # Tuner Count Cannot be greater than 3
        try:
            TUNER_COUNT = int(self.data["main"]["tuner_count"])
            if not 1 <= TUNER_COUNT <= 4:
                print("Tuner count set outside of 1-4 range.  Setting to default")
                self.data["main"]["tuner_count"] = 3
        except ValueError:
            print("tuner_count value is not valid.  Setting to default")
            self.data["main"]["tuner_count"] = 3
        print("Tuner count set to " + str(self.data["main"]["tuner_count"]))

        print("Server is set to run on  " +
              str(self.data["main"]["plex_accessible_ip"]) + ":" +
              str(self.data["main"]["plex_accessible_port"]))

        if os.path.exists(pathlib.Path(script_dir).joinpath('is_container')):
            self.data["main"]["bind_ip"] = "0.0.0.0" 
            self.data["main"]["bind_port"] = "6077"
        else:
            self.data["main"]["bind_ip"] = self.data["main"]["plex_accessible_ip"]
            self.data["main"]["bind_port"] = self.data["main"]["plex_accessible_port"]

        # generate UUID here for when we are not using docker
        if self.data["main"]["uuid"] is None:
            print("No UUID found.  Generating one now...")
            # from https://pynative.com/python-generate-random-string/
            # create a string that wouldn't be a real device uuid for
            self.data["main"]["uuid"] = ''.join(random.choice("hijklmnopqrstuvwxyz") for i in range(8))
            self.write('main', 'uuid', self.data["main"]["uuid"])
        print("UUID set to: " + self.data["main"]["uuid"] + "...")

        if (self.data["main"]["override_latitude"] is not None) and (self.data["main"]["override_longitude"] is not None):
            self.data["main"]["mock_location"] = {
                "latitude": self.data["main"]["override_latitude"],
                "longitude": self.data["main"]["override_longitude"]
            }

        if not self.data["main"]["ffmpeg_path"]:
            if opersystem in ["Windows"]:
                base_ffmpeg_dir = pathlib.Path(script_dir).joinpath('ffmpeg')
                self.data["main"]["ffmpeg_path"] = pathlib.Path(base_ffmpeg_dir).joinpath('ffmpeg.exe')
            else:
                self.data["main"]["ffmpeg_path"] = "ffmpeg"

        if not self.data["main"]["cache_dir"]:
            self.data["main"]["cache_dir"] = pathlib.Path(script_dir).joinpath('cache')
        else:
            self.data["main"]["cache_dir"] = pathlib.Path(self.data["main"]["cache_dir"])

        if not self.data["main"]["cache_dir"].is_dir():
            print("Invalid Cache Directory. Exiting...")
            clean_exit(1)
