#!/usr/bin/perl
use strict;
use warnings;

use LWP::Simple;
use YAML::Syck;
use Digest::MD5 qw{md5_hex};
use IPC::Open3;

my $file = 'url.yaml';
my $urls = LoadFile($file);

foreach (@$urls) {
    my $info = $_;
    my $url = $info->{url};
    my $start = $info->{start};
    my $stop = $info->{stop};
    my $hash = $info->{hash} // "";
    my $old = $info->{section} // "";
    print "fetch $url\n";

    my $page = get($url);
    my $section;

    foreach (split /\n/, $page) {
        if (defined $start) {
            undef $start if m{$start};
            next;
        }
        if (defined $stop and m{$stop}) {
            last;
        }
        $section .= "$_\n";
    }

    unless ($hash) {
        print "\tpage was never scraped\n";
    }

    my $nhash = md5_hex($section);
    if (not $hash eq $nhash) {
        local $/;
        my $cmd = 'elinks -force-html -no-references -no-numbering -dump';
        my $pid = open3(my $cin, my $cout, my $cerr, $cmd)
            or die("open3 failed: rendering failed: $!");
        print $cin $section;
        close($cin);
        waitpid($pid, 0);
        my $render = <$cout>;

        $info->{hash} = md5_hex($render);
        $info->{section} = $render;
        print "Page changed:\n$render\n";
    }
}

DumpFile($file, $urls);
