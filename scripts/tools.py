#!/usr/bin/python
# -*- coding: utf-8 -*-
# Execution example : python scripts/tools.py


#
# Libs
#

import hashlib
import json
import logging
from lxml import etree
import os
import re
import sys
import urllib
import urllib2


#
# Config
#

folder_separator = '/'
scripts_folder = 'scripts'
download_folder = 'download'
conf_folder = 'conf'
conf_file = os.path.join(conf_folder, 'conf.json')

# Namespaces
xsi = 'http://www.w3.org/2001/XMLSchema-instance'
xsi_schemalocation = 'http://www.cines.fr/pac/sip http://www.cines.fr/pac/sip.xsd'
nsmap = {
	None : 'http://www.cines.fr/pac/sip',
	'xsi' : xsi
}
ns = {
	'mods' : 'http://www.loc.gov/mods/v3',
	'mets' : 'http://www.loc.gov/METS/',
	'xlink' : 'http://www.w3.org/1999/xlink'
}
ns_marc = {
	'ns0' : 'http://docs.oasis-open.org/ns/search-ws/sruResponse',
	'ns1' : 'http://www.loc.gov/MARC21/slim'
}
# Constants
type = {
	'book' : 'Monographie'
}
format = {
	'jp2' : 'JPEG2000',
	'xml' : 'XML'
}


#
# Functions
#

# Write SIP results into result file
def write_xml_file(file_path, data) :
	tree = etree.ElementTree(data)
	tree.write(file_path, encoding='UTF-8', pretty_print=True, xml_declaration=True)

def get_title() :
	title = ''
	if len(tree.xpath('.//mods:nonSort', namespaces = ns)) > 0 :
		title += tree.find('.//mods:nonSort', ns).text
	title += tree.find('.//mods:title', ns).text
	return title

def type_filter(values) :
	return [type[str(values[0].text)]]

def concat_filter(values) :
	return [' '.join(str(value.text) for value in values)]

def first_filter(values) :
	return [values[0].text]

def all_filter(values) :
	return [value.text for value in values]

def filename_filter(values) :
	return [values[0].replace('file://', '').replace('ocr/', 'master/')]

def md5_filter(values) :
	# For a file, download it and return the MD5 checksum
	image_url = 'http://' + conf['ftp_server'] + conf['remote_path'] + '_'.join(values[0].split(folder_separator)[-1].split('_')[0:3]) + folder_separator + 'master' + folder_separator + values[0].split(folder_separator)[-1]
	image_path = values[0].replace('file://master/', conf['local_path'] + folder_separator + download_folder + folder_separator).replace('file://ocr/', conf['local_path'] + folder_separator + download_folder + folder_separator)
	if download_image(image_url, image_path) :
		return [md5(image_path)]

def md5xml_filter(values) :
	image_url = 'http://' + conf['ftp_server'] + conf['remote_path'] + values[0].text + folder_separator + values[0].text + '.xml'
	image_path = conf['local_path'] + folder_separator + download_folder + folder_separator + values[0].text + '.xml'
	if download_image(image_url, image_path) :
		return [md5(image_path)]

def format_filter(values) :
	return [format[values[0].split('.')[-1]]]

def get_mets_file_filter(values) :
	return ['DESC/' + values[0].text + '.xml']

# Download an image from its image_url if it exists into the image_path
def download_image(image_url, image_path) :
	try :
		req = urllib2.Request(image_url)
		response = urllib2.urlopen(req)
		urllib.urlretrieve(image_url, image_path)
		return True
	except Exception, e :
		logging.error('Image url does\'nt exist : ' + image_url)
		return False

# Calculate the MD5 checksum for the file fname
def md5(fname) :
	logging.info('Calculate the MD5 checksum for the file : ' + fname)
	hash = hashlib.md5()
	with open(fname, 'rb') as f :
		for chunk in iter(lambda: f.read(4096), b""):
			hash.update(chunk)
	return hash.hexdigest()

