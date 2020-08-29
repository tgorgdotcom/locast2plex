templates = {



    # HTTP Error
    'htmlError': """<html>
    <head></head>
    <body>
        <h2>{}</h2>
    </body>
</html>""",



    # XML DISCOVER
    # with help from https://github.com/ZeWaren/python-upnp-ssdp-example
    'xmlDiscover': """<root xmlns="urn:schemas-upnp-org:device-1-0">
    <specVersion>
        <major>1</major>
        <minor>0</minor>
    </specVersion>
    <device>
        <deviceType>urn:schemas-upnp-org:device:MediaServer:1</deviceType>
        <friendlyName>Locast2Plex</friendlyName>
        <manufacturer>Silicondust</manufacturer>
        <modelName>{0}</modelName>
        <modelNumber>{0}</modelNumber>
        <serialNumber/>
        <UDN>uuid:{1}</UDN>
    </device>
    <URLBase>http://{2}</URLBase>
</root>""",





    'xmlLineupItem': """<Program>
    <GuideNumber>{}</GuideNumber>
    <GuideName>{}</GuideName>
    <URL>http://{}</URL>
</Program>""",


    # mostly pulled from tellytv
    # NOTE: double curly brace escaped to prevent format from breaking
    'jsonDiscover': """{{
    "FriendlyName": "Locast2Plex",
    "Manufacturer": "Silicondust",
    "ModelNumber": "{0}",
    "FirmwareName": "{1}",
    "TunerCount": {2},
    "FirmwareVersion": "{3}",
    "DeviceID": "{4}",
    "DeviceAuth": "locast2plex",
    "BaseURL": "http://{5}",
    "LineupURL": "http://{5}/lineup.json"
}}""",



    # mostly pulled from tellytv
    # Don't need curly braces to escape here
    'jsonLineupStatus': """{
    "ScanInProgress": true,
    "Progress": 50,
    "Found": 5
}""",



    # mostly pulled from tellytv
    # Don't need curly brece escape here
    'jsonLineupComplete': """{
    "ScanInProgress": false,
    "ScanPossible": true,
    "Source": "Antenna",
    "SourceList": ["Antenna"]
}""",




    'jsonLineupItem': """{{
    "GuideNumber": "{}",
    "GuideName": "{}",
    "URL": "http://{}"
}}"""
}