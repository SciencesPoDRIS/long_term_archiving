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
	logging.info('Write SIP into file')
	tree = etree.ElementTree(data)
	tree.write(sip_file_path, encoding='UTF-8', pretty_print=True, xml_declaration=True)

# Generate the SIP file according to a METS file
def generateSipFromMets(local_folder_path, mets_file) :
	logging.info('Generate SIP file from METS file for folder : ' + local_folder_path)
	batch_folder = local_folder_path.split('/')[-1]
	data = ''
	# Load METS file
	tree = etree.parse(os.path.join(local_folder_path, mets_file)).getroot()
	data = etree.Element('pac', nsmap=nsmap, attrib={'{' + xsi + '}schemaLocation' : xsi_schemalocation})
	docdc = etree.SubElement(data, 'DocDC')
	title = ''
	if len(tree.findall('.//mods:nonSort', ns)) > 0 :
		title += tree.find('.//mods:nonSort', ns).text
	title += tree.find('.//mods:title', ns).text
	etree.SubElement(docdc, 'title', {'language' : language}).text = title
	etree.SubElement(docdc, 'creator').text = tree.find('.//mods:namePart[@type="given"]', ns).text + ' ' + tree.find('.//mods:namePart[@type="family"]', ns).text
	for topic in tree.findall('.//mods:topic', ns) :
		etree.SubElement(docdc, 'subject', {'language' : language}).text = topic.text
	etree.SubElement(docdc, 'description', {'language' : language}).text = description.decode('utf8')
	if len(tree.findall('.//mods:publisher', ns)) > 0 :
		etree.SubElement(docdc, 'publisher').text = tree.find('.//mods:publisher', ns).text
	else :
		etree.SubElement(docdc, 'publisher').text = publisher
	etree.SubElement(docdc, 'date').text = tree.find('.//mods:dateIssued', ns).text
	if tree.find('.//mods:genre[@authority="marcgt"]', ns).text in type.keys() :
		etree.SubElement(docdc, 'type', {'language' : language}).text = type[tree.find('.//mods:genre[@authority="marcgt"]', ns).text]
	else :
		logging.error('Type missing : ' + tree.find('.//mods:genre[@authority="marcgt"]', ns).text + ' is not in types dictionnary.')
		print 'Type missing : ' + tree.find('.//mods:genre[@authority="marcgt"]', ns).text + ' is not in types dictionnary.'
	url_title = urllib.quote(re.sub(r'([^\s\w\'-]|_)+', '', title.lower().encode('utf-8').replace('é', 'e')), safe='')
	url = conf['server_url'] + '?version=2.0&operation=searchRetrieve&query=dc.title%3D' + url_title + '&maximumRecords=200&recordSchema=unimarcxml'
	try :
		tree_marc = etree.parse(urllib.urlopen(url)).getroot()
		records_count = len(tree_marc.findall('.//ns0:recordData', ns_marc))
		if records_count > 0 :
			format = tree_marc.find('.//ns1:datafield[@tag="215"]/ns1:subfield[@code="a"]', ns_marc).text + ' ' + tree_marc.find('.//ns1:datafield[@tag="215"]/ns1:subfield[@code="d"]', ns_marc).text
		else :
			format = ''
			logging.info('No format to add for document : ' + title)
			logging.info('The url is probably wrong : ' + url)
	except Exception, e :
		format = ''
		logging.error('Wrong url / host unknown : ' + url)
		print 'Wrong url / host unknown : ' + url
	etree.SubElement(docdc, 'format', {'language' : language}).text = format
	etree.SubElement(docdc, 'source', {'language' : language}).text = tree.find('.//mods:identifier[@type="callnumber"]', ns).text
	etree.SubElement(docdc, 'language').text = language
	for geographic in tree.findall('.//mods:geographic', ns) :
		etree.SubElement(docdc, 'coverage', {'language' : language}).text = geographic.text
	for temporal in tree.findall('.//mods:temporal', ns) :
		etree.SubElement(docdc, 'coverage', {'language' : language}).text = temporal.text
	etree.SubElement(docdc, 'rights', {'language' : language}).text = rights
	docmeta = etree.SubElement(data, 'DocMeta')
	etree.SubElement(docmeta, 'identifiantDocProducteur').text = tree.find('.//mods:recordIdentifier', ns).text
	if tree.find('.//mods:note[@type="cataloging"]', ns) in type.keys() :
		etree.SubElement(docmeta, 'noteDocument', {'language' : language}).text = tree.find('.//mods:note[@type="cataloging"]', ns).text
	etree.SubElement(docmeta, 'serviceVersant').text = serviceVersant
	etree.SubElement(docmeta, 'planClassement', {'language' : language}).text = planClassement.decode('utf8')
	# Add METS file as XML file
	fichmeta = etree.SubElement(data, 'FichMeta')
	etree.SubElement(fichmeta, 'formatFichier').text = 'XML'
	etree.SubElement(fichmeta, 'nomFichier').text = mets_file.replace('DEPOT/', '')
	etree.SubElement(fichmeta, 'empreinteOri', {'type' : 'MD5'}).text = md5(os.path.join(local_folder_path, mets_file))
	for file in tree.findall('.//mets:file', ns) :
		# List only the not compressed files, ie. those in "master" or "ocr" folder
		if 'file://master/' in file.find('.//mets:FLocat', ns).get('{http://www.w3.org/1999/xlink}href') or 'file://ocr/' in file.find('.//mets:FLocat', ns).get('{http://www.w3.org/1999/xlink}href') :
			fichmeta = etree.SubElement(data, 'FichMeta')
			if file.get('MIMETYPE') in mimetype :
				etree.SubElement(fichmeta, 'formatFichier').text = mimetype[file.get('MIMETYPE')]
			else :
				logging.error('Mimetype missing : ' + tree.find('.//mods:genre[@authority="marcgt"]', ns).text + ' is not in mimetypes dictionnary.')
			etree.SubElement(fichmeta, 'nomFichier').text = file.find('.//mets:FLocat', ns).get('{http://www.w3.org/1999/xlink}href').replace('file://master/', 'master/').replace('file://ocr/', 'master/')
			# For all files, download it and calculate the MD5 checksum
			image_url = file.find('.//mets:FLocat', ns).get('{http://www.w3.org/1999/xlink}href').replace('file:/', 'http://drd-archives01.sciences-po.fr/ArchivesNumPat/Lot1/' + batch_folder).replace('ocr/', 'master/')
			image_path = file.find('.//mets:FLocat', ns).get('{http://www.w3.org/1999/xlink}href').replace('file://master/', download_folder + '/').replace('file://ocr/', download_folder + '/')
			# Download all images into the 'download' folder
			if downloadImage(image_url, image_path) :
				etree.SubElement(fichmeta, 'empreinteOri', {'type' : 'MD5'}).text = md5(image_path)
			else :
				pass
	# Clear 'download' folder content
	clearFolder(download_folder)
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
		# Todo : send only one folder
		sendCinesArchive(local_folder_path)
		# Write the folder as blacklisted folder into the file
		writeAsBlacklistedFolder(subdir)
	logging.info('End script')