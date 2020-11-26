# pylama:ignore=E722
import os
import time
import datetime
import json
import pathlib
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import lib.stations as stations
from lib.l2p_tools import clean_exit
from lib.filelock import Timeout, FileLock


def epg_process(config, location):
    dummy_xml(config, location)
    try:
        while True:
            time.sleep(config["main"]["epg_update_frequency"])
            
            print("Fetching EPG for DMA " + str(location["DMA"]) + ".")
            generate_epg_file(config, location)
            
    except KeyboardInterrupt:
        clean_exit()


def dummy_xml(config, location):
    out_path = pathlib.Path(config["main"]["cache_dir"]).joinpath(str(location["DMA"]) + "_epg").with_suffix(".xml")
    if os.path.exists(out_path):
        return

    print("Creating Temporary Empty XMLTV File.")

    base_cache_dir = config["main"]["cache_dir"]

    cache_dir = pathlib.Path(base_cache_dir).joinpath(str(location["DMA"]) + "_epg")
    if not cache_dir.is_dir():
        cache_dir.mkdir()

    out = ET.Element('tv')
    out.set('source-info-url', 'https://www.locast.org')
    out.set('source-info-name', 'locast.org')
    out.set('generator-info-name', 'locastepg')
    out.set('generator-info-url', 'github.com/tgorgdotcom/locast2plex')
    with open(out_path, 'wb') as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(ET.tostring(out, encoding='UTF-8'))


def generate_epg_file(config, location):

    base_cache_dir = config["main"]["cache_dir"]

    out_path = pathlib.Path(base_cache_dir).joinpath(str(location["DMA"]) + "_epg").with_suffix(".xml")
    out_lock_path = pathlib.Path(base_cache_dir).joinpath(str(location["DMA"]) + "_epg").with_suffix(".xml.lock")

    cache_dir = pathlib.Path(base_cache_dir).joinpath(str(location["DMA"]) + "_epg")
    if not cache_dir.is_dir():
        cache_dir.mkdir()

    dma_channels = stations.get_dma_stations_and_channels(config, location)

    # Make a date range to pull
    todaydate = datetime.datetime.utcnow().replace(hour=0,minute=0,second=0,microsecond=0) # make sure we're dealing with UTC!
    dates_to_pull = [todaydate]
    days_to_pull = int(config["main"]["epg_update_days"])
    for x in range(1, days_to_pull - 1):
        xdate = todaydate + datetime.timedelta(days=x)
        dates_to_pull.append(xdate)

    remove_stale_cache(cache_dir, todaydate)

    out = ET.Element('tv')
    out.set('source-info-url', 'https://www.locast.org')
    out.set('source-info-name', 'locast.org')
    out.set('generator-info-name', 'locastepg')
    out.set('generator-info-url', 'github.com/tgorgdotcom/locast2plex')
    out.set('generator-special-thanks', 'deathbybandaid')

    done_channels = False

    for x_date in dates_to_pull:
        url = ('https://api.locastnet.org/api/watch/epg/' +
               str(location["DMA"]) + "?startTime=" + x_date.isoformat())

        result = get_cached(cache_dir, x_date.strftime("%m-%d-%Y"), url)
        channel_info = json.loads(result)

        # List Channels First
        if not done_channels:
            done_channels = True
            for channel_item in channel_info:
                sid = str(channel_item['id'])
                channel_number = str(dma_channels[sid]['channel'])
                channel_realname = str(dma_channels[sid]['friendlyName'])
                channel_callsign = str(dma_channels[sid]['callSign'])

                if 'logo226Url' in channel_item.keys():
                    channel_logo = channel_item['logo226Url']
                    
                elif 'logoUrl' in channel_item.keys():
                    channel_logo = channel_item['logoUrl']

                c_out = sub_el(out, 'channel', id=sid)
                sub_el(c_out, 'display-name', text='%s %s' % (channel_number, channel_callsign))
                sub_el(c_out, 'display-name', text='%s %s %s' % (channel_number, channel_callsign, sid))
                sub_el(c_out, 'display-name', text=channel_number)
                sub_el(c_out, 'display-name', text='%s %s fcc' % (channel_number, channel_callsign))
                sub_el(c_out, 'display-name', text=channel_callsign)
                sub_el(c_out, 'display-name', text=channel_realname)

                if channel_logo != None:
                    sub_el(c_out, 'icon', src=channel_logo)

        # Now list Program informations
        for channel_item in channel_info:
            sid = str(channel_item['id'])
            channel_number = str(dma_channels[sid]['channel'])
            channel_realname = str(dma_channels[sid]['friendlyName'])
            channel_callsign = str(dma_channels[sid]['callSign'])

            if 'logo226Url' in channel_item.keys():
                channel_logo = channel_item['logo226Url']
                
            elif 'logoUrl' in channel_item.keys():
                channel_logo = channel_item['logoUrl']

            for event in channel_item['listings']:

                tm_start = tm_parse(event['startTime']) # this is returned from locast in UTC
                tm_duration = event['duration'] * 1000
                tm_end = tm_parse(event['startTime'] + tm_duration)

                event_genres = []
                if 'genres' in event.keys():
                    event_genres = event['genres'].split(",")

                # note we're returning everything as UTC, as the clients handle converting to correct timezone
                prog_out = sub_el(out, 'programme', start=tm_start, stop=tm_end, channel=sid)

                if event['title']:
                    sub_el(prog_out, 'title', lang='en', text=event['title'])

                if 'movie' in event_genres and event['releaseYear']:
                    sub_el(prog_out, 'sub-title', lang='en', text='Movie: ' + event['releaseYear'])
                elif 'episodeTitle' in event.keys():
                    sub_el(prog_out, 'sub-title', lang='en', text=event['episodeTitle'])

                if 'description' not in event.keys():
                    event['description'] = "Unavailable"
                elif event['description'] is None:
                    event['description'] = "Unavailable"
                sub_el(prog_out, 'desc', lang='en', text=event['description'])

                sub_el(prog_out, 'length', units='minutes', text=str(event['duration']))

                for f in event_genres:
                    sub_el(prog_out, 'category', lang='en', text=f.strip())
                    sub_el(prog_out, 'genre', lang='en', text=f.strip())

                if event["preferredImage"] is not None:
                    sub_el(prog_out, 'icon', src=event["preferredImage"])

                if 'rating' not in event.keys():
                    event['rating'] = "N/A"
                r = ET.SubElement(prog_out, 'rating')
                sub_el(r, 'value', text=event['rating'])

                if 'seasonNumber' in event.keys() and 'episodeNumber' in event.keys():
                    s_ = int(str(event['seasonNumber']), 10)
                    e_ = int(str(event['episodeNumber']), 10)
                    sub_el(prog_out, 'episode-num', system='common',
                           text='S%02dE%02d' % (s_, e_))
                    sub_el(prog_out, 'episode-num', system='xmltv_ns',
                           text='%d.%d.0' % (int(s_)-1, int(e_)-1))
                    sub_el(prog_out, 'episode-num', system='SxxExx',
                           text='S%02dE%02d' % (s_, e_))

                if 'isNew' in event.keys():
                    if event['isNew']:
                        sub_el(prog_out, 'new')

    xml_lock = FileLock(out_lock_path)
    with xml_lock:
        with open(out_path, 'wb') as f:
            f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write(ET.tostring(out, encoding='UTF-8'))


