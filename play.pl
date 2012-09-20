#!/usr/bin/perl
use strict;
use warnings;
use Pod::Usage;
use Getopt::Long;
use File::Temp qw/ tempfile /;
use Cwd qw/ abs_path /;


# --- default configuration ------
my $player = "mplayer -shuffle -quiet -vo null -playlist";
my $music = "/all/hudba/";

# --- end of def. configuration --

#$SIG{INT} = 'IGNORE'; # ignorujeme ^C - mel by ho zpracovat prehravac (a skoncit == skoncime i my)
# pri pouziti system() toto neni potreba - INT nedostame my ale player

sub find_artist {
	my ($dir) = shift;
	die("Neplatný adresář") if not $dir or not -d $dir;

	opendir(my $d, $dir) || die("selhalo otevreni adresare");
	my @artists = grep { !/^\./ and -d $dir.'/'.$_ } readdir($d);
	closedir($d);

	die("zadne podadresare na vyber") if not @artists;

	return $dir .'/'. @artists[ rand @artists ];
}

sub find_songs {
	my @selected = ();
	my @lookin =  @_;

	foreach my $ld (@lookin) {

		$ld =~ s/\/$//;

		die("Adresar ".$ld." neexistuje!") if not -d $ld;

		opendir(my $d, $ld) || die("selhalo otevreni adresare ".$ld);
		my @content = map { $ld.'/'.$_ } grep { !/^\./ } readdir($d);
		closedir($d);

		push @lookin, grep { -d $_ } @content ;
		push @selected, grep { -f $_ and /(mp3|ogg|flv)$/ } @content ;
	}
	return @selected;
}

sub create_playlist {
	my ($selectedRef) = @_;
	my (@selected) = @$selectedRef;

	my ($ph, $playlist) = tempfile('/tmp/play_XXXXXX', SUFFIX=>'.pls');
	foreach my $song (@selected) { print $ph $song, "\n"; }
	close $ph;

	return $playlist;
}

my $help;
my $man;
my $exact;
GetOptions(
	"help|h|?" => \$help,
	"man|m" => \$man,
	"exact|e" => \$exact
);
pod2usage() if $help;
pod2usage(-verbose => 2) if $man;

my $dir = shift;
if ( not $dir ) {
	$dir = $music;
}
$dir = abs_path($dir);
my $song_dir = $dir;
$song_dir = find_artist($dir) if not $exact;

my @selected = find_songs($song_dir);

die("Nenalezeny zadne songy!") if not @selected;

my $playlist = create_playlist(\@selected);
print $playlist, "\n";
#system("less $playlist");
system("$player $playlist");
unlink ( $playlist ) or die("nelze odstranit ".$playlist);

__END__
=head1 play

Script to play your music collection in random fashion.

=head1 SYNOPSIS

B<play> [-h | -m | music_dir | -e song_dir]

Options:

    -h, --help            brief help message
    -m, --man             full help/description
    -e, --exact song_dir  use song_dir as source of songs
    music_dir             select random subdir from music_dir as source of songs

Without music_dir/exact dir B<play> will use predefined
music directory (see $music at start of source code).

=head1 EXAMPLES

=over 2

=item * play

=item * play /your/music/dir/path

=item * play -e /path/to/songs/directory

=back

=head1 DESCRIPTION

B<play> will select random subdirectory (artist)
of your music_dir. Find recursively all ogg/mp3/flv
files in this (artist) directory and start your
music player with this temporary playlist.

If you want to switch to another music directory (collection)
then simply put path to this dir as first argument of B<play>.

If you want to skip random selection of artist,
and only play all music files (ogg/mp3/flv) in exact directory, then you
can use the B<-e> option and specify this directory.

=head1 AUTHOR

Queria Sa-Tas <queria@sa-tas.net>

=cut

