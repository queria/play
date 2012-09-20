#!/bin/bash

# --- configuration: -------------
PLAYER="mplayer -shuffle -msglevel all=-1:demux=4:statusline=5 -playlist -vo null"
MUSIC_DIR="/all/hudba/"

# --- end of configuration -------

PLAYLIST=$(mktemp "/tmp/play_XXXXXX.pls")

if [ -d "${1}" ];
then
	SELECTED=$(readlink -f "${1}")
else
	SELECTED=$(find /all/hudba/ -maxdepth 1 -type d|grep -v "/all/hudba/$"|sort -R|head -n 1)
fi

find "${SELECTED}" -iname "*.ogg" -o -iname "*.mp3" -printf "%p\\n" >> ${PLAYLIST}
echo "**** Playlist ${PLAYLIST} created with $(wc -l ${PLAYLIST}) songs"
${PLAYER} "${PLAYLIST}"
rm "${PLAYLIST}"
echo "**** Playlist ${PLAYLIST} removed"

# |-print0 |xargs --null --no-run-if-empty ${PLAYER}
#${PLAYER} $LIST
#${PLAYER} $(find "${SELECTED}" -iname "*.ogg" -o -iname "*.mp3")

