UrlObs
======

Url Observer: monitor changes of web pages according to user-defined XPath rules. Written in Perl, use YAML config format. Dead simple.

Require (cpan install):
* LWP::UserAgent
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
* no_order: whether we do a sorting (effectively ignoring the output ordering)
* keep_old: whether we should ignore deletions by keeping old entries (useful for youtube RSS, they blink). This option forces no_order by default.
* user_agent: Specify the browser signature, useful to circumvent certain useless site protections [optional].

The file is modified by the program as a database. Look at example.yml for an example.
