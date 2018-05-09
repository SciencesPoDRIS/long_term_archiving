#!/usr/bin/python
# -*- coding: utf-8 -*-
# Execution example : python scripts/cines/sip.py /path/to/mets.file /path/to/output.file /path/to/mapping.file /path/to/conf.file


#
# External libs
#

import copy
import hashlib
import json
import logging
from lxml import etree
import os
import re
import sys
import time
import urllib


#
# Internal libs
#

import sip_filters


#
# Config
#

log_folder = 'log'
log_level = logging.DEBUG
folder_separator = '/'
scripts_folder = 'scripts'
tree_marc_singleton = None
records_count = 0

# Namespaces
xsi = 'http://www.w3.org/2001/XMLSchema-instance'
xsi_schemalocation = 'http://www.cines.fr/pac/sip http://www.cines.fr/pac/sip.xsd'
nsmap = {
	None : 'http://www.cines.fr/pac/sip',
	'xsi' : xsi
}
nsmap_seda = {
	None : 'fr:gouv:culture:archivesdefrance:seda:v1.0'
}
ns = {
	'mods' : 'http://www.loc.gov/mods/v3',
	'mets' : 'http://www.loc.gov/METS/',
	'xlink' : 'http://www.w3.org/1999/xlink',
	'ddi' : 'ddi:codebook:2_2',
	'dc' : 'http://purl.org/dc/elements/1.1/'
}
ns_marc = {
	'ns0' : 'http://docs.oasis-open.org/ns/search-ws/sruResponse',
	'ns1' : 'http://www.loc.gov/MARC21/slim'
}
# Constants
type = {
	'book' : 'Monographie',
	'map' : 'Carte',
	'journal' : 'Journal'
}
format = {
	'jp2' : 'JPEG2000',
	'xml' : 'XML'
}


#
# Functions
#

# Singleton : get the srusrw tree
# Load catalog via protocol SRU/SRW
def get_srusrw_tree() :
	global tree_marc_singleton
	global records_count
	# If tree_marc_singleton is not instanciated, load the catalog
	if tree_marc_singleton is None :
		srusrw_url = get_srusrw_url()
		try :
			tree_marc_singleton = etree.parse(urllib.urlopen(srusrw_url)).getroot()
			records_count = len(tree_marc_singleton.xpath('.//ns0:recordData', namespaces = ns_marc))
			logging.info('SRUSRW count : ' + str(records_count))
		except Exception, e :
			logging.error('Wrong url or host unknown : ' + srusrw_url)
	return tree_marc_singleton

# Build the SRU/SRW url to query the library catalog
def get_srusrw_url() :
	url_title = urllib.quote(re.sub(r'([^\s\w\'-]|_)+', '', get_title().lower().encode('utf-8').replace('é', 'e').replace('ç', 'c').replace('è', 'e').replace('ê', 'e').replace('ń', 'n')), safe='')
	url_creator = urllib.quote(re.sub(r'([^\s\w\'-]|_)+', '', get_creator().lower().encode('utf-8').replace('é', 'e').replace('ç', 'c').replace('è', 'e').replace('ê', 'e').replace('ń', 'n')), safe='')
	srusrw_url = conf['server_url'] + '?version=2.0&operation=searchRetrieve&query='
	if url_creator != '' :
		srusrw_url += 'dc.creator%3D' + url_creator + '%20and%20'
	srusrw_url += 'dc.title%3D' + url_title + '&maximumRecords=200&recordSchema=unimarcxml'
	logging.info('SRUSRW URL : ' + srusrw_url)
	return srusrw_url

def get_title() :
	title = ''
	if len(tree.xpath('.//mods:nonSort', namespaces = ns)) > 0 :
		title += tree.find('.//mods:nonSort', ns).text
	title += tree.find('.//mods:title', ns).text
	# Truncate title after question mark
	title = title.split('?')[0]
	return title

def get_creator() :
	creator = ''
	if len(tree.xpath('.//mods:namePart[@type="family"]', namespaces = ns)) > 0 :
		creator += tree.find('.//mods:namePart[@type="family"]', ns).text
	return creator

# Write SIP results into result file
def write_xml_file(file_path, data) :
	tree = etree.ElementTree(data)
	tree.write(file_path, encoding='UTF-8', pretty_print=True, xml_declaration=True)

