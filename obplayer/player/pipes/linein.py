#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Copyright 2012-2015 OpenBroadcaster, Inc.

This file is part of OpenBroadcaster Player.

OpenBroadcaster Player is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

OpenBroadcaster Player is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with OpenBroadcaster Player.  If not, see <http://www.gnu.org/licenses/>.
"""

import obplayer

import os
import traceback

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, GstVideo

from .base import ObGstPipeline


class ObLineInPipeline (ObGstPipeline):
    min_class = [ 'audio' ]
    max_class = [ 'audio' ]

    def __init__(self, name, player):
        ObGstPipeline.__init__(self, name)
        self.player = player

        self.pipeline = Gst.Pipeline(name)

        audio_input = obplayer.Config.setting('audio_in_mode')
        if audio_input == 'alsa':
            self.audiosrc = Gst.ElementFactory.make('alsasrc', name + '-src')
            alsa_device = obplayer.Config.setting('audio_in_alsa_device')
            if alsa_device != '':
                self.audiosrc.set_property('device', alsa_device)

        elif audio_input == 'jack':
            self.audiosrc = Gst.ElementFactory.make('jackaudiosrc', name + '-src')
            self.audiosrc.set_property('connect', 0)  # don't autoconnect ports.
            name = obplayer.Config.setting('audio_in_jack_name')
            self.audiosrc.set_property('client-name', name if name else 'obplayer')

        elif audio_input == 'oss':
            self.audiosrc = Gst.ElementFactory.make('osssrc', name + '-src')

        elif audio_input == 'pulse':
            self.audiosrc = Gst.ElementFactory.make('pulsesrc', name + '-src')
            self.audiosrc.set_property('client-name', 'obplayer-pipe: line-in')

        elif audio_input == 'test':
            self.audiosrc = Gst.ElementFactory.make('fakesrc', name + '-src')

        else:
            self.audiosrc = Gst.ElementFactory.make('autoaudiosrc', name + '-src')

        self.pipeline.add(self.audiosrc)

        self.queue = Gst.ElementFactory.make('queue2', name + '-queue')
        self.pipeline.add(self.queue)
        self.audiosrc.link(self.queue)

        self.audioconvert = Gst.ElementFactory.make('audioconvert', name + '-convert')
        self.pipeline.add(self.audioconvert)
        self.queue.link(self.audioconvert)

        self.audiosink = None
        self.fakesink = Gst.ElementFactory.make('fakesink', name + '-fakesink')
        self.set_property('audio-src', self.fakesink)

        self.register_signals()

    def set_property(self, property, value):
        if property == 'audio-sink':
            if self.audiosink:
                self.pipeline.remove(self.audiosink)
            self.audiosink = value
            if self.audiosink:
                self.pipeline.add(self.audiosink)
                self.audioconvert.link(self.audiosink)

    def patch(self, mode):
        self.wait_state(Gst.State.NULL)
        if 'audio' in mode:
            self.set_property('audio-sink', self.player.outputs['audio'].get_bin())
        ObGstPipeline.patch(self, mode)

        self.wait_state(Gst.State.PLAYING)
        if obplayer.Config.setting('gst_init_callback'):
            os.system(obplayer.Config.setting('gst_init_callback'))

    def unpatch(self, mode):
        self.wait_state(Gst.State.NULL)
        if 'audio' in mode:
            self.set_property('audio-sink', self.fakesink)
        ObGstPipeline.unpatch(self, mode)
        if len(self.mode) > 0:
            self.wait_state(Gst.State.PLAYING)
            if obplayer.Config.setting('gst_init_callback'):
                os.system(obplayer.Config.setting('gst_init_callback'))


