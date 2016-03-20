#!/usr/bin/perl
use strict;
use warnings;

use utf8;
use constant VERBOSE => 0;
binmode STDOUT, ":encoding(UTF-8)";
binmode STDERR, ":encoding(UTF-8)";

use LWP::UserAgent;
use YAML::Syck;
use Digest::MD5 qw{md5_hex};
use Text::Diff;
use HTML::TreeBuilder::XPath;
use XML::XPath;
use XML::XPath::XMLParser;
use Encode qw(encode decode);
use List::Util qw{first min};


sub process_content {
    my ($text) = @_;
    $text =~ s/[ \t\r]\+/ /g;
    return $text;
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
    my @old = map{ decode('UTF-8', $_) } @{$info->{content} // []};
    my $freq = $info->{interval} // 0;
    my $ldate = $info->{last} // 0;
    my $keepold = $info->{keep_old} // 0;
    my $noorder = $info->{no_order} // $keepold;
    my $onlydiffs = $info->{onlydiffs} // 1;
    my $failures = $info->{failures} // 0;
    my $useragent = $info->{user_agent};
    my $cookie = $info->{cookie};
    my $min_alert_failures = $info->{min_failure_alert} // 5;

    my @headers = ();
    push @headers, ("Cookie" => $cookie) if $cookie;

    $freq = $freq * 2 ** min($min_alert_failures, $failures);
    next if ($ldate + $freq > time()); # Skip too fresh

    print "fetching $url\n" if VERBOSE;
    my $ua = LWP::UserAgent->new();
    $ua->agent($useragent) if defined $useragent;
    my $res = $ua->get($url, @headers);
    $info->{last} = time();
    unless ($res->is_success) {
        if ($info->{failures} >= $min_alert_failures) {
            warn("〉✗ Fetch failed for $title (freq: $freq):");
            warn("  HTTP: ". $res->status_line ."\n\n");
        }
        ++$info->{failures};
        next;
    }
    my $page = $res->decoded_content;

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
        warn("〉✗ Unknown type for $title\n"); next;
    }

    if ($keepold) {
        foreach my $el (@old) {
            push(@render, $el) unless first{$_ eq $el} @render;
        }
    }

    if ($noorder) {
        @render  = sort @render;
    }

    @render = map{ process_content($_) } @render;

    print "old: {@old}\n" if VERBOSE;
    print "rendered: {@render}\n" if VERBOSE;

    my $nhash = md5_hex(encode('UTF-8', join('', @render)));
    print "hashed $nhash\n" if VERBOSE;

    if (not $hash eq $nhash) {
        my @diffs = ();
        if ($onlydiffs) {
            my %a = map { $_ => 1 } @old;
            my %b = map { $_ => 1 } @render;
            push(@diffs, "++ New:");
            foreach (keys %b) {
                push(@diffs, "  ". $_) unless defined $a{$_};
            }
            push(@diffs, "-- Off:");
            foreach (keys %a) {
                push(@diffs, "  ". $_) unless defined $b{$_};
            }
        }
        else {
            diff(\@old, \@render, {OUTPUT => \@diffs});
        }
        print "〉 Changes for $title:\n";
        print "$_\n" foreach @diffs;
        print "\n";
    }
    else {
        print "no change $nhash\n" if VERBOSE;
    }

    $info->{hash} = $nhash;
    $info->{content} = \@render;
    $info->{failures} = 0;
}

DumpFile($file, $urls);
