#!/usr/bin/perl
use strict;
use warnings;

use LWP::Simple;

my $p = get('http://www.fimfiction.net/story/149184/shadows-of-the-crystal-empire');
print($p);
