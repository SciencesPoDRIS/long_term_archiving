#!/usr/bin/python
# -*- coding: utf-8 -*-
# Execution example : python scripts/long_term_archiving.py MY_PROJECT


#
# Libs
#

import codecs
from ftplib import FTP
import json
import logging
import os
import paramiko
import shutil
import sys
from cines import sip


#
# Config
#

# Complete with the folders number
# whitelisted_folders = ['sc_0000354761_00000000390999', 'sc_0000397026_00000001066004', 'sc_0000611205_00000000309875']
whitelisted_folders = ['sc_0000954232_00000001698433']
folder_separator = '/'
blacklisted_folders_file = 'blacklistedFolders'
blacklisted_folders = []
forbidden_folders = ['.', '..']
log_folder = 'log'
log_level = logging.DEBUG
conf_folder = 'conf'
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
	'ns1' : 'http://www.loc.gov/MARC21/slim',
	'zs'  : 'http://docs.oasis-open.org/ns/search-ws/sruResponse'
}
# Constants
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

# Download the remote_folder_path into the local_folder_path
def ftpDownloadRemoteFolder(remote_folder_path, local_folder_path) :
	logging.info('Download the folder to local : ' + remote_folder_path)
	# Connect to server through FTP
	ftp = FTP(conf['ftp_server'], conf['ftp_user'], conf['ftp_password'])
	# Change current directory
	ftp.cwd(remote_folder_path)
	# Walk through the remote folder content
	contents = []
	ftp.retrlines('LIST', contents.append)
	for content in contents :
		words = content.split(None, 8)
		content_name = words[-1].lstrip()
		# If it is a directory
		if words[0][0] == 'd' :
			if content_name not in forbidden_folders :
				# Create local folder
				local_folder = os.path.join(local_folder_path, content_name)
				createFolder(local_folder)
				# Download remote folder content
				ftpDownloadRemoteFolder(os.path.join(conf['remote_path'], remote_folder_path, content_name), local_folder)
		# Else, it is a file
		else :
			ftp.cwd(remote_folder_path)
			# Download file
			local_filename = os.path.join(local_folder_path, content_name)
			ftp.retrbinary('RETR ' + content_name, open(local_filename, 'w').write)
	ftp.quit()

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

# Send archive folder to CINES through SFTP
def sendCinesArchive(local_folder_path) :
	logging.info('Send archive to server through FTP for folder : ' + local_folder_path)
	# Open connection
	transport = paramiko.Transport((conf['ftp_cines_server'], int(conf['ftp_cines_port'])))
	transport.connect(username=conf['ftp_cines_user'], password=conf['ftp_cines_password'])
	sftp = paramiko.SFTPClient.from_transport(transport)
	root_folder_path = local_folder_path.replace(conf['tmp_path'], conf['remote_cines_path'])
	sftp.mkdir(root_folder_path, 0770)
	# Send file through SFTP
	for dirpath, dirnames, filenames in os.walk(local_folder_path) :
		remote_folder_path = os.path.join(conf['remote_cines_path'], folder_separator.join(dirpath.split(folder_separator)[4:]))
		# Create remote directories
		for dirname in dirnames :
			folder_path = os.path.join(dirpath, dirname).replace(conf['tmp_path'], conf['remote_cines_path'])
			sftp.mkdir(folder_path, 0770)
		# Create remote files
		for filename in filenames :
			local_file_path = os.path.join(dirpath, filename)
			remote_file_path = os.path.join(dirpath, filename).replace(conf['tmp_path'], conf['remote_cines_path'])
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
	log_file = os.path.join(log_folder, sys.argv[0].split(folder_separator)[-1].replace('.py', '.log'))
	# Init logs
	logging.basicConfig(filename=log_file, filemode='a+', format='%(asctime)s  |  %(levelname)s  |  %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=log_level)
	logging.info('Start script')
	# Generate path for config file and mapping file
	my_project = sys.argv[1]
	config_file = os.path.join(conf_folder, 'conf.' + my_project + '.json')
	mapping_file = 'mapping/mapping.' + my_project + '.json'
	sip_file = 'sip.' + my_project + '.xml'
	if not os.path.isfile(config_file) :
		logging.error('Config file %s doesn\'t exist, please create it.', config_file)
		sys.exit()
	if not os.path.isfile(mapping_file) :
		logging.error('Mapping file %s doesn\'t exist, please create it.', config_file)
		sys.exit()
	# Load conf file
	logging.info('Load conf file')
	with open(config_file) as conf_f :
		conf = json.load(conf_f)
	contents_bis = []
	if conf['source'] == 'ftp' :
		# Connect to server through FTP
		logging.info('Connect to server through FTP')
		ftp = FTP(conf['ftp_server'], conf['ftp_user'], conf['ftp_password'])
		ftp.cwd(conf['remote_path'])
		# List all files and folders from remote_path
		ftp.retrlines('LIST', contents_bis.append)
		# Close the FTP connection
		ftp.quit()
	elif conf['source'] == 'local' :
		for root, dirs, files in os.walk(conf['tmp_path']):
			for dir in dirs :
				contents_bis.append(dir)
	else :
		logging.error('Config file has no \'source\' parameter or it is badly setted. The supported values are \'ftp\' ou \'source\'.')
		sys.exit()
	# Filters all forbidden folders
	readBlacklistedFolders()
	# Delete tmp_path before download
	removeFolder(conf['tmp_path'])
	# Check that tmp_path already exists
	createFolder(conf['tmp_path'])
	# for subdir in contents_bis :
	for subdir in contents_bis :
		# Get folder name
		subdir = subdir.split(None, 8)[-1].lstrip()
		# if subdir in white listed folders :
		if subdir in whitelisted_folders :
			local_folder_path = os.path.join(conf['tmp_path'], subdir)
			remote_folder_path = os.path.join(conf['remote_path'], subdir)
			# Create subdir locally into tmp_path
			createFolder(local_folder_path)
			# Download subdir locally from FTP
			if conf['source'] == 'ftp' :
				ftpDownloadRemoteFolder(remote_folder_path, local_folder_path)
			# Create wanted folder structure for CINES
			mets_file = createStructure(local_folder_path)
			# Generate SIP.xml from the METS.xml file
			mets_file_path = os.path.join(local_folder_path, 'DEPOT', 'DESC', mets_file)
			sip_file_path = os.path.join(local_folder_path, sip_file_name)
			sip.generate(mets_file_path, sip_file_path, mapping_file, conf)
			# Send the folder to CINES
			sendCinesArchive(local_folder_path)
			# Write the folder as blacklisted folder into the file
			writeAsBlacklistedFolder(subdir)
			# Delete locally downloaded subdir
			removeFolder(local_folder_path)
	logging.info('End script')