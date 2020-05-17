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
        <modelName>HDHR3-US</modelName>
        <modelNumber>HDHR3-US</modelNumber>
        <serialNumber/>
        <UDN>uuid:{}</UDN>
    </device>
    <URLBase>http://{}</URLBase>
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
    "ModelNumber": "HDHR3-US",
    "FirmwareName": "hdhomerun3_atsc",
    "TunerCount": 2,
    "FirmwareVersion": "20150826",
    "DeviceID": "{0}",
    "DeviceAuth": "locast2plex",
    "BaseURL": "http://{1}",
    "LineupURL": "http://{1}/lineup.json"
}}""",



    # mostly pulled from tellytv
    # Don't need curly brece escape here
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