"""

    Copyright (C) 2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

import threading

import xbmc

from six.moves import cPickle as pickle

from .common import CONFIG
from .common import STREAM_CONTROL
from .common import PrintDebug
from .common import encode_utf8
from .common import i18n
from .common import settings


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
                if (current_file != self.playing_file and
                    not (current_file.startswith('plugin://plugin.video.composite_for_plex/') and
                         self.media_id in current_file)) or self.stopped():
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
                    self.log.debug('Video paused at: %s secs of %s @ %s%%' % (current_time, total_time, progress))
                    self.server.report_playback_progress(self.media_id, current_time * 1000, state='paused', duration=total_time * 1000)
                else:
                    self.log.debug('Video played time: %s secs of %s @ %s%%' % (current_time, total_time, progress))
                    self.server.report_playback_progress(self.media_id, current_time * 1000, state='playing', duration=total_time * 1000)
                    played_time = current_time

            if self.monitor.waitForAbort(wait_time):
                break

            waited += wait_time

        if current_time != 0 and total_time != 0:
            self.log.debug('Playback Stopped: %s secs of %s @ %s%%' % (current_time, total_time, progress))
            # report_playback_progress state=stopped will adjust current time to match duration and mark media as watched if progress >= 98%
            self.server.report_playback_progress(self.media_id, current_time * 1000, state='stopped', duration=total_time * 1000)

        if self.session is not None:
            self.log.debug('Stopping PMS transcode job with session %s' % self.session)
            self.server.stop_transcode_session(self.session)


class CallbackPlayer(xbmc.Player):
    def __init__(self, window, *args, **kwargs):
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

        self.log.debug('Active monitor threads: |%s|' % ', '.join([thread.media_id for thread in active_threads]))
        self.threads = active_threads

    def onPlayBackStarted(self):
        if settings.get_setting('monitoroff'):
            self.window.clearProperty('composite.monitor_dict')
            return

        if self.window.getProperty('composite.monitor_dict'):
            playback_dict = pickle.loads(self.window.getProperty('composite.monitor_dict'))
            self.window.clearProperty('composite.monitor_dict')
            self.cleanup_threads()
            self.threads.append(PlaybackMonitorThread(playback_dict))

    def onPlayBackEnded(self):
        self.stop_threads()
        self.cleanup_threads()

    def onPlayBackStopped(self):
        self.onPlayBackEnded()

    def onPlayBackError(self):
        self.onPlayBackEnded()


def set_audio_subtitles(stream):
    """
        Take the collected audio/sub stream data and apply to the media
        If we do not have any subs then we switch them off
    """

    # If we have decided not to collect any sub data then do not set subs
    log = PrintDebug(CONFIG['name'], 'player')

    player = xbmc.Player()

    if stream['contents'] == 'type':
        log.debug('No audio or subtitle streams to process.')

        # If we have decided to force off all subs, then turn them off now and return
        if settings.get_setting('streamControl') == STREAM_CONTROL.NEVER:
            player.showSubtitles(False)
            log.debug('All subs disabled')

        return True

    # Set the AUDIO component
    if settings.get_setting('streamControl') == STREAM_CONTROL.PLEX:
        log.debug('Attempting to set Audio Stream')

        audio = stream['audio']

        if stream['audio_count'] == 1:
            log.debug('Only one audio stream present - will leave as default')

        elif audio:
            log.debug('Attempting to use selected language setting: %s' %
                      encode_utf8(audio.get('language', audio.get('languageCode', i18n('Unknown')))))
            log.debug('Found preferred language at index %s' % stream['audio_offset'])
            try:
                player.setAudioStream(stream['audio_offset'])
                log.debug('Audio set')
            except:
                log.debug('Error setting audio, will use embedded default stream')

    # Set the SUBTITLE component
    if settings.get_setting('streamControl') == STREAM_CONTROL.PLEX:
        log.debug('Attempting to set preferred subtitle Stream')
        subtitle = stream['subtitle']
        if subtitle:
            log.debug('Found preferred subtitle stream')
            try:
                player.showSubtitles(False)
                if subtitle.get('key'):
                    player.setSubtitles(subtitle['key'])
                else:
                    log.debug('Enabling embedded subtitles at index %s' % stream['sub_offset'])
                    player.setSubtitleStream(int(stream['sub_offset']))

                player.showSubtitles(True)
                return True
            except:
                log.debug('Error setting subtitle')

        else:
            log.debug('No preferred subtitles to set')
            player.showSubtitles(False)
