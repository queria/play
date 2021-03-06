#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""play.py [-h|--help] [-m|--man] [-e|--exact] [music-dir]"""
import os
import sys
from random import choice
from stat import *
from tempfile import NamedTemporaryFile
from subprocess import call, PIPE


# --- default configuration ------
#player = "mplayer -shuffle -quiet -vo null -playlist";
player = ['mplayer', '-shuffle',
          '-msglevel', 'all=-1:demux=4:statusline=5',
          '-vo', 'null', '-playlist']
collection = "/all/hudba/"
# --- end default configuration --


def find_songs(dir_):
    supported = ('mp3', 'ogg', 'flv', 'flac')
    songs = []
    dirs = [dir_]
    for dir_ in dirs:
        for sub in os.listdir(dir_):
            pathname = os.path.join(dir_, sub)
            mode = os.stat(pathname)[ST_MODE]
            if S_ISDIR(mode):
                dirs.append(pathname)
            elif S_ISREG(mode) and pathname.endswith(supported):
                songs.append(pathname)
    return songs


def select_artist(dir_):
    subdirs = []
    for sub in os.listdir(dir_):
        pathname = os.path.join(dir_, sub)
        if os.path.isdir(pathname):
            subdirs.append(pathname)
    if not subdirs:
        return ''
    return choice(subdirs)


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


opt_help = False
opt_man = False
opt_exact = False
music_dir = ''
for opt in sys.argv[1:]:
    if opt == '-h' or opt == '--help':
        opt_help = True
    elif opt == '-m' or opt == '--man':
        opt_man = True
    elif opt == '-e' or opt == '--exact':
        opt_exact = True
    else:
        music_dir = opt
if opt_help:
    help()
if opt_man:
    man()

if not music_dir:
    music_dir = collection

if not os.path.isdir(music_dir):
    usage(1, "Music directory ({}) doesn't exists!\n".format(music_dir))

music_dir = os.path.abspath(music_dir)
selected = music_dir

if not opt_exact:
    selected = select_artist(music_dir)

songs = find_songs(selected)

file_ = NamedTemporaryFile(
    mode='w', dir='/tmp/',
    prefix='play_', suffix='.pls',
    delete=False)
print("\n".join(songs), file=file_)
cmd = player + [file_.name]
file_.close()

try:
    call(cmd)
except (OSError, KeyboardInterrupt) as e:
    print("... koncim")


os.unlink(file_.name)
