#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set et sw=4 ts=4 ft=python:
"""play.py [-h|--help] [-m|--man] [-n|--notags]
 [-s|--sorted] [-e|--exact] [music-dir]"""
from __future__ import print_function, unicode_literals
import mplayer
import os
import pprint
import random
import stat
import subprocess
import sys
import time
import mutagen

import qsio

# --- default configuration ------
DEFAULT_COLLECTION = "/all/music/"
# --- end default configuration --


def usage(code, msg=''):
    if msg:
        print("** Error: ", msg)
    print(__doc__)
    # print(__doc__ % globals())
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
    print("[sorted]\tdisables random shuffling,\n",
          "\tso songs are always played in the same alphab. sorted order")
    print()
    help()


def get_opts(args):
    opts = {
        'help': False,
        'man': False,
        'exact': False,
        'music_dir': '',
        'sorted': False,
        'notags': False,
    }
    for opt in args[1:]:
        if opt == '-h' or opt == '--help':
            opts['help'] = True
        elif opt == '-m' or opt == '--man':
            opts['man'] = True
        elif opt == '-e' or opt == '--exact':
            opts['exact'] = True
        elif opt == '-s' or opt == '--sorted':
            opts['sorted'] = True
        elif opt == '-n' or opt == '--notags':
            opts['notags'] = True
        else:
            opts['music_dir'] = opt
    return opts


def sround(num, scale=0):
    try:
        return round(num, scale)
    except TypeError:
        return 0


def un(string):
    return string.decode('utf-8', 'ignore')


class SongInfo(object):
    def __init__(self, songpath, use_tags=True):
        self.path = songpath
        self.filename = os.path.basename(songpath)
        self.title = ''
        self.artist = ''
        self.album = ''
        self.length = None
        self.bitrate = None

        self._length_perc = 0

        if songpath:
            self._extract_info(songpath, use_tags)
        else:
            self._text = '- not found -'
            return

        extra = []
        if self.length:
            # l = u'%ds' % round(self.length)
            # extra.append(l)
            self._length_perc = self.length/100.0
        if self.bitrate:
            bt = self.bitrate
            bt = u'%dkbps' % (bt / 1000)
            extra.append(bt)
        extra_str = (', '.join(extra)) if extra else ''

        if not use_tags or not self.title:
            self._text = ('%s [%s]' % (
                self.filename,
                extra_str))
        else:
            self._text = ('%s - %s - %s [%s]' % (
                self.artist,
                self.album,
                self.title,
                extra_str))
        try:
            self._text_for_search = '%s %s' % (
                self.path.lower(),
                self._text.lower())
        except UnicodeDecodeError:
            print('Unable to process %s' % self.path)
            print('text %s' % self._text.lower())
            raise

    def __str__(self):
        return self._text

    def has_substr(self, substr):
        return substr in self._text_for_search

    def percent_pos(self, time_pos, raw=False):
        if time_pos is None:
            return '100'
        p = time_pos / self._length_perc
        if raw:
            return p
        return str(int(round(p)))

    def _extract_info(self, songpath, use_tags=True):
        song = mutagen.File(songpath, easy=True)
        if use_tags and getattr(song, 'tags', None):
            self.title = self._extract_field(
                song, ('title', 'TITLE'))
            self.artist = self._extract_field(
                song, ('artist', 'ARTIST'))
            self.album = self._extract_field(
                song, ('album', 'ALBUM', 'ALBUMTITLE'))
        if getattr(song, 'info', None):
            self.length = getattr(song.info, 'length', None)
            self.bitrate = getattr(song.info, 'bitrate', None)

    def _extract_field(self, song, field_names, default=''):
        if song.tags is None:
            return default
        for name in field_names:
            default = song.tags.get(name, default)
            if default:
                if isinstance(default, list):
                    return default[0]
                return default


