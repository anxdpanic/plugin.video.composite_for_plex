# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import random

from six.moves import range
from six.moves.urllib_parse import unquote

from kodi_six import xbmc  # pylint: disable=import-error
from kodi_six import xbmcgui  # pylint: disable=import-error
from kodi_six import xbmcplugin  # pylint: disable=import-error

from .common import get_handle
from .common import jsonrpc_play
from .common import write_pickled
from .constants import CONFIG
from .constants import StreamControl
from .logger import Logger
from .settings import AddonSettings
from .strings import encode_utf8
from .strings import i18n
from .items.track import create_track_item
from .utils import get_xml
from .utils import get_thumb_image
from ..plex import plex

LOG = Logger(CONFIG['name'])
SETTINGS = AddonSettings(CONFIG['id'])


def monitor_channel_transcode_playback(session_id, server):
    # Logic may appear backward, but this does allow for a failed start to be detected
    # First while loop waiting for start

    if SETTINGS.get_setting('monitoroff'):
        return

    count = 0
    monitor = xbmc.Monitor()
    player = xbmc.Player()

    LOG.debug('Not playing yet...sleeping for up to 20 seconds at 2 second intervals')
    while not player.isPlaying() and not monitor.abortRequested():
        count += 1
        if count >= 10:
            # Waited 20 seconds and still no movie playing - assume it isn't going to..
            return
        if monitor.waitForAbort(2.0):
            return

    LOG.debug('Waiting for playback to finish')
    while player.isPlaying() and not monitor.abortRequested():
        if monitor.waitForAbort(0.5):
            break

    LOG.debug('Playback Stopped')
    LOG.debug('Stopping PMS transcode job with session: %s' % session_id)
    server.stop_transcode_session(session_id)


def play_media_id_from_uuid(server_uuid, media_id, force=None, transcode=False,  # pylint: disable=too-many-arguments
                            transcode_profile=0, plex_network=None, player=False):
    if plex_network is None:
        plex_network = plex.Plex(load=True)

    server = plex_network.get_server_from_uuid(server_uuid)
    random_number = str(random.randint(1000000000, 9999999999))
    url = server.get_formatted_url('/library/metadata/%s?%s' % (media_id, random_number))
    play_library_media(url, force=force, transcode=transcode,
                       transcode_profile=transcode_profile, player=player)


def play_library_media(url, force=None, transcode=False, transcode_profile=0,  # pylint: disable=too-many-locals, too-many-statements, too-many-branches, too-many-arguments
                       plex_network=None, player=False):
    if plex_network is None:
        plex_network = plex.Plex(load=True)

    session = None

    server = plex_network.get_server_from_url(url)

    media_id = url.split('?')[0].split('&')[0].split('/')[-1]

    tree = get_xml(url)
    if tree is None:
        return

    streams = get_audio_subtitles_from_media(server, tree, True)

    stream_data = streams.get('full_data', {})
    stream_details = streams.get('details', [{}])
    stream_media = streams.get('media', {})

    if force and streams['type'] == 'music':
        play_playlist(server, streams)
        return

    url = select_media_to_play(streams, server)

    codec = stream_details[0].get('codec')
    resolution = stream_details[0].get('videoResolution')
    try:
        bit_depth = int(stream_details[0].get('bitDepth', 8))
    except ValueError:
        bit_depth = None

    if codec and (SETTINGS.get_setting('transcode_hevc') and codec.lower() == 'hevc'):
        transcode = True
    if resolution and (SETTINGS.get_setting('transcode_g1080') and resolution.lower() == '4k'):
        transcode = True
    if bit_depth and (SETTINGS.get_setting('transcode_g8bit') and bit_depth > 8):
        transcode = True

    if url is None:
        return

    try:
        transcode_profile = int(transcode_profile)
    except ValueError:
        transcode_profile = 0

    protocol = url.split(':', 1)[0]

    if protocol == 'file':
        LOG.debug('We are playing a local file')
        playback_url = url.split(':', 1)[1]
    elif protocol.startswith('http'):
        LOG.debug('We are playing a stream')
        if transcode:
            LOG.debug('We will be transcoding the stream')
            session, playback_url = \
                server.get_universal_transcode(streams['extra']['path'],
                                               transcode_profile=transcode_profile)
        else:
            playback_url = server.get_formatted_url(url)
    else:
        playback_url = url

    resume = int(int(stream_media['viewOffset']) / 1000)
    duration = int(int(stream_media['duration']) / 1000)

    LOG.debug('Resume has been set to %s ' % resume)
    if CONFIG['kodi_version'] >= 18:
        list_item = xbmcgui.ListItem(path=playback_url, offscreen=True)
    else:
        list_item = xbmcgui.ListItem(path=playback_url)
    if stream_data:
        list_item.setInfo(type=streams['type'], infoLabels=stream_data)
        thumb = stream_data.get('thumbnailImage', CONFIG['icon'])
        list_item.setArt({'icon': thumb, 'thumb': thumb})

    if force:

        if int(force) > 0:
            resume = int(int(force) / 1000)
        else:
            resume = force

    if force or session is not None:
        if resume:
            list_item.setProperty('ResumeTime', str(resume))
            list_item.setProperty('TotalTime', str(duration))
            list_item.setProperty('StartOffset', str(resume))
            LOG.debug('Playback from resume point: %s' % resume)

    if streams['type'] == 'picture':
        jsonrpc_play(playback_url)
    else:
        if streams['type'] == 'video' or streams['type'] == 'music':
            monitor_dict = {
                'media_id': media_id,
                'playing_file': playback_url,
                'session': session,
                'server': server,
                'streams': streams,
                'callback_args': {
                    'force': force,
                    'transcode': transcode,
                    'transcode_profile': transcode_profile
                }
            }
            write_pickled('playback_monitor.pickle', monitor_dict)

        if get_handle() == -1 or player:
            xbmc.Player().play(playback_url, list_item)
        else:
            xbmcplugin.setResolvedUrl(get_handle(), True, list_item)