def get_epg(config, location):
    epg_path = pathlib.Path(config['main']['cache_dir']).joinpath(str(location["DMA"]) + "_epg.xml")
    xml_lock = FileLock(str(epg_path) + '.lock')

    return_str = None
    with xml_lock:
        with open(epg_path, 'rb') as epg_file:
            return_str = epg_file.read().decode('utf-8')

    return return_str


def get_cached(cache_dir, cache_key, url):
    cache_path = cache_dir.joinpath(cache_key + '.json')
    if cache_path.is_file():
        print('FROM CACHE:', str(cache_path))
        with open(cache_path, 'rb') as f:
            return f.read()
    else:
        print('Fetching:  ', url)
        try:
            resp = urllib.request.urlopen(url)
            result = resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 400:
                print('Got a 400 error!  Ignoring it.')
                result = (
                    b'{'
                    b'"note": "Got a 400 error at this time, skipping.",'
                    b'"channels": []'
                    b'}')
            else:
                raise
        with open(cache_path, 'wb') as f:
            f.write(result)
        return result


def remove_stale_cache(cache_dir, todaydate):
    for p in cache_dir.glob('*'):
        try:
            cachedate = datetime.datetime.strptime(str(p.name).replace('.json', ''), "%m-%d-%Y")
            if cachedate >= todaydate:
                continue
        except:
            pass
        print('Removing stale cache file:', p.name)
        p.unlink()


def tm_parse(tm):
    tm = datetime.datetime.utcfromtimestamp(tm/1000.0)
    tm = str(tm.strftime('%Y%m%d%H%M%S +0000'))
    return tm


def sub_el(parent, name, text=None, **kwargs):
    el = ET.SubElement(parent, name, **kwargs)
    if text:
        el.text = text
    return el
