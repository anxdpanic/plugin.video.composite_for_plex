# -*- coding: utf-8 -*-
"""

    Copyright (C) 2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import threading

from kodi_six import xbmc  # pylint: disable=import-error

from .common import read_pickled
from .constants import CONFIG
from .constants import StreamControl
from .logger import Logger
from .settings import AddonSettings
from .strings import encode_utf8
from .strings import i18n
from .up_next import UpNext

LOG = Logger(CONFIG['name'], 'player')
SETTINGS = AddonSettings()


class PlaybackMonitorThread(threading.Thread):
    LOG = Logger(CONFIG['name'], 'PlaybackMonitorThread')
    MONITOR = xbmc.Monitor()
    PLAYER = xbmc.Player()

    def __init__(self, monitor_dict):
        super(PlaybackMonitorThread, self).__init__()
        self._stopped = threading.Event()
        self._ended = threading.Event()

        self._monitor_dict = monitor_dict

        self.daemon = True
        self.start()

    def media_id(self):
        return self._monitor_dict.get('media_id')

    def playing_file(self):
        return self._monitor_dict.get('playing_file')

    @staticmethod
    def plugin_path():
        return 'plugin://%s/' % CONFIG['id']

    def server(self):
        return self._monitor_dict.get('server')

    def session(self):
        return self._monitor_dict.get('session')

    def streams(self):
        return self._monitor_dict.get('streams')

    def stop(self):
        self.LOG.debug('[%s]: Stop event set...' % self.media_id())
        self._stopped.set()

    def stopped(self):
        return self._stopped.is_set()

    def end(self):
        self.LOG.debug('[%s]: End event set...' % self.media_id())
        self._ended.set()

    def ended(self):
        return self._ended.is_set()

    def _wait_for_playback(self):
        np_wait_time = 0.5
        np_waited = 0.0

        while not self.PLAYER.isPlaying() and not self.MONITOR.abortRequested():
            self.LOG.debug('Waiting for playback to start')

            xbmc.sleep(int(np_wait_time * 1000))
            if np_waited >= 5:
                self.stop()
                return

            np_waited += np_wait_time

    def report_playback_progress(self, current_time, total_time,
                                 progress, played_time=-1):
        if played_time > -1:
            if played_time == current_time:
                self.LOG.debug('Video paused at: %s secs of %s @ %s%%' %
                               (current_time, total_time, progress))
                self.server().report_playback_progress(self.media_id(),
                                                       current_time * 1000,
                                                       state='paused',
                                                       duration=total_time * 1000)
            else:
                self.LOG.debug('Video played time: %s secs of %s @ %s%%' %
                               (current_time, total_time, progress))
                self.server().report_playback_progress(self.media_id(),
                                                       current_time * 1000,
                                                       state='playing',
                                                       duration=total_time * 1000)
                played_time = current_time
        else:
            self.LOG.debug('Playback Stopped: %s secs of %s @ %s%%' %
                           (current_time, total_time, progress))
            # report_playback_progress state=stopped will adjust current time to match duration
            # and mark media as watched if progress >= 98%
            self.server().report_playback_progress(self.media_id(), current_time * 1000,
                                                   state='stopped', duration=total_time * 1000)
        return played_time

    def run(self):
        current_time = 0
        played_time = 0
        progress = 0
        total_time = 0

        if self.session():
            self.LOG.debug('We are monitoring a transcode session')

        self._wait_for_playback()

        if self.streams():
            set_audio_subtitles(self.streams())

        wait_time = 0.5
        waited = 0.0

        # Whilst the file is playing back
        while self.PLAYER.isPlaying() and not self.MONITOR.abortRequested():

            try:
                current_file = self.PLAYER.getPlayingFile()
                if current_file != self.playing_file() and \
                        not (current_file.startswith(self.plugin_path())
                             and self.media_id() in current_file) or self.stopped():
                    self.stop()
                    break
            except RuntimeError:
                pass

            try:
                current_time = int(self.PLAYER.getTime())
                total_time = int(self.PLAYER.getTotalTime())
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
                played_time = self.report_playback_progress(current_time, total_time,
                                                            progress, played_time)

            if self.MONITOR.waitForAbort(wait_time):
                break

            waited += wait_time

        if current_time != 0 and total_time != 0:
            _ = self.report_playback_progress(current_time, total_time, progress)

        if self.session() is not None:
            self.LOG.debug('Stopping PMS transcode job with session %s' % self.session())
            self.server().stop_transcode_session(self.session())


class CallbackPlayer(xbmc.Player):
    LOG = Logger(CONFIG['name'], 'CallbackPlayer')

    def __init__(self, window, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

        self.threads = []
        self.window = window

    def stop_threads(self):
        for thread in self.threads:
            if thread.ended():
                continue

            if not thread.stopped():
                self.LOG.debug('[%s]: stopping...' % thread.media_id())
                thread.stop()

        for thread in self.threads:
            if thread.stopped() and not thread.ended():
                try:
                    thread.join()
                except RuntimeError:
                    pass

    def cleanup_threads(self, only_ended=False):
        active_threads = []
        for thread in self.threads:
            if only_ended and not thread.ended():
                active_threads.append(thread)
                continue

            if thread.ended():
                self.LOG.debug('[%s]: clean up...' % thread.media_id())
            else:
                self.LOG.debug('[%s]: stopping...' % thread.media_id())
                if not thread.stopped():
                    thread.stop()
            try:
                thread.join()
            except RuntimeError:
                pass
        self.LOG.debug('Active monitor threads: |%s|' %
                       ', '.join([thread.media_id() for thread in active_threads]))
        self.threads = active_threads

    def onPlayBackStarted(self):  # pylint: disable=invalid-name
        monitor_playback = not SETTINGS.get_setting('monitoroff', fresh=True)
        playback_dict = read_pickled('playback_monitor.pickle')

        self.cleanup_threads()
        if monitor_playback and playback_dict:
            self.threads.append(PlaybackMonitorThread(playback_dict))

        if not monitor_playback:
            self.LOG('Playback monitoring is disabled ...')
        elif not playback_dict:
            self.LOG('Playback monitoring failed to start, missing required {} ...')

        if playback_dict:
            full_data = playback_dict.get('streams', {}).get('full_data', {})
            media_type = full_data.get('mediatype', '').lower()
            if SETTINGS.use_up_next() and media_type == 'episode':
                self.LOG('Using Up Next ...')
                UpNext(server=playback_dict.get('server'),
                       media_id=playback_dict.get('media_id'),
                       callback_args=playback_dict.get('callback_args', {})).run()
            else:
                self.LOG('Up Next is disabled ...')

    def onPlayBackEnded(self):  # pylint: disable=invalid-name
        self.stop_threads()
        self.cleanup_threads()

    def onPlayBackStopped(self):  # pylint: disable=invalid-name
        self.onPlayBackEnded()

    def onPlayBackError(self):  # pylint: disable=invalid-name
        self.onPlayBackEnded()


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
