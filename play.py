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
player = ['mplayer','-shuffle','-quiet','-vo','null','-playlist'];
collection = "/all/hudba/";
# --- end default configuration --

def find_songs(dir):
    supported = ('mp3','ogg','flv')
    songs = []
    dirs = [dir]
    for dir in dirs:
        for sub in os.listdir(dir):
            pathname = os.path.join(dir,sub)
            mode = os.stat(pathname)[ST_MODE]
            if S_ISDIR(mode):
                dirs.append(pathname)
            elif S_ISREG(mode) and pathname.endswith(supported):
                songs.append(pathname)
    return songs

def select_artist(dir):
    subdirs = []
    for sub in os.listdir(dir):
        pathname = os.path.join(dir,sub)
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
    print("play -\tscript to choose subdirectory (artist)\n",
    "\tand play all music files contained (recursively looked up)")
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

f = NamedTemporaryFile(mode='w',dir='/tmp/',prefix='play_',suffix='.pls',delete=False)
print("\n".join(songs),file=f)
cmd = player + [f.name]
f.close()

try:
    call(cmd) #, stdout=PIPE)
except OSError as e:
    print("... koncim")


os.unlink(f.name)

#print("music_dir: {}\n"
#    "selected: {}".format(
#        music_dir,
#        selected))

#my $dir = shift;
#if ( not $dir ) {
#	$dir = $music;
#}
#$dir = abs_path($dir);
#my $song_dir = $dir;
#$song_dir = find_artist($dir) if not $exact;
#
#my @selected = find_songs($song_dir);
#
#die("Nenalezeny zadne songy!") if not @selected;
#
#my $playlist = create_playlist(\@selected);
#print $playlist, "\n";
#system("$player $playlist");
#unlink ( $playlist ) or die("nelze odstranit ".$playlist);
print('hi')
#use strict;
#use warnings;
#use Pod::Usage;
#use Getopt::Long;
#use File::Temp qw/ tempfile /;
#use Cwd qw/ abs_path /;


# --- end of def. configuration --

#sub find_artist {
#	my ($dir) = shift;
#	die("Neplatný adresář") if not -d $dir;
#
#	opendir(my $d, $dir) || die("selhalo otevreni adresare");
#	my @artists = grep { !/^\./ and -d $dir.'/'.$_ } readdir($d);
#	closedir($d);
#
#	die("zadne podadresare na vyber") if not @artists;
#
#	return $dir .'/'. @artists[ rand @artists ];
#}
#
#sub find_songs {
#	my @selected = ();
#	my @lookin =  @_;
#
#	foreach my $ld (@lookin) {
#
#		$ld =~ s/\/$//;
#
#		die("Adresar ".$ld." neexistuje!") if not -d $ld;
#
#		opendir(my $d, $ld) || die("selhalo otevreni adresare ".$ld);
#		my @content = map { $ld.'/'.$_ } grep { !/^\./ } readdir($d);
#		closedir($d);
#
#		push @lookin, grep { -d $_ } @content ;
#		push @selected, grep { -f $_ and /(mp3|ogg|flv)$/ } @content ;
#	}
#	return @selected;
#}
#
#sub create_playlist {
#	my ($selectedRef) = @_;
#	my (@selected) = @$selectedRef;
#
#	my ($ph, $playlist) = tempfile('/tmp/play_XXXXXX', SUFFIX=>'.pls');
#	foreach my $song (@selected) { print $ph $song, "\n"; }
#	close $ph;
#
#	return $playlist;
#}
#
#my $help;
#my $man;
#my $exact;
#GetOptions(
#	"help|h|?" => \$help,
#	"man|m" => \$man,
#	"exact|e" => \$exact
#);
#pod2usage() if $help;
#pod2usage(-verbose => 2) if $man;
#
#my $dir = shift;
#if ( not $dir ) {
#	$dir = $music;
#}
#$dir = abs_path($dir);
#my $song_dir = $dir;
#$song_dir = find_artist($dir) if not $exact;
#
#my @selected = find_songs($song_dir);
#
#die("Nenalezeny zadne songy!") if not @selected;
#
#my $playlist = create_playlist(\@selected);
#print $playlist, "\n";
#system("$player $playlist");
#unlink ( $playlist ) or die("nelze odstranit ".$playlist);

#__END__
#=head1 play
#
#Script to play your music collection in random fashion.
#
#=head1 SYNOPSIS
#
#B<play> [-h | -m | music_dir | -e song_dir]
#
#Options:
#
#    -h, --help            brief help message
#    -m, --man             full help/description
#    -e, --exact song_dir  use song_dir as source of songs
#    music_dir             select random subdir from music_dir as source of songs
#
#Without music_dir/exact dir B<play> will use predefined
#music directory (/all/hudba).
#
#=head1 EXAMPLES
#
#=over 2
#
#=item * play
#
#=item * play /your/music/dir/path
#
#=item * play -e /path/to/songs/directory
#
#=back
#
#=head1 DESCRIPTION
#
#B<play> will select random subdirectory (artist)
#of your music_dir. Find recursively all ogg/mp3/flv
#files in this (artist) directory and start your
#music player with this temporary playlist.
#
#If you want to switch to another music directory (collection)
#then simply put path to this dir as first argument of B<play>.
#
#If you want to skip random selection of artist,
#and only play all music files (ogg/mp3/flv) in exact directory, then you
#can use the B<-e> option and specify this directory.
#
#=head1 AUTHOR
#
#Queria Sa-Tas <queria@sa-tas.net>
#
#=cut
#
