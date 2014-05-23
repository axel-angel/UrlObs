#!/usr/bin/perl
use strict;
use warnings;

use LWP::Simple;
use YAML::Syck;
use Digest::MD5 qw{md5_hex};
use IPC::Open3;
use Text::Diff;

my $file = $ARGV[0] // "url.yaml";
my $urls = LoadFile($file);

sub html_render {
    my ($html) = @_;
    my $cmd = 'elinks -force-html -no-references -no-numbering -dump';
    my $pid = open3(my $cin, my $cout, my $cerr, $cmd)
        or die("open3 failed: rendering failed: $!");
    print $cin $html;
    close($cin);
    waitpid($pid, 0);

    local $/;
    return <$cout>;
}

foreach (@$urls) {
    my $info = $_;
    my $url = $info->{url};
    my $title = $info->{title} // $url;
    my $start = $info->{start};
    my $stop = $info->{stop};
    my $hash = $info->{hash} // "";
    my $old = $info->{content} // "";
    my $freq = $info->{interval} // 0;
    my $ldate = $info->{last} // 0;

    next if ($ldate + $freq > time()); # Skip too fresh
    my $page = get($url) or die("fetch failed: $!");

    my $section;
    foreach (split /\n/, $page) {
        if (defined $start) {
            undef $start if m{$start};
            next;
        }
        elsif (defined $stop and m{$stop}) {
            last;
        }
        $section .= "$_\n";
    }

    my $render = html_render($section);
    my $nhash = md5_hex($render);

    if (not $hash eq $nhash) {
        my $diffs = diff(\$old, \$render);
        print "Changes for $title:\n$diffs\n";
    }

    $info->{hash} = $nhash;
    $info->{section} = $render;
    $info->{last} = time();
}

DumpFile($file, $urls);