# Download an image from its image_url if it exists into the image_path
def download_image(image_url, image_path) :
	try :
		urllib.urlretrieve(image_url, image_path)
		return True
	except Exception as e :
		logging.error('Image url doesn\'t exist : ' + image_url)
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
	# By default filters is first_filter, so get only the content of the first occurrence
	filters = ['first']
	for access_method in node['value'] :
		# If values is empty, pass through next access method
		# Implement logic for xpath
		if len(values) == 0 and access_method['method'] == 'xpath' :
			# Set filters logic for this method
			if 'filters' in access_method :
				filters = access_method['filters']
			# Iterate over xpaths
			for xpath in access_method['paths'] :
				# Extract values
				element = tree if element is None else element
				if len(element.xpath(xpath, namespaces = ns)) > 0 :
					values += element.xpath(xpath, namespaces = ns)
		# Implement logic for the SRU/SRW protocol
		elif len(values) == 0 and access_method['method'] == 'srusrw' :
			tree_marc = get_srusrw_tree()
			if records_count > 0 :
				# Set filters logic for this method
				if 'filters' in access_method:
					filters = access_method['filters']
				for xpath in access_method['paths'] :
					xpath_value = tree_marc.find(xpath, ns_marc)
					if xpath_value is not None :
						values += [tree_marc.find(xpath, ns_marc)]
	# Implement the filters logic
	# TODO : check that this function exists
	if len(values) > 0 :
		contents = values
		for filter in filters :
			contents = eval('sip_filters.' + filter + '_filter(contents)')
	else :
		logging.error('Node "' + node['name'] + '" has a problem with the filters attribute.')
	return contents

def get_attributes(attributes, element) :
	res = {}
	for attribute in attributes :
		if 'value' in attribute :
			res[attribute['name']] = attribute['value']
		elif 'xpath' in attribute :
			tmp = element.xpath(attribute['xpath'], namespaces = ns)
			if 'filters' in attribute :
				for filter in attribute['filters'] :
					tmp = eval('sip_filters.' + filter + '_filter(tmp)')
			res[attribute['name']] = tmp[0]
	return res


# Build the node (name, value, children...) and add it to the node_parent
def create_node(node_parent, node, element) :
	node_name = node['name']
	node_attributes = get_attributes(node['attributes'] if 'attributes' in node else {}, element)
	if 'recursive' in node :
		node_b = copy.deepcopy(node)
		node_b['repeat'] = node_b['repeat'].replace('.//dsc/c', './c')
		node['children'].append(node_b)
		del node['recursive']
		create_node(node_parent, node, element)
	# If node has children, create them
	elif 'repeat' in node :
		repeats = element.xpath(node['repeat'], namespaces = ns)
		# Delete the repeat attribute
		node_b = copy.deepcopy(node)
		del node_b['repeat']
		for repeat in repeats :
			# Recall the function to create the node
			create_node(node_parent, node_b, repeat)
	elif 'children' in node :
		node_children = node['children']
		# If node_parent is None, create the root element
		if node_parent is None :
			new_node = etree.Element(node_name, node_attributes)
		else :
			new_node = etree.SubElement(node_parent, node_name, node_attributes)
		for node_child in node_children :
			create_node(new_node, node_child, element)
	# Else get the node values and create as many nodes as return by the get_node_values function
	elif 'value' in node :
		values = get_node_values(node, element)
		for value in values :
			etree.SubElement(node_parent, node_name, node_attributes).text = value
	elif 'filters' in node :
		value = ''
		for filter in node['filters'] :
			if value == '' :
				value = eval('sip_filters.' + filter + '_filter()')
			else :
				value = eval('sip_filters.' + filter + '_filter(value)')
		etree.SubElement(node_parent, node_name, node_attributes).text = value
	if 'default_values' in node and ((not 'value' in node) or ('value' in node and len(values) == 0)) :
		for default_value in node['default_values'] :
			etree.SubElement(node_parent, node_name, node_attributes).text = default_value
	# If node_parent is None, new_node is the root element, so return it coz it contains the whole tree
	if node_parent is None :
		return new_node

def generate(input_file, output_file, json_file, conf_arg) :
	# Load input_file
	global tree
	global conf
	conf = conf_arg
	tree = etree.parse(input_file).getroot()
	# Load meta_json file
	with open(json_file) as json_f :
		meta_json = json.load(json_f)
	# Start the creation of the XML with the 'root' tag of the JSON file
	for node in meta_json['root'] :
		data = create_node(None, node, tree)
	# Write result into output_file
	write_xml_file(output_file, data)

def main() :
	# Check that log folder exists, else create it
	if not os.path.exists(log_folder) :
		os.makedirs(log_folder)
	# Create log file path
	log_file = os.path.join(log_folder, sys.argv[0].split(folder_separator)[-1].replace('.py', '.log'))
	# Init logs
	logging.basicConfig(filename=log_file, filemode='a+', format='%(asctime)s  |  %(levelname)s  |  %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=log_level)
	logging.info('Start script')
	# Check if sys.argv is a list
	if not isinstance(sys.argv, list) :
		logging.error('sys.argv is not an array. Please check your command line.')
		sys.exit()
	# Check if the number of arguments is correct
	elif len(sys.argv) != 5 :
		logging.error('Wrong number of args. Your command line should look like : python sip.py /path/to/mets.file /path/to/output.file /path/to/matching.file path/to/conf.file')
		sys.exit()
	else :
		mets_file = sys.argv[1]
		output_file = sys.argv[2]
		json_file = sys.argv[3]
		conf_file = sys.argv[4]
		# Load conf file
		with open(conf_file) as conf_f :
			conf_arg = json.load(conf_f)
		# Transform XML into another XML according to a json file
		generate(mets_file, output_file, json_file, conf_arg)


#
# Main
#

if __name__ == '__main__':
	main()
