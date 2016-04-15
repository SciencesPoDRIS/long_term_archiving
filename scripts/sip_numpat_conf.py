#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Libs
#
import codecs
import ftptool
import hashlib
import json
import logging
from lxml import etree
import os
import paramiko
import re
import shutil
import sys
import urllib
import urllib2

#
# Config
#
folder_separator = '/'
download_folder = 'download'
blacklisted_folders_file = 'blacklistedFolders'
blacklisted_folders = []
forbidden_folders = ['.', '..']
log_folder = 'log'
log_level = logging.DEBUG
conf_folder = 'conf'
conf_file = os.path.join(conf_folder, 'conf.json')
sip_file_name = 'sip.xml'
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
# Constantes
language = 'fra'
subject = 'Non renseigné'
description = 'Non renseigné'
publisher = 's.n.'
type = {
	'book' : 'Monographie'
}
rights = 'Libre de droits'
serviceVersant = 'Fondation Nationale des Sciences Politiques'
planClassement = 'Numérisation patrimoniale'
mimetype = {
	'image/jp2' : 'JPEG2000',
	'image/xml' : 'XML',
	'image/jpeg' : 'JPEG'
}

#
# Functions
#

# Create a new folder into folder_path
# @return True if a new folder has been created, else False
def createFolder(folder_path) :
	# Check if folder already exists
	if not os.path.exists(folder_path) :
		os.mkdir(folder_path)
		return True
	else :
		return False

# Delete the folder into folder_path
# @return True if the folder has been deleted, else False
def removeFolder(folder_path) :
	if os.path.exists(folder_path) :
		shutil.rmtree(folder_path)
		return True
	else :
		return False

# Download a whole folder tree from remote_folder_path into local_folder_path through FTP
def downloadFolder(ftp_host, remote_folder_path, local_folder_path) :
	logging.info('Download the folder to local : ' + remote_folder_path)
	ftp_host.mirror_to_local(remote_folder_path, local_folder_path)

# Create the tree structure for the archived folder, as waited by the CINES platform
def createStructure(local_folder_path) :
	logging.info('Create structure for folder : ' + local_folder_path)
	# If exists, delete "ill" folder
	removeFolder(os.path.join(local_folder_path, 'ill'))
	# If exists, delete "illview" folder
	removeFolder(os.path.join(local_folder_path, 'illview'))
	# If exists, delete "view" folder
	removeFolder(os.path.join(local_folder_path, 'view'))
	# If not exists, create DEPOT folder
	createFolder(os.path.join(local_folder_path, 'DEPOT'))
	# If not exists, create DESC folder into DEPOT folder
	createFolder(os.path.join(local_folder_path, 'DEPOT', 'DESC'))
	for root, dirs, files in os.walk(local_folder_path):
		for file in files :
			# If exists, delete .pdf file at the root of the folder
			# And if exists, recursively delete ".DS_Store" files (for MAC)
			if file.lower().endswith('.pdf') or file.lower() == '.ds_store' :
				os.remove(os.path.join(root, file))
			# If exists, move METS file into /DEPOT/DESC
			elif file.lower().endswith('.xml') :
				if not 'DEPOT' in root :
					mets_file = file
					shutil.move(os.path.join(local_folder_path, mets_file), os.path.join(local_folder_path, 'DEPOT', 'DESC', mets_file))
			# Else move others files into /DEPOT
			else :
				if not 'DEPOT' in root :
					shutil.move(os.path.join(local_folder_path, file), os.path.join(local_folder_path, 'DEPOT', file))
		# Move all folders into /DEPOT, except those "DEPOT" itself
		for dir in dirs :
			if dir != 'DEPOT' and not root.endswith('/DEPOT') :
				shutil.move(os.path.join(local_folder_path, dir), os.path.join(local_folder_path, 'DEPOT', dir))
	return mets_file

# Download an image from its image_url if it exists into the image_path
def downloadImage(image_url, image_path) :
	logging.info('Download an image from its image_url : ' + image_url)
	try :
		req = urllib2.Request(image_url)
		response = urllib2.urlopen(req)
		urllib.urlretrieve(image_url, image_path)
		return True
	except Exception, e :
		logging.error('Image url does\'nt exist : ' + image_url)
		print 'Image url does\'nt exist : ' + image_url
		return False

# Calculate the MD5 checksum for the file fname
def md5(fname) :
	logging.info('Calculate the MD5 checksum for the file : ' + fname)
	hash = hashlib.md5()
	with open(fname, 'rb') as f :
		for chunk in iter(lambda: f.read(4096), b""):
			hash.update(chunk)
	return hash.hexdigest()

# Clear a folder from its content
def clearFolder(folder_path) :
	for file in os.listdir(folder_path) :
		file_path = os.path.join(folder_path, file)
		try :
			if os.path.isfile(file_path):
				os.unlink(file_path)
		except Exception, e :
			logging.error('Folder does\'nt exist : ' + folder_path)
			print 'Folder does\'nt exist : ' + folder_path

