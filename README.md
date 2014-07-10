UrlObs
======

Url Observer: monitor changes of web pages according to user-defined XPath rules. Written in Perl, use YAML config format. Dead simple.

Require (cpan install):
* LWP::Simple
* HTML::TreeBuilder::XPath
* XML::XPath
* XML::XPath::XMLParser
* YAML::Syck
* Digest::MD5
* Text::Diff

Use:
```sh
perl urlobs.pl example.yaml
```

YAML format is a list of entry where:
* url: is the url
* xpath: XPath rule selecting monitored nodes (text extracted)
* title: used for humans [optional]
* interval: is the minimum fetching interval (seconds) [optional]
* type: whether it is html or xml [missing means html]

The file is modified by the program as a database. Look at example.yml for an example.
