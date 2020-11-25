# from https://github.com/deathbybandaid/fHDHR_Locast/blob/master/fHDHR/fHDHRweb/fHDHRdevice/channels_m3u.py
import lib.stations as stations
from io import StringIO


def get_channels_m3u(config, location, base_url):

    FORMAT_DESCRIPTOR = "#EXTM3U"
    RECORD_MARKER = "#EXTINF"

    fakefile = StringIO()

    xmltvurl = ('%s%s/xmltv.xml' % ("http://", base_url))

    fakefile.write(
                    "%s\n" % (
                                FORMAT_DESCRIPTOR + " " +
                                "url-tvg=\"" + xmltvurl + "\"" + " " +
                                "x-tvg-url=\"" + xmltvurl + "\"")
                    )
    station_list = stations.get_dma_stations_and_channels(config, location)

    for sid in station_list:

        fakefile.write(
                        "%s\n" % (
                                    RECORD_MARKER + ":-1" + " " +
                                    "channelID=\"" + str(sid) + "\" " +
                                    "tvg-chno=\"" + str(station_list[sid]['channel']) + "\" " +
                                    "tvg-name=\"" + station_list[sid]['friendlyName'] + "\" " +
                                    "tvg-id=\"" + str(sid) + "\" " +
                                    (("tvg-logo=\"" + station_list[sid]['logoUrl'] + "\" ") if 'logoUrl' in station_list[sid].keys() else "") +
                                    "group-title=\"Locast2Plex\"," + station_list[sid]['friendlyName']
                                 )
                      )

        fakefile.write(
                        "%s\n" % (
                                    (
                                        '%s%s/watch/%s' %
                                        ("http://", base_url, str(sid))
                                    )
                                 )
                      )

    return fakefile.getvalue()