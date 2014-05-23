UrlObs
======

Url Observer: fetch the URLs in the configuration and print the changes. Written in Perl, use YAML config format. Dead simple.

Require (cpan install):
* LWP::Simple
* YAML::Syck
* Digest::MD5
* IPC::Open3
* Text::Diff

Use:
```sh
perl urlobs.pl example.yaml
```

YAML format is a list of entry where:
* url: is the url
* title: used for humans [optional]
* interval: is the minimum fetching interval (seconds) [optional]
* start: ignore everything before this Perl-regex [optional]
* stop: ignore everything after this Perl-regex [optional]

The file is modified by the program as a database
