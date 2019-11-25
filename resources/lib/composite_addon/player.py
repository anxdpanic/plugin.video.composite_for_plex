# -*- coding: utf-8 -*-
"""

    Copyright (C) 2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import threading

import xbmc  # pylint: disable=import-error

from .common import CONFIG
from .common import StreamControl
from .common import PrintDebug
from .common import encode_utf8
from .common import i18n
from .common import notify_all
from .common import read_pickled
from .common import SETTINGS

LOG = PrintDebug(CONFIG['name'], 'player')


class PlaybackMonitorThread(threading.Thread):
    def __init__(self, monitor_dict):
        super(PlaybackMonitorThread, self).__init__()

        self._stopped = threading.Event()
        self._ended = threading.Event()

        self.log = PrintDebug(CONFIG['name'], 'monitor_thread')

        self.player = xbmc.Player()
        self.monitor = xbmc.Monitor()

        self.monitor_dict = monitor_dict

        self.media_id = self.monitor_dict.get('media_id')
        self.playing_file = self.monitor_dict.get('playing_file')
        self.server = self.monitor_dict.get('server')
        self.session = self.monitor_dict.get('session')
        self.streams = self.monitor_dict.get('streams')

        self.plugin_path = 'plugin://%s/' % CONFIG['id']

        self.daemon = True
        self.start()

    def stop(self):
        self.log.debug('[%s]: Stop event set...' % self.media_id)
        self._stopped.set()

    def stopped(self):
        return self._stopped.is_set()

    def end(self):
        self.log.debug('[%s]: End event set...' % self.media_id)
        self._ended.set()

    def ended(self):
        return self._ended.is_set()

    def abort_now(self):
        return not self.player.isPlaying() or self.monitor.abortRequested() or self.stopped()

    def run(self):
        current_time = 0
        played_time = 0
        progress = 0
        total_time = 0

        if self.session:
            self.log.debug('We are monitoring a transcode session')

        np_wait_time = 0.5
        np_waited = 0.0

        while not self.player.isPlaying() and not self.monitor.abortRequested():
            self.log.debug('Waiting for playback to start')

            xbmc.sleep(int(np_wait_time * 1000))
            if np_waited >= 5:
                self.end()
                return

            np_waited += np_wait_time

        if self.streams:
            set_audio_subtitles(self.streams)

        wait_time = 0.5
        waited = 0.0

        # Whilst the file is playing back
        while self.player.isPlaying() and not self.monitor.abortRequested():

            try:
                current_file = self.player.getPlayingFile()
                if current_file != self.playing_file and \
                        not (current_file.startswith(self.plugin_path)
                             and self.media_id in current_file) or self.stopped():
                    self.stop()
                    break
            except RuntimeError:
                pass

            try:
                current_time = int(self.player.getTime())
                total_time = int(self.player.getTotalTime())
            except RuntimeError:
                pass

            try:
                progress = int((float(current_time) / float(total_time)) * 100)
            except ZeroDivisionError:
                progress = 0

            try:
                report = int((float(waited) / 10.0)) >= 1
            except ZeroDivisionError:
                report = False

            if report:  # only report every ~10 seconds, times are updated at 0.5 seconds
                waited = 0.0
                if played_time == current_time:
                    self.log.debug('Video paused at: %s secs of %s @ %s%%' %
                                   (current_time, total_time, progress))
                    self.server.report_playback_progress(self.media_id,
                                                         current_time * 1000,
                                                         state='paused',
                                                         duration=total_time * 1000)
                else:
                    self.log.debug('Video played time: %s secs of %s @ %s%%' %
                                   (current_time, total_time, progress))
                    self.server.report_playback_progress(self.media_id,
                                                         current_time * 1000,
                                                         state='playing',
                                                         duration=total_time * 1000)
                    played_time = current_time

            if self.monitor.waitForAbort(wait_time):
                break

            waited += wait_time

        if current_time != 0 and total_time != 0:
            self.log.debug('Playback Stopped: %s secs of %s @ %s%%' %
                           (current_time, total_time, progress))
            # report_playback_progress state=stopped will adjust current time to match duration
            # and mark media as watched if progress >= 98%
            self.server.report_playback_progress(self.media_id, current_time * 1000,
                                                 state='stopped', duration=total_time * 1000)

        if self.session is not None:
            self.log.debug('Stopping PMS transcode job with session %s' % self.session)
            self.server.stop_transcode_session(self.session)


class CallbackPlayer(xbmc.Player):
    def __init__(self, window, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

        self.log = PrintDebug(CONFIG['name'], 'callback_player')
        self.threads = []
        self.window = window

    def stop_threads(self):
        for thread in self.threads:
            if thread.ended():
                continue

            if not thread.stopped():
                self.log.debug('[%s]: stopping...' % thread.media_id)
                thread.stop()

        for thread in self.threads:
            if thread.stopped() and not thread.ended():
                try:
                    thread.join()
                except RuntimeError:
                    pass

    def cleanup_threads(self, only_ended=True):
        active_threads = []
        for thread in self.threads:
            if only_ended and not thread.ended():
                active_threads.append(thread)
                continue

            if thread.ended():
                self.log.debug('[%s]: clean up...' % thread.media_id)
            else:
                self.log.debug('[%s]: stopping...' % thread.media_id)
                if not thread.stopped():
                    thread.stop()
            try:
                thread.join()
            except RuntimeError:
                pass

        self.log.debug('Active monitor threads: |%s|' %
                       ', '.join([thread.media_id for thread in active_threads]))
        self.threads = active_threads

    def onPlayBackStarted(self):  # pylint: disable=invalid-name
        monitor_playback = SETTINGS.get_setting('monitoroff', fresh=True)
        playback_dict = read_pickled('playback_monitor.pickle')

        if monitor_playback and playback_dict:
            self.cleanup_threads()
            self.threads.append(PlaybackMonitorThread(playback_dict))

        if not monitor_playback:
            self.log('Playback monitoring is disabled ...')
        elif not playback_dict:
            self.log('Playback monitoring failed to start, missing required {} ...')

        full_data = playback_dict.get('streams', {}).get('full_data', {})
        media_type = full_data.get('mediatype', '').lower()
        if SETTINGS.use_up_next() and media_type == 'episode':
            self.log('Using Up Next ...')
            next_up(server=playback_dict.get('server'),
                    media_id=playback_dict.get('media_id'),
                    callback_args=playback_dict.get('callback_args', {}))
        else:
            self.log('Up Next is disabled ...')

    def onPlayBackEnded(self):  # pylint: disable=invalid-name
        self.stop_threads()
        self.cleanup_threads()

    def onPlayBackStopped(self):  # pylint: disable=invalid-name
        self.onPlayBackEnded()

    def onPlayBackError(self):  # pylint: disable=invalid-name
        self.onPlayBackEnded()


# pylint: disable=too-many-nested-blocks
def next_up(server, media_id, callback_args):
    try:
        current_metadata = server.get_metadata(media_id)
        current_metadata = current_metadata[0]
    except:  # pylint: disable=bare-except
        return

    current_extended = None
    next_metadata = None
    next_extended = None

    if current_metadata:
        season = int(current_metadata.get('parentIndex'))
        episode = int(current_metadata.get('index'))
        LOG.debug('Found metadata for S%sE%s' % (str(season).zfill(2), str(episode).zfill(2)))

        season_episodes = server.get_children(current_metadata.get('parentRatingKey'))
        if season_episodes is not None:
            for video in season_episodes:
                if video.get('index'):
                    if int(video.get('index')) == episode:
                        LOG.debug('Found extended metadata for S%sE%s' %
                                  (str(season).zfill(2), str(episode).zfill(2)))
                        current_extended = video
                    elif int(video.get('index')) == episode + 1:
                        LOG.debug('Found extended metadata for S%sE%s' %
                                  (str(season).zfill(2), str(episode + 1).zfill(2)))
                        next_extended = video

                if current_extended is not None and next_extended is not None:
                    break

            if next_extended is None:
                LOG.debug('Looking for S%s' % str(season + 1).zfill(2))
                tv_seasons = server.get_children(current_metadata.get('grandparentRatingKey'))
                next_season = None

                if tv_seasons:
                    LOG.debug('Found tv show seasons')
                    for directory in tv_seasons:
                        if directory.get('index'):
                            if int(directory.get('index')) == season + 1:
                                LOG.debug('Found season S%s' % str(season + 1).zfill(2))
                                next_season = directory
                                break

                    if next_season is not None:
                        LOG.debug('Looking for S%s episodes' % str(season + 1).zfill(2))
                        season_episodes = server.get_children(next_season.get('ratingKey'))
                        if season_episodes:
                            for video in season_episodes:
                                if int(video.get('index')) == 1:
                                    LOG.debug('Found extended metadata for S%sE01' %
                                              str(season + 1).zfill(2))
                                    next_extended = video
                                    break

        if next_extended is not None and next_extended.get('ratingKey'):
            try:
                next_metadata = server.get_metadata(next_extended.get('ratingKey'))
                next_metadata = next_metadata[0]
            except:  # pylint: disable=bare-except
                return

            LOG.debug('Found metadata for S%sE%s' %
                      (next_metadata.get('parentIndex', '0').zfill(2),
                       next_metadata.get('index', '0').zfill(2)))

        if current_metadata is not None and next_metadata is not None:
            current_episode = get_nextup_episode(server, current_metadata, current_extended)
            if current_episode:
                LOG.debug('Got current episode Up Next data')
                next_episode = get_nextup_episode(server, next_metadata, next_extended)
                if next_episode:
                    LOG.debug('Got next episode Up Next data')
                    next_info = {
                        "current_episode": current_episode,
                        "next_episode": next_episode,
                        "play_info": {
                            "media_id": next_metadata.get('ratingKey', '0'),
                            "force": callback_args.get('force', None),
                            "transcode": callback_args.get('transcode', False),
                            "transcode_profile": callback_args.get('transcode_profile', 0),
                            "server_uuid": server.uuid
                        }
                    }
                    LOG.debug('Notifying Up Next')
                    notify_all('upnext_data', next_info)


def get_nextup_episode(server, metadata, extended_metadata=None):
    if extended_metadata is None:
        extended_metadata = {}

    fanart = ''
    image = ''
    grandparent_image = ''

    if metadata.get('thumb'):
        image_url = metadata.get('thumb')
        if image_url.startswith('/'):
            image_url = server.get_url_location() + image_url
        image = server.get_kodi_header_formatted_url(image_url)
    if metadata.get('grandparentThumb'):
        image_url = metadata.get('grandparentThumb')
        if image_url.startswith('/'):
            image_url = server.get_url_location() + image_url
        grandparent_image = server.get_kodi_header_formatted_url(image_url)
    if metadata.get('art'):
        image_url = metadata.get('art')
        if image_url.startswith('/'):
            image_url = server.get_url_location() + image_url
        fanart = server.get_kodi_header_formatted_url(image_url)

    episode = {
        "episodeid": '_%s' % metadata.get('ratingKey', '-1'),
        "tvshowid": '_%s' % metadata.get('parentRatingKey', '-1'),
        "title": metadata.get('title', ''),
        "art": {
            "tvshow.poster": grandparent_image,
            "thumb": image,
            "tvshow.fanart": fanart,
            "tvshow.landscape": "",
            "tvshow.clearart": "",
            "tvshow.clearlogo": "",
        },
        "plot": metadata.get('summary', ''),
        "showtitle": metadata.get('grandparentTitle', ''),
        "playcount": int(metadata.get('viewCount', extended_metadata.get('viewCount', 0))),
        "season": int(metadata.get('parentIndex', 0)),
        "episode": int(metadata.get('index', 0)),
        "rating": float(metadata.get('rating', extended_metadata.get('rating', 0))),
        "firstaired": metadata.get('originallyAvailableAt', '')
    }

    return episode


def set_audio_subtitles(stream):
    """
        Take the collected audio/sub stream data and apply to the media
        If we do not have any subs then we switch them off
    """

    # If we have decided not to collect any sub data then do not set subs

    player = xbmc.Player()
    control = SETTINGS.get_setting('streamControl', fresh=True)

    if stream['contents'] == 'type':
        LOG.debug('No audio or subtitle streams to process.')

        # If we have decided to force off all subs, then turn them off now and return
        if control == StreamControl.NEVER:
            player.showSubtitles(False)
            LOG.debug('All subs disabled')

        return

    # Set the AUDIO component
    if control == StreamControl.PLEX:
        LOG.debug('Attempting to set Audio Stream')

        audio = stream['audio']

        if stream['audio_count'] == 1:
            LOG.debug('Only one audio stream present - will leave as default')

        elif audio:
            LOG.debug(
                'Attempting to use selected language setting: %s' %
                encode_utf8(audio.get('language', audio.get('languageCode', i18n('Unknown'))))
            )
            LOG.debug('Found preferred language at index %s' % stream['audio_offset'])
            try:
                player.setAudioStream(stream['audio_offset'])
                LOG.debug('Audio set')
            except:  # pylint: disable=bare-except
                LOG.debug('Error setting audio, will use embedded default stream')

    # Set the SUBTITLE component
    if control == StreamControl.PLEX:
        LOG.debug('Attempting to set preferred subtitle Stream')
        subtitle = stream['subtitle']
        if subtitle:
            LOG.debug('Found preferred subtitle stream')
            try:
                player.showSubtitles(False)
                if subtitle.get('key'):
                    player.setSubtitles(subtitle['key'])
                else:
                    LOG.debug('Enabling embedded subtitles at index %s' % stream['sub_offset'])
                    player.setSubtitleStream(int(stream['sub_offset']))

                player.showSubtitles(True)
                return
            except:  # pylint: disable=bare-except
                LOG.debug('Error setting subtitle')

        else:
            LOG.debug('No preferred subtitles to set')
            player.showSubtitles(False)
