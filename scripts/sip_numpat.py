#!/usr/bin/python
# -*- coding: utf-8 -*-
# Execution example : python sip_numpat.py path/to/METS.xml

#
# Libs
#
import codecs, hashlib, json, logging, os, sys, urllib, urllib2
import xml.etree.ElementTree as ET

#
# Config
#
folder_separator = '/'
log_folder = 'log'
log_file = log_folder + folder_separator + 'sip_numpat.log'
log_level = logging.DEBUG
sip_folder = 'sips'
sip_file = sip_folder + folder_separator + 'sip_numpat.xml'
image_folder = 'images'
batch_folder = sys.argv[1].split(folder_separator)[-1].split('.')[0]
conf_folder = 'conf'
conf_file = conf_folder + folder_separator + 'conf.json'
# Namespaces
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
version = '1'
versionPrecedente = '0'
mimetype = {
	'image/jp2' : 'JPEG2000',
	'image/xml' : 'XML',
	'image/jpeg' : 'JPEG'
}

#
# Programm
#
def main() :
	data = ''
	# Load METS file
	tree = ET.parse(sys.argv[1]).getroot()
	data = ET.Element('pac', {'xmlns' : 'http://www.cines.fr/pac/sip', 'xmlns:xsi' : 'http://www.w3.org/2001/XMLSchema-instance', 'xsi:schemaLocation' : 'http://www.cines.fr/pac/sip http://www.cines.fr/pac/sip.xsd'})
	docdc = ET.SubElement(data, 'DocDC')
	title = tree.find('.//mods:nonSort', ns).text + tree.find('.//mods:title', ns).text
	ET.SubElement(docdc, 'title', {'language' : language}).text = title
	ET.SubElement(docdc, 'creator').text = tree.find('.//mods:namePart[@type="given"]', ns).text + ' ' + tree.find('.//mods:namePart[@type="family"]', ns).text
	for topic in tree.findall('.//mods:topic', ns) :
		ET.SubElement(docdc, 'subject', {'language' : language}).text = topic.text
	ET.SubElement(docdc, 'description', {'language' : language}).text = description.decode('utf8')
	ET.SubElement(docdc, 'publisher').text = publisher.decode('utf8')
	ET.SubElement(docdc, 'date').text = tree.find('.//mods:dateIssued', ns).text
	if tree.find('.//mods:genre[@authority="marcgt"]', ns).text in type.keys() :
		ET.SubElement(docdc, 'type', {'language' : language}).text = type[tree.find('.//mods:genre[@authority="marcgt"]', ns).text]
	else :
		logging.error('Type missing : ' + tree.find('.//mods:genre[@authority="marcgt"]', ns).text + ' is not in types dictionnary.')
		print 'Type missing : ' + tree.find('.//mods:genre[@authority="marcgt"]', ns).text + ' is not in types dictionnary.'
	url_title = title.lower().encode('utf-8').replace(' ', '%20').replace('é', 'e')
	url = conf['server_url'] + '?version=2.0&operation=searchRetrieve&query=dc.title%3D' + url_title + '&maximumRecords=200&recordSchema=unimarcxml'
	try :
		tree_marc = ET.parse(urllib.urlopen(url)).getroot()
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
	ET.SubElement(docdc, 'format', {'language' : language}).text = format
	ET.SubElement(docdc, 'source', {'language' : language}).text = tree.find('.//mods:identifier[@type="callnumber"]', ns).text
	ET.SubElement(docdc, 'language').text = language
	for geographic in tree.findall('.//mods:geographic', ns) :
		ET.SubElement(docdc, 'coverage', {'language' : language}).text = geographic.text
	for temporal in tree.findall('.//mods:temporal', ns) :
		ET.SubElement(docdc, 'coverage', {'language' : language}).text = temporal.text
	ET.SubElement(docdc, 'rights', {'language' : language}).text = rights
	docmeta = ET.SubElement(data, 'DocMeta')
	ET.SubElement(docmeta, 'identifiantDocProducteur').text = tree.find('.//mods:recordIdentifier', ns).text
	ET.SubElement(docmeta, 'noteDocument', {'language' : language}).text = tree.find('.//mods:note[@type="cataloging"]', ns).text
	ET.SubElement(docmeta, 'serviceVersant').text = serviceVersant
	ET.SubElement(docmeta, 'version').text = version
	ET.SubElement(docmeta, 'versionPrecedente').text = versionPrecedente
	for file in tree.findall('.//mets:file', ns) :
		fichmeta = ET.SubElement(data, 'FichMeta')
		if file.get('MIMETYPE') in mimetype :
			ET.SubElement(fichmeta, 'formatFichier').text = mimetype[file.get('MIMETYPE')]
		else :
			logging.error('Mimetype missing : ' + tree.find('.//mods:genre[@authority="marcgt"]', ns).text + ' is not in mimetypes dictionnary.')
			print 'Mimetype missing : ' + tree.find('.//mods:genre[@authority="marcgt"]', ns).text + ' is not in mimetypes dictionnary.'
		ET.SubElement(fichmeta, 'nomFichier').text = file.find('.//mets:FLocat', ns).get('{http://www.w3.org/1999/xlink}href').replace('file://master/', '').replace('file://ocr/', '').replace('file://view/', '')
		# If checksum doesn't exist (for .jpg file by example), download file and calculate the MD5 checksum
		if file.get('CHECKSUM') is None :
			image_url = file.find('.//mets:FLocat', ns).get('{http://www.w3.org/1999/xlink}href').replace('file:/', 'http://drd-archives01.sciences-po.fr/ArchivesNumPat/Lot1/' + batch_folder)
			image_path = file.find('.//mets:FLocat', ns).get('{http://www.w3.org/1999/xlink}href').replace('file://view/', image_folder + folder_separator)
			# Download this image into the image folder
			if downloadImage(image_url, image_path) :
				ET.SubElement(fichmeta, 'empreinteOri', {'type' : 'MD5'}).text = md5(image_path)
			else :
				pass
		else :
			ET.SubElement(fichmeta, 'empreinteOri', {'type' : file.get('CHECKSUMTYPE')}).text = file.get('CHECKSUM')
	# Clear image folder content
	clearFolder(image_folder)
	writeSipFile(data)

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

def writeSipFile(data) :
	# Write result into file
	logging.info('Write results in file')
	tree = ET.ElementTree(data)
	tree.write(sip_file, encoding='utf8')
	logging.info('End')

#
# Main
#
if __name__ == '__main__':
	# Check that log folder exists, else create it
	if not os.path.exists(log_folder) :
		os.makedirs(log_folder)
	# Check that image folder exists, else create it
	if not os.path.exists(image_folder) :
		os.makedirs(image_folder)
	# Clear image folder content
	clearFolder(image_folder)
	# Init logs
	logging.basicConfig(filename = log_file, filemode = 'w', format = '%(asctime)s  |  %(levelname)s  |  %(message)s', datefmt = '%m/%d/%Y %I:%M:%S %p', level = log_level)
	logging.info('Start')
	# Load conf file
	logging.info('Load conf file')
	with open(conf_file) as json_file:
		conf = json.load(json_file)
	# Check that the METS file is passed as argument
	if len(sys.argv) < 2 :
		logging.error('Arguments error')
		print 'Arguments error'
		print 'Correct usage : ' + sys.argv[0] + ' "path/to/METS.xml"'
	else :
		main()