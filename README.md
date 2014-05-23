UrlObs
======

Url Observer (Perl+YAML, detect change)

Require:
* LWP::Simple;
* YAML::Syck;
* Digest::MD5 qw{md5\_hex};
* IPC::Open3;
* Text::Diff;

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
