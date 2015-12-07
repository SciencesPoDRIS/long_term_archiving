#!/usr/bin/python
# -*- coding: utf-8 -*-
# Execution example : python scripts/sip_numpat.py "path/to/folder/to/archive"

#
# Libs
#
import codecs, hashlib, json, logging, os, shutil, sys, urllib, urllib2
from lxml import etree

#
# Config
#
folder_separator = '/'
log_folder = 'log'
log_level = logging.DEBUG
sip_folder = 'sips'
sip_file_name = 'sip.xml'
image_folder = 'images'
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
def generate_sip_from_mets(archive_folder, mets_file) :
	data = ''
	# Load METS file
	tree = etree.parse(archive_folder + mets_file).getroot()
	data = etree.Element('pac', nsmap = nsmap, attrib = {'{' + xsi + '}schemaLocation' : xsi_schemalocation})
	docdc = etree.SubElement(data, 'DocDC')
	title = tree.find('.//mods:nonSort', ns).text + tree.find('.//mods:title', ns).text
	etree.SubElement(docdc, 'title', {'language' : language}).text = title
	etree.SubElement(docdc, 'creator').text = tree.find('.//mods:namePart[@type="given"]', ns).text + ' ' + tree.find('.//mods:namePart[@type="family"]', ns).text
	for topic in tree.findall('.//mods:topic', ns) :
		etree.SubElement(docdc, 'subject', {'language' : language}).text = topic.text
	etree.SubElement(docdc, 'description', {'language' : language}).text = description.decode('utf8')
	etree.SubElement(docdc, 'publisher').text = tree.find('.//mods:publisher', ns).text
	etree.SubElement(docdc, 'date').text = tree.find('.//mods:dateIssued', ns).text
	if tree.find('.//mods:genre[@authority="marcgt"]', ns).text in type.keys() :
		etree.SubElement(docdc, 'type', {'language' : language}).text = type[tree.find('.//mods:genre[@authority="marcgt"]', ns).text]
	else :
		logging.error('Type missing : ' + tree.find('.//mods:genre[@authority="marcgt"]', ns).text + ' is not in types dictionnary.')
		print 'Type missing : ' + tree.find('.//mods:genre[@authority="marcgt"]', ns).text + ' is not in types dictionnary.'
	url_title = title.lower().encode('utf-8').replace(' ', '%20').replace('é', 'e')
	url = conf['server_url'] + '?version=2.0&operation=searchRetrieve&query=dc.title%3D' + url_title + '&maximumRecords=200&recordSchema=unimarcxml'
	try :
		tree_marc = etree.parse(urllib.urlopen(url)).getroot()
		records_count = len(tree_marc.findall('.//ns0:recordData', ns_marc))
		if records_count > 0 :
			format = tree_marc.find('.//ns1:datafield[@tag="215"]/ns1:subfield[@code="a"]', ns_marc).text + ' ' + tree_marc.find('.//ns1:datafield[@tag="215"]/ns1:subfield[@code="d"]', ns_marc).text
		else :
			format = ''
			logging.info('No format to add for document : ' + title)
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
	for file in tree.findall('.//mets:file', ns) :
		# List only the not compressed files, ie. those in "master" or "ocr" folder
		if 'file://master/' in file.find('.//mets:FLocat', ns).get('{http://www.w3.org/1999/xlink}href') or 'file://ocr/' in file.find('.//mets:FLocat', ns).get('{http://www.w3.org/1999/xlink}href') :
			fichmeta = etree.SubElement(data, 'FichMeta')
			if file.get('MIMETYPE') in mimetype :
				etree.SubElement(fichmeta, 'formatFichier').text = mimetype[file.get('MIMETYPE')]
			else :
				logging.error('Mimetype missing : ' + tree.find('.//mods:genre[@authority="marcgt"]', ns).text + ' is not in mimetypes dictionnary.')
				print 'Mimetype missing : ' + tree.find('.//mods:genre[@authority="marcgt"]', ns).text + ' is not in mimetypes dictionnary.'
			etree.SubElement(fichmeta, 'nomFichier').text = file.find('.//mets:FLocat', ns).get('{http://www.w3.org/1999/xlink}href').replace('file://master/', 'master/')
			# If checksum doesn't exist (for .jpg file by example), download file and calculate the MD5 checksum
			if file.get('CHECKSUM') is None :
				image_url = file.find('.//mets:FLocat', ns).get('{http://www.w3.org/1999/xlink}href').replace('file:/', 'http://drd-archives01.sciences-po.fr/ArchivesNumPat/Lot1/' + batch_folder)
				image_path = file.find('.//mets:FLocat', ns).get('{http://www.w3.org/1999/xlink}href').replace('file://view/', image_folder + folder_separator)
				# Download this image into the image folder
				if downloadImage(image_url, image_path) :
					etree.SubElement(fichmeta, 'empreinteOri', {'type' : 'MD5'}).text = md5(image_path)
				else :
					pass
			else :
				etree.SubElement(fichmeta, 'empreinteOri', {'type' : file.get('CHECKSUMTYPE')}).text = file.get('CHECKSUM')
	# Clear image folder content
	clearFolder(image_folder)
	sip_file_path = archive_folder + folder_separator + sip_file_name
	writeSipFile(sip_file_path, data)

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