# Write SIP results into result file
def writeSipFile(sip_file_path, data) :
	print data
	# logging.info('Write SIP into file')
	# tree = etree.ElementTree(data)
	# tree.write(sip_file_path, encoding='UTF-8', pretty_print=True, xml_declaration=True)

# Generate the SIP file according to a METS file
def generateSipFromMets(local_folder_path, mets_file) :
	# Log
	logging.info('Generate SIP file from METS file for folder : ' + local_folder_path)
	batch_folder = local_folder_path.split('/')[-1]
	# Load METS file
	mets_file = 'data/sc_0000267825_00000000926980.xml'
	xsi_schemalocation = 'http://www.cines.fr/pac/sip http://www.cines.fr/pac/sip.xsd'
	tree = etree.parse(mets_file).getroot()
	data = etree.Element('pac', nsmap=nsmap, attrib={'{' + xsi + '}schemaLocation' : xsi_schemalocation})
	docdc = etree.SubElement(data, 'DocDC')
	# Open conf file
	conf_file = 'scripts/sip_numpat.json'
	with open(conf_file) as json_file :
		conf = json.load(json_file)
		for tag in conf['tags'] :
			etree.SubElement(docdc, tag['name'], tag['attributes']).text = tree.find(tag['xpath'], ns).text
	sip_file_path = os.path.join(local_folder_path, sip_file_name)
	writeSipFile(sip_file_path, data)

# Send archive folder to CINES through SFTP
def sendCinesArchive(local_folder_path) :
	logging.info('Send archive to server through FTP for folder : ' + local_folder_path)
	# Open connection
	transport = paramiko.Transport((conf['ftp_cines_server'], int(conf['ftp_cines_port'])))
	transport.connect(username=conf['ftp_cines_user'], password=conf['ftp_cines_password'])
	sftp = paramiko.SFTPClient.from_transport(transport)
	root_folder_path = local_folder_path.replace(conf['local_path'], conf['remote_cines_path'])
	sftp.mkdir(root_folder_path, 0770)
	# Send file through SFTP
	for dirpath, dirnames, filenames in os.walk(local_folder_path) :
		remote_folder_path = os.path.join(conf['remote_cines_path'], folder_separator.join(dirpath.split(folder_separator)[4:]))
		# Create remote directories
		for dirname in dirnames :
			folder_path = os.path.join(dirpath, dirname).replace(conf['local_path'], conf['remote_cines_path'])
			sftp.mkdir(folder_path, 0770)
		# Create remote files
		for filename in filenames :
			local_file_path = os.path.join(dirpath, filename)
			remote_file_path = os.path.join(dirpath, filename).replace(conf['local_path'], conf['remote_cines_path'])
			sftp.put(local_file_path, remote_file_path)
	# Close connection
	sftp.close()
	transport.close()

def readBlacklistedFolders() :
	with open(blacklisted_folders_file, 'rb') as f :
		for l in f.readlines() :
			blacklisted_folders.append(l.replace('\n', ''))

def writeAsBlacklistedFolder(folder) :
	logging.info('Write folder as treated on so as blacklisted : ' + folder)
	data = folder + '\n'
	with codecs.open(blacklisted_folders_file, 'a+', 'utf8') as f :
		f.write(data.decode('utf8'))
	f.close()


#
# Main
#

if __name__ == '__main__' :
	# Check that log folder exists, else create it
	if not os.path.exists(log_folder) :
		os.makedirs(log_folder)
	# Create log file path
	log_file = os.path.join(log_folder, sys.argv[0].replace('.py', '.log'))
	# Init logs
	logging.basicConfig(filename=log_file, filemode='a+', format='%(asctime)s  |  %(levelname)s  |  %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=log_level)
	logging.info('Start script')
	# Load conf file
	logging.info('Load conf file')
	with open(conf_file) as json_file :
		conf = json.load(json_file)
	# Connect to server through FTP
	ftp_host = ftptool.FTPHost.connect(conf['ftp_server'], user=conf['ftp_user'], password=conf['ftp_password'])
	# List all files and folders from remote_path
	(subdirs, files) = ftp_host.listdir(conf['remote_path'])
	# Filters all forbidden folders
	readBlacklistedFolders()
	subdirs = [x for x in subdirs if x not in forbidden_folders + blacklisted_folders]
	# Check that local_path already exists
	createFolder(conf['local_path'])
	for subdir in subdirs[0:1] :
		local_folder_path = os.path.join(conf['local_path'], subdir)
		remote_folder_path = os.path.join(conf['remote_path'], subdir)
		# Create subdir locally into local_path
		createFolder(local_folder_path)
		# Download subdir locally
		downloadFolder(ftp_host, remote_folder_path, local_folder_path)
		# Create awaited folder structure for CINES
		mets_file = createStructure(local_folder_path)
		# Generate SIP.xml from the METS.xml file
		generateSipFromMets(local_folder_path, os.path.join('DEPOT', 'DESC', mets_file))
		# Send the folder to CINES
		# ToDo : send only one folder (???)
		sendCinesArchive(local_folder_path)
		# Write the folder as blacklisted folder into the file
		writeAsBlacklistedFolder(subdir)
	logging.info('End script')