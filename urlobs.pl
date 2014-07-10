#!/usr/bin/perl
use strict;
use warnings;

use utf8;
use constant VERBOSE => 0;

use LWP::Simple;
use YAML::Syck;
use Digest::MD5 qw{md5_hex};
use Text::Diff;
use HTML::TreeBuilder::XPath;
use XML::XPath;
use XML::XPath::XMLParser;
use Encode qw(encode);

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
    my $old = $info->{content} // "";
    my $freq = $info->{interval} // 0;
    my $ldate = $info->{last} // 0;

    next if ($ldate + $freq > time()); # Skip too fresh
    print "fetching $url\n" if VERBOSE;
    my $page = get($url) or (warn("fetch failed: $url $!") and next);

    my $section, my $render;
    if ($type eq "html") {
        my $tree = HTML::TreeBuilder::XPath->new;
        $tree->parse($page);
        my @xs = $tree->findnodes($xpath);
        $section = join("", map{ $_->as_HTML } @xs);
        $render = join("\n", map{ $_->as_text } @xs);
    }
    elsif ($type eq "xml") {
        my $tree = XML::XPath->new($page);
        my @xs = $tree->findnodes($xpath);
        $section = join("", map{ $_->toString } @xs);
        $render = join("\n", map{ $_->string_value } @xs);
    }
    else {
        warn("unknown type: $type"); next;
    }

    $render =~ s/[ \t\r]\+/ /g;
    $render =~ s/(^[ \t\r]+|[ \t\r]+$)//g;

    print "old: {$old}\n" if VERBOSE;
    print "content: {$section}\n" if VERBOSE;
    print "rendered: {$render}\n" if VERBOSE;

    my $nhash = md5_hex(encode('UTF-8', $render));
    print "hashed $nhash\n" if VERBOSE;

    if (not $hash eq $nhash) {
        my $diffs = diff(\$old, \$render);
        print "Changes for $title:\n$diffs\n";
    }
    else {
        print "no change $nhash\n" if VERBOSE;
    }

    $info->{hash} = $nhash;
    $info->{content} = $render;
    $info->{last} = time();
}

DumpFile($file, $urls);