def get_audio_subtitles_from_media(server, tree, full=False):  # pylint: disable=too-many-locals, too-many-statements, too-many-branches
    """
        Cycle through the Parts sections to find all 'selected' audio and subtitle streams
        If a stream is marked as selected=1 then we will record it in the dict
        Any that are not, are ignored as we do not need to set them
        We also record the media locations for playback decision later on
    """
    LOG.debug('Gather media stream info')

    parts = []
    parts_count = 0
    subtitle = {}
    sub_count = 0
    audio = {}
    audio_count = 0
    media = {}
    sub_offset = -1
    audio_offset = -1
    selected_sub_offset = -1
    selected_audio_offset = -1
    full_data = {}
    contents = 'type'
    extra = {}

    timings = tree.find('Video')
    if timings is not None:
        media_type = 'video'
        extra['path'] = timings.get('key')
    else:
        timings = tree.find('Track')
        if timings:
            media_type = 'music'
            extra['path'] = timings.get('key')
        else:
            timings = tree.find('Photo')
            if timings:
                media_type = 'picture'
                extra['path'] = timings.get('key')
            else:
                LOG.debug('No Video data found')
                return {}

    media['viewOffset'] = timings.get('viewOffset', 0)
    media['duration'] = timings.get('duration', 12 * 60 * 60)

    if full:
        if media_type == 'video':
            full_data = {
                'plot': encode_utf8(timings.get('summary', '')),
                'title': encode_utf8(timings.get('title', i18n('Unknown'))),
                'sorttitle':
                    encode_utf8(timings.get('titleSort',
                                            timings.get('title', i18n('Unknown')))),
                'rating': float(timings.get('rating', 0)),
                'studio': encode_utf8(timings.get('studio', '')),
                'mpaa': encode_utf8(timings.get('contentRating', '')),
                'year': int(timings.get('year', 0)),
                'tagline': timings.get('tagline', ''),
                'thumbnailImage': get_thumb_image(timings, server),
                'mediatype': 'video'
            }

            if timings.get('type') == 'episode':
                full_data['episode'] = int(timings.get('index', 0))
                full_data['aired'] = timings.get('originallyAvailableAt', '')
                full_data['tvshowtitle'] = \
                    encode_utf8(timings.get('grandparentTitle', tree.get('grandparentTitle', '')))
                full_data['season'] = int(timings.get('parentIndex', tree.get('parentIndex', 0)))
                full_data['mediatype'] = 'episode'

        elif media_type == 'music':

            full_data = {
                'TrackNumber': int(timings.get('index', 0)),
                'discnumber': int(timings.get('parentIndex', 0)),
                'title': str(timings.get('index', 0)).zfill(2) + '. ' +
                         encode_utf8(timings.get('title', i18n('Unknown'))),
                'rating': float(timings.get('rating', 0)),
                'album': encode_utf8(timings.get('parentTitle',
                                                 tree.get('parentTitle', ''))),
                'artist': encode_utf8(timings.get('grandparentTitle',
                                                  tree.get('grandparentTitle', ''))),
                'duration': int(timings.get('duration', 0)) / 1000,
                'thumbnailImage': get_thumb_image(timings, server)
            }

            extra['album'] = timings.get('parentKey')
            extra['index'] = timings.get('index')

    details = timings.findall('Media')

    media_details_list = []
    for media_details in details:

        try:
            if media_details.get('videoResolution') == 'sd':
                resolution = 'SD'
            elif int(media_details.get('videoResolution', 0)) > 1088:
                resolution = '4K'
            elif int(media_details.get('videoResolution', 0)) >= 1080:
                resolution = 'HD 1080'
            elif int(media_details.get('videoResolution', 0)) >= 720:
                resolution = 'HD 720'
            else:
                resolution = 'SD'
        except ValueError:
            resolution = ''

        media_details_temp = {
            'bitrate': round(float(media_details.get('bitrate', 0)) / 1000, 1),
            'bitDepth': media_details.get('bitDepth', 8),
            'videoResolution': resolution,
            'container': media_details.get('container', 'unknown'),
            'codec': media_details.get('videoCodec')
        }

        options = media_details.findall('Part')

        # Get the media locations (file and web) for later on
        for stuff in options:

            try:
                bits = stuff.get('key'), stuff.get('file')
                parts.append(bits)
                media_details_list.append(media_details_temp)
                parts_count += 1
            except:  # pylint: disable=bare-except
                pass

    # if we are deciding internally or forcing an external subs file, then collect the data
    if media_type == 'video' and SETTINGS.get_setting('streamControl') == StreamControl().PLEX:

        contents = 'all'
        tags = tree.getiterator('Stream')

        for bits in tags:
            stream = dict(bits.items())

            # Audio Streams
            if stream['streamType'] == '2':
                audio_count += 1
                audio_offset += 1
                if stream.get('selected') == '1':
                    LOG.debug('Found preferred audio id: %s ' % stream['id'])
                    audio = stream
                    selected_audio_offset = audio_offset

            # Subtitle Streams
            elif stream['streamType'] == '3':

                if sub_offset == -1:
                    sub_offset = int(stream.get('index', -1))
                elif 0 < int(stream.get('index', -1)) < sub_offset:
                    sub_offset = int(stream.get('index', -1))

                if stream.get('selected') == '1':
                    LOG.debug('Found preferred subtitles id : %s ' % stream['id'])
                    sub_count += 1
                    subtitle = stream
                    if stream.get('key'):
                        subtitle['key'] = server.get_formatted_url(stream['key'])
                    else:
                        selected_sub_offset = int(stream.get('index')) - sub_offset

    else:
        LOG.debug('Stream selection is set OFF')

    stream_data = {
        'contents': contents,  # What type of data we are holding
        'audio': audio,  # Audio data held in a dict
        'audio_count': audio_count,  # Number of audio streams
        'subtitle': subtitle,  # Subtitle data (embedded) held as a dict
        'sub_count': sub_count,  # Number of subtitle streams
        'parts': parts,  # The different media locations
        'parts_count': parts_count,  # Number of media locations
        'media': media,  # Resume/duration data for media
        'details': media_details_list,  # Bitrate, resolution and container for each part
        'sub_offset': selected_sub_offset,  # Stream index for selected subs
        'audio_offset': selected_audio_offset,  # Stream index for select audio
        'full_data': full_data,  # Full metadata extract if requested
        'type': media_type,  # Type of metadata
        'extra': extra
    }  # Extra data

    LOG.debug(stream_data)
    return stream_data


