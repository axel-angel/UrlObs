#!/usr/bin/perl
use strict;
use warnings;

use utf8;
use constant VERBOSE => 0;


use LWP::Simple;
use YAML::Syck;
use Digest::MD5 qw{md5_hex};
use Algorithm::Diff qw{diff};
use HTML::TreeBuilder::XPath;
use XML::XPath;
use XML::XPath::XMLParser;
use Encode qw(encode);
use List::Util qw{first};


sub process_content {
    my ($text) = @_;
    $text = encode('UTF-8', $text);
    $text =~ s/[ \t\r]\+/ /g;
    return $text;
}


sub mydiff {
    my ($a, $b) = @_;

    my @rep;
    my @diffs = diff($a, $b);
    for my $l (@diffs) {
        for my $m (@$l) {
            push(@rep, $m->[0] ." ". $m->[2]);
        }
    }

    return join("\n", @rep);
}


my $file = $ARGV[0] // "url.yaml";
die("$file: $!") unless -e $file;
my $urls = LoadFile($file);

foreach (@$urls) {
    my $info = $_;
    my $url = $info->{url};
    my $xpath = $info->{xpath};
    my $type = $info->{type} // "html";
    my $title = $info->{title} // $url;
    my $hash = $info->{hash} // "";
    my @old = @{$info->{content} // []};
    my $freq = $info->{interval} // 0;
    my $ldate = $info->{last} // 0;
    my $keepold = $info->{keep_old} // 0;
    my $noorder = $info->{no_order} // $keepold;

    next if ($ldate + $freq > time()); # Skip too fresh
    print "fetching $url\n" if VERBOSE;
    my $page = get($url) or (warn("fetch failed: $url $!") and next);

    my @render;
    if ($type eq "html") {
        my $tree = HTML::TreeBuilder::XPath->new;
        $tree->parse($page);
        my @xs = $tree->findnodes($xpath);
        @render = map{ $_->as_text } @xs;
    }
    elsif ($type eq "xml") {
        my $tree = XML::XPath->new($page);
        my @xs = $tree->findnodes($xpath);
        @render = map{ $_->string_value } @xs;
    }
    else {
        warn("unknown type: $type"); next;
    }

    if ($noorder) {
        @render  = sort @render;
    }

    if ($keepold) {
        foreach my $el (@old) {
            push(@render, $el) unless first{$_ eq $el} @render;
        }
    }

    @render = map{ process_content($_) } @render;

    print "old: {@old}\n" if VERBOSE;
    print "rendered: {@render}\n" if VERBOSE;

    my $nhash = md5_hex(join('', @render));
    print "hashed $nhash\n" if VERBOSE;

    if (not $hash eq $nhash) {
        my @diffs = mydiff(\@old, \@render);
        print "Changes for $title:\n". join("\n", @diffs) ."\n";
    }
    else {
        print "no change $nhash\n" if VERBOSE;
    }

    $info->{hash} = $nhash;
    $info->{content} = \@render;
    $info->{last} = time();
}

DumpFile($file, $urls);
