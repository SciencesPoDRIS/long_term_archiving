# long_term_preservation

Versionning of the sip files for the [CINES](http://www.cines.fr).

Python version needed : 2.5 or after.


## Install

* rename the file conf/conf.default.json into conf/conf.MY_PROJECT.json where MY_PROJECT is the name of my project and edit it to put your own SRU/SRW server url
* `mkvirtualenv long_term_archiving`
* `pip install lxml`
* `pip install paramiko`

## How to use it ?

long_term_preservation can be used with any system compatible with python 2.5 by invoking the command

`python scripts/long_term_archiving.py MY_PROJECT`


## How to create a mapping json file that will build the XML from another XML ?


each method has an attribute "method" that is one of these values : "xpath", "srusrw"
each method has an attribute "paths" that is th paths to access the value. This attibutes is an array and the successive values matches are concatenated
those methods are tested sequentially and the first that match a value is the correct one (the next ones are not executed)



tag	mandatory	description	dataType	example

name	yes	name of the tag created	String	"title"

attributes	no	associated array of the keys / values of attributes of the tag	JSObject of keys / values	{"language" : "fra", "country" : "france"}

access_methods	yes	ordered list that describe the methods to extract data to put as content of the tag	array of JSObject

access_methods > method	yes	protocol to use to extract data	String of ["xpath", "srusrw"]

access_methods > paths	yes	paths to access the value	array of Strings	[".//mods:namePart[@type=\"given\"]", ".//mods:namePart[@type=\"family\"]"]

access_methods > filter	no	filter to apply after that the data are extracted	String of ["concat", "all", "first"]

default_value	no	If nothing match, set default value as content tag	String	"Non renseigné"


## Credits

[Sciences Po - Bibliothèque](http://www.sciencespo.fr/bibliotheque/)

## Licence

This code is produced under the licence LGPL and CECILL-C.

Please feel free to reuse and modify this code.