def select_media_to_play(data, server):
    # if we have two or more files for the same movie, then present a screen
    result = 0
    dvd_playback = False

    count = data['parts_count']
    options = data['parts']
    details = data['details']

    if count > 1:

        dialog_options = []
        dvd_index = []
        index_count = 0
        for items in options:

            if items[1]:
                name = items[1].split('/')[-1]
                # name='%s %s %sMbps' % (items[1].split('/')[-1],
                # details[index_count]['videoResolution'], details[index_count]['bitrate'])
            else:
                name = '%s %s %sMbps' % (items[0].split('.')[-1],
                                         details[index_count]['videoResolution'],
                                         details[index_count]['bitrate'])

            if SETTINGS.get_setting('forcedvd'):
                if '.ifo' in name.lower():
                    LOG.debug('Found IFO DVD file in ' + name)
                    name = 'DVD Image'
                    dvd_index.append(index_count)

            dialog_options.append(name)
            index_count += 1

        LOG.debug('Create selection dialog box - we have a decision to make!')
        start_time = xbmcgui.Dialog()
        result = start_time.select(i18n('Select media to play'), dialog_options)
        if result == -1:
            return None

        if result in dvd_index:
            LOG.debug('DVD Media selected')
            dvd_playback = True

    else:
        if SETTINGS.get_setting('forcedvd'):
            if '.ifo' in options[result]:
                dvd_playback = True

    media_url = select_media_type(
        {
            'key': options[result][0],
            'file': options[result][1]
        },
        server, dvd_playback
    )

    LOG.debug('We have selected media at %s' % media_url)
    return media_url


