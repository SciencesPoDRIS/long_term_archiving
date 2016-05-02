## long_term_preservation

Versionning of the sip files for the CINES

Python version needed : 2.5 or after


## Install

Rename the file conf/conf.default.json into conf/conf.json and edit it to put your own SRU/SRW server url
mkvirtualenv long_term_archiving
pip install ftptool
pip install six
pip install lxml
pip install paramiko

## How to use it ?

long_term_preservation can be used with any system compatible with python 2.5 by invoking the command

`python scripts/sip_numpat.py "path/to/folder/to/archive"`


## Credits

[Sciences Po - Bibliothèque](http://www.sciencespo.fr/bibliotheque/)