class Player(object):
    def __init__(self, music_dir, exact_folder=False, shuffle=True,
                 show_tags=True):
        self._no_song = SongInfo('')
        self._player = mplayer.Player(args=('-novideo',),
                                      stderr=subprocess.STDOUT)
        self.music_dir = music_dir
        self.exact_folder = exact_folder
        self.shuffle = shuffle
        self.show_tags = show_tags
        self.volume_diff = 5
        self._last_vol = None
        self._cols = self._term_cols()
        self._songs = []

        self._pick_playlist()

    def _pick_playlist(self):
        self._changed = False
        self._last_info = None
        self._searching = None
        self._search_hit = self._no_song
        self._search_changed = False

        picked_music_dir = self.music_dir
        if not self.exact_folder:
            picked_music_dir = self._select_artist(picked_music_dir)
        print('\rSelected directory: %s' % picked_music_dir)

        self._songs = self._load_songs(
            self._find_songs(picked_music_dir))

        print('\rTotal %d songs' % len(self._songs))

        if self.shuffle:
            random.shuffle(self._songs)
            print('\rShuffled song list.')
        else:
            self._songs = sorted(self._songs)

    def repick_playlist(self):
        print('')
        print('\r')
        self._pick_playlist()
        self._current = -1
        self._finish_song()

    def _find_songs(self, dir_):
        supported = ('mp3', 'ogg', 'flv', 'flac', 'webm', 'mp4')
        songs = []
        dirs = [dir_]
        # print('searching for songs: 0')
        for dir_ in dirs:
            for sub in os.listdir(dir_):
                pathname = os.path.join(dir_, sub.decode('utf-8', 'ignore'))
                mode = os.stat(pathname)[stat.ST_MODE]
                if stat.S_ISDIR(mode):
                    dirs.append(pathname)
                elif stat.S_ISREG(mode) and pathname.endswith(supported):
                    songs.append(pathname)
                print('\rfindings songs: {dirs} dirs, {files} files        '
                      .format(dirs=len(dirs), files=len(songs)),
                      end='')
        print('')
        return songs

    def _load_songs(self, song_files):
        songs = []
        total = len(song_files)
        for song_file in song_files:
            songs.append(SongInfo(song_file, self.show_tags))
            print('\rloading songs: {cur}/{total}'
                  .format(cur=len(songs), total=total),
                  end='')
        print('')
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
            '<': (self.jump_back5,),
            '>': (self.jump_fwd5,),
            'e': (self.jump_end,),
            'n': (self.next_song,),
            'p': (self.prev_song,),
            'i': (self.print_song_info,),
            'q': (self.stop,),
            'r': (self.reset_term,),
            'P': (self._player.pause,),
            ' ': (self._player.pause,),
            'l': (self.list_songs,),
            '~': (self.repick_playlist,),
            qsio.NonBlockingKeypress.KEY_INT: (self.stop,),
        }
        with qsio.NonBlockingKeypress(key_map) as keybd:
            keybd.reg_key('/', self._start_search, pass_backref=True)
            keybd.reg_key('h', lambda: self._show_keybindings(keybd))

            # whole playlist
            p = self._player
            while self.song and self.song.path:
                print("%s\r" % (self.song), end='')
                # FIXME(queria|later): ^^ what should be fixed here?
                p.loadfile(self.song.path)
                # wait till file is loaded
                while p.paused is None:
                    time.sleep(0.1)
                _ = p.length  # noqa
                # restore volume
                if self._last_vol is None:
                    self._last_vol = p.volume
                p.volume = self._last_vol
                # play file
                if p.paused:
                    p.pause()
                self._report_nowplaying()
                # whole song
                while self._playing_sleep():
                    if not keybd.process_keys():
                        self.stop()
                        break
                self._current += 1
                print('\r')
        self._clean_nowplaying()

    def _playing_sleep(self):
        if self._player.paused:
            time.sleep(0.4)
        else:
            time.sleep(0.1)
        if self._searching is not None:
            if self._search_changed:
                search_msg = 'search: %s  => %s (%s)' % (
                    self._searching,
                    self._search_hit.path,
                    self._search_hit)
                search_msg = search_msg.ljust(self._cols - 1)
                # self._search_changed = False
                # FIXME(queria): update has to be done twice
                # doing just one print() is for some reason
                # (not clear to me now) not enough, and screen
                # updated is delayed by one key press
                # - on "first" look it's not related to
                #   qsio/playing_sleep loop
                #   more like to stdout/console update
                # - adding print('x') before this print
                #   does not helped!
                print('%s\r' % search_msg, end='')
            return True
        if self._changed or self._player.percent_pos is None:
            self._changed = False
            return False
        paused = 'PAUSED' if self._player.paused else ''
        msg_format = "[%d/%d] %s %s%% %s"
        try:
            msg_data = (
                self._current + 1,
                len(self._songs),
                unicode(self.song),
                self.song.percent_pos(self._player.time_pos),
                paused)
        except UnicodeEncodeError as exc:
            msg_data = (
                self._current + 1,
                len(self._songs),
                str(exc),
                self.song.percent_pos(self._player.time_pos),
                paused)
        msg = msg_format % msg_data
        vol = '[vol=%s%%]' % sround(self._player.volume)

        msg_max_len = self._cols - len(vol) - 1
        if len(msg) > msg_max_len:
            msg = msg[:msg_max_len]
        print("%s%s\r" % (msg.ljust(msg_max_len), vol), end='')
        return True

    def _start_search(self, keybd):
        print('\n')
        self._searching = ''
        keybd.passthrough(self._update_search)
        self._search_changed = True

    def _update_search(self, keybd, char):
        if char is None:
            return
        if ord(char) == 13:  # enter
            wanted = self._search_hit
            self._stop_search(keybd)
            self.jump_to_name(wanted.path, move_in_queue=True)
        elif ord(char) == 27:  # escape
            self._stop_search(keybd)
        else:
            self._search_changed = True
            if ord(char) == 127:  # backspace
                self._searching = self._searching[:-1]
            else:
                self._searching += char
            self._searching = self._searching.lower()
            self._search_hit = self._no_song
            for song in self._songs:
                if song.has_substr(self._searching):
                    self._search_hit = song
                    break

    def _stop_search(self, keybd):
        self._search_changed = True
        self._searching = None
        self._search_hit = self._no_song
        keybd.passthrough(None)

    def _show_keybindings(self, keybd):
        print('\r')
        keymap = keybd.dump_keymap()
        for key, actions in keymap.iteritems():
            actions_strs = []
            for action in actions:
                # actions_strs.append(str(dir(action['callback'])))
                if not hasattr(action['callback'], 'im_func'):
                    # type(action['callback']) != 'instancemethod':
                    continue
                actions_strs.append('%s' % (
                    # action['callback'].im_class.__name__,
                    action['callback'].im_func.__name__,
                ))

            print('\r "%s" => %s' % (
                key,
                ', '.join(actions_strs)
            ))
        print('\r')

    @property
    def song(self):
        try:
            return self._songs[self._current]
        except IndexError:
            # out of songs
            return None

    @property
    def songinfo(self, i_know_this_is_deprecated=False):
        if not i_know_this_is_deprecated:
            print('songinfo is deprecated, use just song now'
                  ' or pass i_know_this_is_deprecated=True')
        info = self.song
        if not info:
            return self._no_song
        return info

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

    def jump_to(self, index, move_in_queue=False):
        if index < 0 or index >= len(self._songs):
            print('invalid index')
            return False
        if move_in_queue:
            # move the 'index' song
            # just behing current one
            self._songs.insert(
                self._current + 1,
                self._songs.pop(index))
        else:
            # just jump to position
            # before 'index' song
            self._current = index - 1
        # as finish_song will move one next after current
        self._finish_song()
        return True

    def jump_to_name(self, song_name, move_in_queue=False):
        if not song_name:
            return False
        for idx, song in enumerate(self._songs):
            if song_name == song.path:
                return self.jump_to(idx, move_in_queue)
        return False

    def jump_end(self):
        try:
            self._player.time_pos = self._player.length - 10
        except TypeError:
            pass  # weird float error in mplayer.py?

    def jump_time(self, steptime=0, stepcount=1):
        try:
            while stepcount > 0:
                self._player.time_pos = max(
                    0.0, self._player.time_pos + steptime)
                stepcount -= 1
        except TypeError as exc:
            print('Ouch: %s', exc)

    def jump_fwd5(self):
        self.jump_time(steptime=5, stepcount=1)

    def jump_back5(self):
        self.jump_time(steptime=-5, stepcount=1)

    def reset_term(self):
        self._cols = self._term_cols()

    def _finish_song(self):
        try:
            self._player.time_pos = self._player.length
        except TypeError:
            pass  # weird float error in mplayer.py?
        self._changed = True

    def print_song_info(self):
        print('\r')
        if self._player.metadata:
            md = self._player.metadata
            for k, v in md.iteritems():
                print(' %s: %s\r' % (k, v))
        if self._player.length is not None:
            print(' length: %s\r' % self.song.length)
            print(' length_perc: %s\r' % self.song.percent_pos(1, raw=True))
            print(' current_pos: %s\r' % self._player.time_pos)
        print('file: %s\r' % self.song.path)

    def list_songs(self, printout=True):
        if not printout:
            return self._songs
        print('')
        print('\n\r'.join([
            ('%s (%s)%s' % (
                s.path,
                s,
                ' <================' if s == self.song else ''
            ))
            for s in self._songs]))
        print('\n\r', end='')

    def _term_cols(self):
        (rows, cols) = subprocess.check_output(['stty', 'size']).split()
        return int(cols)

    def _report_nowplaying(self):
        with open(os.path.expanduser('~/.nowplaying'), 'w') as np_file:
            np_file.write(unicode(self.song).encode('utf-8'))

    def _clean_nowplaying(self):
        os.remove(os.path.expanduser('~/.nowplaying'))


def main():
    reload(sys)
    sys.setdefaultencoding('utf-8')
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
        exact_folder=bool(opts['exact']),
        shuffle=(not bool(opts['sorted'])),
        show_tags=(not bool(opts['notags'])),
    )
    p.play()


if __name__ == '__main__':
    try:
        main()
    except (OSError, KeyboardInterrupt) as e:
        print("... koncim")