# Calculate the MD5 checksum for the file fname
def md5(fname) :
	hash = hashlib.md5()
	with open(fname, 'rb') as f :
		for chunk in iter(lambda: f.read(4096), b""):
			hash.update(chunk)
	return hash.hexdigest()

def writeSipFile(sip_file_path, data) :
	# Write results into file
	logging.info('Write results in file')
	tree = etree.ElementTree(data)
	tree.write(sip_file_path, encoding='UTF-8', pretty_print=True, xml_declaration=True)
	logging.info('End')

def create_structure(archive_folder) :
	# If exists, delete "ill" folder
	if os.path.exists(archive_folder + 'ill') :
		shutil.rmtree(archive_folder + 'ill')
	# If exists, delete "illview" folder
	if os.path.exists(archive_folder + 'illview') :
		shutil.rmtree(archive_folder + 'illview')
	# If exists, delete "view" folder
	if os.path.exists(archive_folder + 'view') :
		shutil.rmtree(archive_folder + 'view')
	# If not exists, create DEPOT folder
	if not os.path.exists(archive_folder + 'DEPOT') :
		os.makedirs(archive_folder + 'DEPOT')
	# If not exists, create DESC folder into DEPOT folder
	if not os.path.exists(archive_folder + 'DEPOT' + folder_separator + 'DESC') :
		os.makedirs(archive_folder + 'DEPOT' + folder_separator + 'DESC')
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
					shutil.move(archive_folder + mets_file, archive_folder + 'DEPOT' + folder_separator + 'DESC' + folder_separator + mets_file)
			# Else move others files into /DEPOT
			else :
				if not 'DEPOT' in parent :
					shutil.move(archive_folder + fn, archive_folder + 'DEPOT' + folder_separator + fn)
		# Move all folders into /DEPOT, except those "DEPOT" itself
		for dn in dirnames :
			if dn != 'DEPOT' and not parent.endswith(folder_separator + 'DEPOT') :
				shutil.move(archive_folder + dn, archive_folder + 'DEPOT' + folder_separator + dn)
	# If not exists, create sip.xml from METS file into DEPOT/DESC folder
	if not os.path.exists(archive_folder + sip_file_name) :
		generate_sip_from_mets(archive_folder, 'DEPOT' + folder_separator + 'DESC' + folder_separator + mets_file)
	# TODO : Send it to server through SFTP

#
# Main
#
if __name__ == '__main__' :
	# Check that log folder exists, else create it
	if not os.path.exists(log_folder) :
		os.makedirs(log_folder)
	# Check that image folder exists, else create it
	if not os.path.exists(image_folder) :
		os.makedirs(image_folder)
	# Clear image folder content
	clearFolder(image_folder)
	# Load conf file
	logging.info('Load conf file')
	with open(conf_file) as json_file :
		conf = json.load(json_file)
	# Check that the METS file is passed as argument
	if len(sys.argv) < 2 :
		logging.error('Arguments error')
		print 'Arguments error'
		print 'Correct usage : scripts/' + sys.argv[0] + ' "path/to/folder/to/archive"'
	else :
		# Get archive folder path
		archive_folder = sys.argv[1]
		# Create log file path
		log_file = log_folder + folder_separator + sys.argv[0].split(folder_separator)[-1].replace('.py', '.log')
		# Init logs
		logging.basicConfig(filename = log_file, filemode = 'w', format = '%(asctime)s  |  %(levelname)s  |  %(message)s', datefmt = '%m/%d/%Y %I:%M:%S %p', level = log_level)
		logging.info('Start')
		create_structure(archive_folder)