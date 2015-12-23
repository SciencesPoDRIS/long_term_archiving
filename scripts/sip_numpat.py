#!/usr/bin/python
# -*- coding: utf-8 -*-
# Execution example : python scripts/sip_numpat.py

#
# Libs
#
import codecs, hashlib, json, logging, os, paramiko, re, shutil, sys, urllib, urllib2
from lxml import etree

#
# Config
#
folder_separator = '/'
log_folder = 'log'
log_level = logging.DEBUG
sip_folder = 'sips'
sip_file_name = 'sip.xml'
download_folder = 'download'
conf_folder = 'conf'
conf_file = conf_folder + folder_separator + 'conf.json'
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
# Programm
#

# Send archive folder through SFTP
def sendArchive(archive_path) :
	# Open connection
	transport = paramiko.Transport((conf['ftp_server'], int(conf['ftp_port'])))
	transport.connect(username = conf['ftp_user'], password = conf['ftp_password'])
	sftp = paramiko.SFTPClient.from_transport(transport)
	root_folder_path = archive_path.replace(conf['archive_folder'], conf['ftp_path'])
	sftp.mkdir(root_folder_path, 0770)
	# Send file through SFTP
	for dirpath, dirnames, filenames in os.walk(archive_path) :
		remote_folder_path = os.path.join(conf['ftp_path'], folder_separator.join(dirpath.split(folder_separator)[4:]))
		# Create remote directories
		for dirname in dirnames :
			folder_path = os.path.join(dirpath, dirname).replace(conf['archive_folder'], conf['ftp_path'])
			sftp.mkdir(folder_path, 0770)
		# Create remote files
		for filename in filenames :
			local_file_path = os.path.join(dirpath, filename)
			remote_file_path = os.path.join(dirpath, filename).replace(conf['archive_folder'], conf['ftp_path'])
			sftp.put(local_file_path, remote_file_path)
	# Close connection
	sftp.close()
	transport.close()

# Download an image from its image_url if it exists into the image_path
def downloadImage(image_url, image_path) :
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
	tree.write(sip_file_path, encoding = 'UTF-8', pretty_print = True, xml_declaration = True)
	logging.info('End')

# Generate the SIP file according to a METS file
def generate_sip_from_mets(archive_folder, mets_file) :
	batch_folder = archive_folder.split(folder_separator)[-1]
	logging.info('Generate SIP file from METS file')
	data = ''
	# Load METS file
	tree = etree.parse(os.path.join(archive_folder, mets_file)).getroot()
	data = etree.Element('pac', nsmap = nsmap, attrib = {'{' + xsi + '}schemaLocation' : xsi_schemalocation})
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
	etree.SubElement(fichmeta, 'empreinteOri', {'type' : 'MD5'}).text = md5(os.path.join(archive_folder, mets_file))
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
			image_path = file.find('.//mets:FLocat', ns).get('{http://www.w3.org/1999/xlink}href').replace('file://master/', download_folder + folder_separator).replace('file://ocr/', download_folder + folder_separator)
			# Download all images into the 'download' folder
			if downloadImage(image_url, image_path) :
				etree.SubElement(fichmeta, 'empreinteOri', {'type' : 'MD5'}).text = md5(image_path)
			else :
				pass
	# Clear 'download' folder content
	clearFolder(download_folder)
	sip_file_path = archive_folder + folder_separator + sip_file_name
	writeSipFile(sip_file_path, data)
	sendArchive(archive_folder)

# Create the tree structure for the archived folder, as waited by the CINES platform
def create_structure(archive_folder) :
	logging.info('Create folder structure')
	# If exists, delete "ill" folder
	if os.path.exists(os.path.join(archive_folder, 'ill')) :
		shutil.rmtree(os.path.join(archive_folder, 'ill'))
	# If exists, delete "illview" folder
	if os.path.exists(os.path.join(archive_folder, 'illview')) :
		shutil.rmtree(os.path.join(archive_folder, 'illview'))
	# If exists, delete "view" folder
	if os.path.exists(os.path.join(archive_folder, 'view')) :
		shutil.rmtree(os.path.join(archive_folder, 'view'))
	# If not exists, create DEPOT folder
	if not os.path.exists(os.path.join(archive_folder, 'DEPOT')) :
		os.makedirs(os.path.join(archive_folder, 'DEPOT'))
	# If not exists, create DESC folder into DEPOT folder
	if not os.path.exists(os.path.join(archive_folder, 'DEPOT', 'DESC')) :
		os.makedirs(os.path.join(archive_folder, 'DEPOT', 'DESC'))
	for parent, dirnames, filenames in os.walk(archive_folder):
		for fn in filenames :
			# If exists, delete .pdf file at the root of the folder
			# And if exists, recursively delete ".DS_Store" files (for MAC)
			if fn.lower().endswith('.pdf') or fn.lower() == '.ds_store' :
				os.remove(os.path.join(parent, fn))
			# If exists, move METS file into /DEPOT/DESC
			elif fn.lower().endswith('.xml') :
				if not 'DEPOT' in parent :
					mets_file = fn
					shutil.move(os.path.join(archive_folder, mets_file), os.path.join(archive_folder, 'DEPOT', 'DESC', mets_file))
			# Else move others files into /DEPOT
			else :
				if not 'DEPOT' in parent :
					shutil.move(os.path.join(archive_folder, fn), os.path.join(archive_folder, 'DEPOT', fn))
		# Move all folders into /DEPOT, except those "DEPOT" itself
		for dn in dirnames :
			if dn != 'DEPOT' and not parent.endswith(folder_separator + 'DEPOT') :
				shutil.move(os.path.join(archive_folder, dn), os.path.join(archive_folder, 'DEPOT', dn))
	# If not exists, create sip.xml from METS file into DEPOT/DESC folder
	if not os.path.exists(archive_folder + sip_file_name) :
		generate_sip_from_mets(archive_folder, os.path.join('DEPOT', 'DESC', mets_file))

#
# Main
#
if __name__ == '__main__' :
	# Check that log folder exists, else create it
	if not os.path.exists(log_folder) :
		os.makedirs(log_folder)
	# Check that image folder exists, else create it
	if not os.path.exists(download_folder) :
		os.makedirs(download_folder)
	# Create log file path
	log_file = log_folder + folder_separator + sys.argv[0].split(folder_separator)[-1].replace('.py', '.log')
	# Init logs
	logging.basicConfig(filename = log_file, filemode = 'w', format = '%(asctime)s  |  %(levelname)s  |  %(message)s', datefmt = '%m/%d/%Y %I:%M:%S %p', level = log_level)
	logging.info('Start')
	# Clear 'download' folder content
	logging.info('Clear \'download\' folder content')
	clearFolder(download_folder)
	# Load conf file
	logging.info('Load conf file')
	with open(conf_file) as json_file :
		conf = json.load(json_file)
	# Check that the METS file is passed as argument
	if len(sys.argv) < 1 :
		logging.error('Arguments error')
		print 'Arguments error'
		print 'Correct usage : scripts/' + sys.argv[0]
	else :
		for item in os.listdir(conf['archive_folder']) :
			# Remove mac files
			if item != '.DS_Store' :
				create_structure(os.path.join(conf['archive_folder'], item))