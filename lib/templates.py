templates = {



# HTTP Error
'htmlError': 
"""<html>
    <head></head>
    <body>
        <h2>{}</h2>
    </body>
</html>""",



# XML DISCOVER
# with help from https://github.com/ZeWaren/python-upnp-ssdp-example
'xmlDiscover': 
"""<root xmlns="urn:schemas-upnp-org:device-1-0">
    <specVersion>
        <major>1</major>
        <minor>0</minor>
    </specVersion>
    <device>
        <deviceType>urn:plex-tv:device:Media:1</deviceType>
        <friendlyName>{0}</friendlyName>
        <manufacturer>{0}</manufacturer>
        <manufacturerURL>https://github.com/tgorgdotcom/locast2plex</manufacturerURL>
        <modelName>{0}</modelName>
        <modelNumber>{1}</modelNumber>
        <modelDescription>{0}</modelDescription>
        <modelURL>https://github.com/tgorgdotcom/locast2plex</modelURL>
        <UDN>uuid:{2}</UDN>
        <serviceList>
            <service>
                <URLBase>http://{3}</URLBase>
                <serviceType>urn:plex-tv:service:MediaGrabber:1</serviceType>
                <serviceId>urn:plex-tv:serviceId:MediaGrabber</serviceId>
            </service>
        </serviceList>
    </device>
</root>""",





# XML DISCOVER OLD
# with help from https://github.com/ZeWaren/python-upnp-ssdp-example
'xmlDiscoverOld': 
"""<root xmlns="urn:schemas-upnp-org:device-1-0">
    <specVersion>
        <major>1</major>
        <minor>0</minor>
    </specVersion>
    <device>
        <deviceType>urn:schemas-upnp-org:device:MediaServer:1</deviceType>
        <friendlyName>{0}</friendlyName>
        <manufacturer>{0}</manufacturer>
        <manufacturerURL>https://github.com/tgorgdotcom/locast2plex</manufacturerURL>
        <modelName>{0}</modelName>
        <modelNumber>{1}</modelNumber>
        <serialNumber/>
        <UDN>uuid:{2}</UDN>
    </device>
    <URLBase>http://{3}</URLBase>
</root>""",





'xmlLineupItem': 
"""<Program>
    <GuideNumber>{}</GuideNumber>
    <GuideName>{}</GuideName>
    <URL>http://{}</URL>
</Program>""",




'xmlRmgIdentification': 
"""<MediaContainer>
    <MediaGrabber identifier="tv.plex.grabbers.locast2plex" title="{0}" protocols="livetv" />
</MediaContainer>""",




'xmlRmgDeviceDiscover': 
"""<MediaContainer size="1">
    <Device	
        key="{0}" 
        make="{1}" 
        model="{1}" 
        modelNumber="{2}" 
        protocol="livetv" 
        status="alive" 
        title="{1}" 
        tuners="{3}" 
        uri="http://{4}" 
        uuid="device://tv.plex.grabbers.locast2plex/{0}" 
        interface='network' />
</MediaContainer>""",



'xmlRmgDeviceIdentity': 
"""<MediaContainer size="1">
    <Device 
        key="{0}" 
        make="{1}" 
        model="{1}"
        modelNumber="{2}" 
        protocol="livetv" 
        status="alive"
        title="{1} ({4})" 
        tuners="{3}"
        uri="http://{4}"
        uuid="device://tv.plex.grabbers.locast2plex/{0}">
            {5}
    </Device>
</MediaContainer>""",




'xmlRmgTunerStreaming': 
"""<Tuner 
    index="{0}"
    status="streaming"
    channelIdentifier="id://{1}"
    lock="1"
    signalStrength="100"
    signalQuality="100" />""",




'xmlRmgTunerIdle': 
"""<Tuner index="{0}" status="idle" />""",




'xmlRmgTunerScanning': 
"""<Tuner 
    index="{0}" 
    status="scanning" 
    progress="50"
    channelsFound="0" />""",



'xmlRmgDeviceChannels': 
"""<MediaContainer size="{0}">
    {1}
</MediaContainer>""",



'xmlRmgDeviceChannelItem': 
"""<Channel 
    drm="0"
    channelIdentifier="id://{0}"
    name="{1}" 
    origin="Locast2Plex"
    number="{0}" 
    type="tv" />""",



'xmlRmgScanProviders': 
"""<MediaContainer size="1" simultaneousScanners="0">
    <Scanner type="atsc">
        <Setting
            id="provider"
            enumValues="1:Locast ({0})"/>
    </Scanner>
</MediaContainer>""",



'xmlRmgScanStatus': 
"""<MediaContainer status="0" message="Scanning..." />""",



# mostly pulled from tellytv
# NOTE: double curly brace escaped to prevent format from breaking
'jsonDiscover': 
"""{{
    "FriendlyName": "{0}",
    "Manufacturer": "{0}",
    "ModelNumber": "{1}",
    "FirmwareName": "{2}",
    "TunerCount": {3},
    "FirmwareVersion": "{4}",
    "DeviceID": "{5}",
    "DeviceAuth": "locast2plex",
    "BaseURL": "http://{6}",
    "LineupURL": "http://{6}/lineup.json"
}}""",



# mostly pulled from tellytv
# Don't need curly braces to escape here
'jsonLineupStatus': 
"""{
    "ScanInProgress": true,
    "Progress": 50,
    "Found": 0
}""",



# mostly pulled from tellytv
# Don't need curly brece escape here
'jsonLineupComplete': 
"""{
    "ScanInProgress": false,
    "ScanPossible": true,
    "Source": "Antenna",
    "SourceList": ["Antenna"]
}""",




'jsonLineupItem': 
"""{{
    "GuideNumber": "{}",
    "GuideName": "{}",
    "URL": "http://{}"
}}"""



}