def select_media_type(part_data, server, dvd_playback=False):  # pylint: disable=too-many-statements, too-many-branches
    stream = part_data['key']
    filename = part_data['file']
    file_location = ''

    if (filename is None) or (SETTINGS.get_stream() == '1'):
        LOG.debug('Selecting stream')
        return server.get_formatted_url(stream)

    # First determine what sort of 'file' file is

    if filename[0:2] == '\\\\':
        LOG.debug('Detected UNC source file')
        file_type = 'UNC'
    elif filename[0:1] in ['/', '\\']:
        LOG.debug('Detected unix source file')
        file_type = 'nixfile'
    elif filename[1:3] == ':\\' or filename[1:2] == ':/':
        LOG.debug('Detected windows source file')
        file_type = 'winfile'
    else:
        LOG.debug('Unknown file type source: %s' % filename)
        file_type = None

    # 0 is auto select.  basically check for local file first, then stream if not found
    if SETTINGS.get_stream() == '0':
        # check if the file can be found locally
        if file_type in ['nixfile', 'winfile']:
            LOG.debug('Checking for local file')
            try:
                exists = open(filename, 'r')
                LOG.debug('Local f found, will use this')
                exists.close()
                return 'file:%s' % filename
            except:  # pylint: disable=bare-except
                pass

        LOG.debug('No local file')
        if dvd_playback:
            LOG.debug('Forcing SMB for DVD playback')
            SETTINGS.set_stream('2')
        else:
            return server.get_formatted_url(stream)

    # 2 is use SMB
    elif SETTINGS.get_stream() == '2' or SETTINGS.get_stream() == '3':

        filename = unquote(filename)
        if SETTINGS.get_stream() == '2':
            protocol = 'smb'
        else:
            protocol = 'afp'

        LOG.debug('Selecting smb/unc')
        if file_type == 'UNC':
            file_location = '%s:%s' % (protocol, filename.replace('\\', '/'))
        else:
            # Might be OSX type, in which case, remove Volumes and replace with server
            server = server.get_location().split(':')[0]
            login_string = ''

            if SETTINGS.get_setting('nasoverride'):
                if SETTINGS.get_setting('nasoverrideip'):
                    server = SETTINGS.get_setting('nasoverrideip')
                    LOG.debug('Overriding server with: %s' % server)

                if SETTINGS.get_setting('nasuserid'):
                    login_string = '%s:%s@' % (SETTINGS.get_setting('nasuserid'),
                                               SETTINGS.get_setting('naspass'))
                    LOG.debug('Adding AFP/SMB login info for user: %s' %
                              SETTINGS.get_setting('nasuserid'))

            if filename.find('Volumes') > 0:
                file_location = '%s:/%s' % \
                                (protocol, filename.replace('Volumes', login_string + server))
            else:
                if file_type == 'winfile':
                    file_location = ('%s://%s%s/%s' %
                                     (protocol, login_string, server,
                                      filename[3:].replace('\\', '/')))
                else:
                    # else assume its a file local to server available over smb/samba.
                    # Add server name to file path.
                    file_location = '%s://%s%s%s' % (protocol, login_string, server, filename)

        if SETTINGS.get_setting('nasoverride') and SETTINGS.get_setting('nasroot'):
            # Re-root the file path
            LOG.debug('Altering path %s so root is: %s' %
                      (file_location, SETTINGS.get_setting('nasroot')))
            if '/' + SETTINGS.get_setting('nasroot') + '/' in file_location:
                components = file_location.split('/')
                index = components.index(SETTINGS.get_setting('nasroot'))
                for _ in list(range(3, index)):
                    components.pop(3)
                file_location = '/'.join(components)
    else:
        LOG.debug('No option detected, streaming is safest to choose')
        file_location = server.get_formatted_url(stream)

    LOG.debug('Returning URL: %s ' % file_location)
    return file_location


def play_playlist(server, data):
    LOG.debug('Creating new playlist')
    playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
    playlist.clear()

    tree = get_xml(server.get_url_location() + data['extra'].get('album') + '/children')

    if tree is None:
        return

    track_tags = tree.findall('Track')
    for track in track_tags:
        LOG.debug('Adding playlist item')

        url, details = create_track_item(server, tree, track, listing=False)
        if CONFIG['kodi_version'] >= 18:
            list_item = xbmcgui.ListItem(details.get('title', i18n('Unknown')), offscreen=True)
        else:
            list_item = xbmcgui.ListItem(details.get('title', i18n('Unknown')))
        thumb = data['full_data'].get('thumbnailImage', CONFIG['icon'])
        list_item.setArt({'icon': thumb, 'thumb': thumb})
        list_item.setInfo(type='music', infoLabels=details)
        playlist.add(url, list_item)

    index = int(data['extra'].get('index', 0)) - 1
    LOG.debug('Playlist complete.  Starting playback from track %s [playlist index %s] ' %
              (data['extra'].get('index', 0), index))
    xbmc.Player().playselected(index)
