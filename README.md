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
* title: used for humans
* url: is the url
* interval: is the minimum fetching interval (seconds)
* start: ignore everything before this Perl-regex
* stop: ignore everything after this Perl-regex
The file is modified by the program as a database