# Build the node value according to node's parameters and return it
def get_node_values(node, element) :
	values = []
	contents = []
	for access_method in node['value'] :
		# If values is empty, pass through next access method
		# Implement logic for xpath
		if len(values) == 0 and access_method['method'] == 'xpath' :
			# Set filter logic for this method
			filter = access_method['filter']
			# Iterate over xpaths
			for xpath in access_method['paths'] :
				# Extract values
				lalilou = tree if element is None else element
				if len(lalilou.xpath(xpath, namespaces = ns)) > 0 :
					values += lalilou.xpath(xpath, namespaces = ns)
		# Implement logic for the SRU/SRW protocol
		elif len(values) == 0 and access_method['method'] == 'srusrw' and records_count > 0 :
			# Set filter logic for this method
			filter = access_method['filter']
			for xpath in access_method['paths'] :
				values += [tree_marc.find(xpath, ns_marc)]
	# Implement the filter logic
	# TODO : check that this function exists
	if len(values) > 0 :
		contents = eval(filter + '_filter(values)')
	return contents

# Build the node (name, value, children...) and add it to the tree
def create_node(node_parent, node, element = None) :
	node_name = node['name']
	node_attributes = node['attributes'] if 'attributes' in node else {}
	# if node has children, create them
	if 'repeat' in node :
		repeats = tree.xpath(node['repeat'], namespaces = ns)
		# Delete the repeat attribute
		del node['repeat']
		for repeat in repeats :
			# Recall the function to create the node
			create_node(node_parent, node, repeat)
	elif 'children' in node :
		node_children = node['children']
		new_node = etree.SubElement(node_parent, node_name, node_attributes)
		for node_child in node_children :
			create_node(new_node, node_child, element)
	# else get the node values and create as many nodes as return by the get_node_values function
	elif 'value' in node :
		values = get_node_values(node, element)
		for value in values :
			new_node = etree.SubElement(node_parent, node_name, node_attributes).text = value
	elif 'default_value' in node and (not 'value' in node or ('value' in node and len(values) == 0)) :
		new_node = etree.SubElement(node_parent, node_name, node_attributes).text = node['default_value']
	else :
		logging.error('This node has to have either a \'children\', a \'value\' or a \'default_value\' attribute : ' + node['name'])

def xml2xml(input_file, output_file, json_file, conf_json) :
	global conf
	conf = conf_json
	# Load input_file
	global tree
	tree = etree.parse(input_file).getroot()
	data = etree.Element('pac', nsmap=nsmap, attrib={'{' + xsi + '}schemaLocation' : xsi_schemalocation})
	# Load meta_json file
	with open(json_file) as json_f :
		meta_json = json.load(json_f)
	# Load catalog via protocol SRU/SRW
	url_title = urllib.quote(re.sub(r'([^\s\w\'-]|_)+', '', get_title().lower().encode('utf-8').replace('é', 'e')), safe='')
	url = conf['server_url'] + '?version=2.0&operation=searchRetrieve&query=dc.title%3D' + url_title + '&maximumRecords=200&recordSchema=unimarcxml'
	try :
		global tree_marc
		tree_marc = etree.parse(urllib.urlopen(url)).getroot()
		global records_count
		records_count = len(tree_marc.xpath('.//ns0:recordData', namespaces = ns_marc))
	except Exception, e :
		format = ''
		logging.error('Wrong url or host unknown : ' + url)
	# Start the creation of the XML with the 'root' tag of the JSON file
	for node in meta_json['root'] :
		create_node(data, node)
	# Write result into output_file
	write_xml_file(output_file, data)

def main() :
	# Load conf file
	with open(conf_file) as conf_f :
		conf_json = json.load(conf_f)
	mets_file = os.path.join(scripts_folder, 'mets.xml')
	output_file = os.path.join(scripts_folder, 'sip.xml')
	# json_file = os.path.join(scripts_folder, sys.argv[0].split(folder_separator)[-1].replace('.py', '.json'))
	json_file = 'scripts/numpat.json'
	# Transform XML into another XML according to a json file
	xml2xml(mets_file, output_file, json_file, conf_json)


#
# Main
#

if __name__ == '__main__':
	main()