#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set et sw=4 ts=4 ft=python:
"""play.py [-h|--help] [-m|--man] [-e|--exact] [music-dir]"""
from __future__ import print_function
import mplayer
import os
import random
import stat
import subprocess
import sys
import time

import qsio

# --- default configuration ------
DEFAULT_COLLECTION = "/all/music/"
# --- end default configuration --


def usage(code, msg=''):
    if msg:
        print("** Error: ", msg)
    print(__doc__)
    #print(__doc__ % globals())
    sys.exit(code)


def help():
    usage(1)


def man():
    print("*play* \tscript to choose subdirectory (artist)\n",
          "\tand play all music files contained (recursively looked up)")
    print()
    print("[exact]\tmeans that specified music-dir will be searched for\n",
          "\tsound files as a whole, no artist-subdir selection will occure")
    print()
    help()


def get_opts(args):
    opts = {
        'help': False,
        'man': False,
        'exact': False,
        'music_dir': '',
    }
    for opt in args[1:]:
        if opt == '-h' or opt == '--help':
            opts['help'] = True
        elif opt == '-m' or opt == '--man':
            opts['man'] = True
        elif opt == '-e' or opt == '--exact':
            opts['exact'] = True
        else:
            opts['music_dir'] = opt
    return opts


def sround(num, scale=0):
    try:
        return round(num, scale)
    except TypeError:
        return 0


class Player(object):
    def __init__(self, music_dir, exact_folder=False):
        if not exact_folder:
            music_dir = self._select_artist(music_dir)
        self._songs = self._find_songs(music_dir)
        random.shuffle(self._songs)
        self._player = mplayer.Player(stderr=subprocess.STDOUT)
        self._changed = False
        self.volume_diff = 5
        self._last_vol = None
        self._cols = self._term_cols()

    def _find_songs(self, dir_):
        supported = ('mp3', 'ogg', 'flv', 'flac')
        songs = []
        dirs = [dir_]
        for dir_ in dirs:
            for sub in os.listdir(dir_):
                pathname = os.path.join(dir_, sub)
                mode = os.stat(pathname)[stat.ST_MODE]
                if stat.S_ISDIR(mode):
                    dirs.append(pathname)
                elif stat.S_ISREG(mode) and pathname.endswith(supported):
                    songs.append(pathname)
        return songs

    def _select_artist(self, dir_):
        subdirs = []
        for sub in os.listdir(dir_):
            pathname = os.path.join(dir_, sub)
            if os.path.isdir(pathname):
                subdirs.append(pathname)
        if not subdirs:
            return ''
        return random.choice(subdirs)

    def play(self):
        self._current = 0
        self._play_song()

    def _play_song(self):
        key_map = {
            '=': (self.volume_up,),
            '+': (self.volume_up,),
            '-': (self.volume_down,),
            'e': (self.jump_end,),
            'n': (self.next_song,),
            'p': (self.prev_song,),
            'i': (self.print_song_info,),
            'q': (self.stop,),
            'P': (self._player.pause,),
            ' ': (self._player.pause,),
            qsio.NonBlockingKeypress.KEY_INT: (self.stop,),
        }
        with qsio.NonBlockingKeypress(key_map) as keybd:
            # whole playlist
            p = self._player
            while self.song:
                p.loadfile(self.song)
                # wait till file is loaded
                while p.paused is None:
                    time.sleep(0.1)
                # restore volume
                if self._last_vol is None:
                    self._last_vol = p.volume
                p.volume = self._last_vol
                # play file
                if p.paused:
                    p.pause()
                # whole song
                while self._playing_sleep():
                    if not keybd.process_keys():
                        self.stop()
                        break
                self._current += 1
                print('\r')

    def _playing_sleep(self):
        if self._changed or self._player.percent_pos is None:
            self._changed = False
            return False
        paused = 'PAUSED' if self._player.paused else ''
        msg_format = "[%d/%d] %s %s%% [%d/%d sec] [vol=%s%%] %s"
        msg_data = (
            self._current + 1,
            len(self._songs),
            self.song,
            self._player.percent_pos,
            sround(self._player.time_pos),
            sround(self._player.length),
            sround(self._player.volume),
            paused)
        print("%s\r" % (msg_format % msg_data).ljust(self._cols - 1),
              end='')
        time.sleep(0.2)
        return True

    @property
    def song(self):
        try:
            return self._songs[self._current]
        except IndexError:
            # out of songs
            return None

    def volume_up(self):
        self._player.volume = min(
            100,
            self._player.volume + self.volume_diff)
        self._last_vol = self._player.volume

    def volume_down(self):
        self._player.volume = max(
            0,
            self._player.volume - self.volume_diff)
        self._last_vol = self._player.volume

    def next_song(self):
        if self._current + 1 == len(self._songs):
            self._current -= 1
        self._finish_song()

    def prev_song(self):
        self._current = max(-1, self._current - 2)
        self._finish_song()

    def stop(self):
        self._current = len(self._songs)
        self._finish_song()

    def jump_end(self):
        try:
            self._player.time_pos = self._player.length - 10
        except TypeError:
            pass  # weird float error in mplayer.py?

    def _finish_song(self):
        try:
            self._player.time_pos = self._player.length
        except TypeError:
            pass  # weird float error in mplayer.py?
        self._changed = True

    def print_song_info(self):
        if self._player.metadata:
            md = self._player.metadata
            print('\r')
            for k, v in md.iteritems():
                print(' %s: %s\r' % (k, v))

    def _term_cols(self):
        (rows, cols) = subprocess.check_output(['stty', 'size']).split()
        return int(cols)


def main():
    opts = get_opts(sys.argv)
    if opts['help']:
        help()
    if opts['man']:
        man()
    music_dir = opts['music_dir']
    if not music_dir:
        music_dir = DEFAULT_COLLECTION
    if not os.path.isdir(music_dir):
        usage(1, "Music directory ({}) doesn't exists!\n".format(music_dir))

    p = Player(
        os.path.abspath(music_dir),
        exact_folder=bool(opts['exact']))
    p.play()


if __name__ == '__main__':
    try:
        main()
    except (OSError, KeyboardInterrupt) as e:
        print("... koncim")
