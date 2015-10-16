#!/usr/bin/python
# -*- coding: utf-8 -*-
# Execution example : python sip_numpat.py path/to/METS.xml

#
# Libs
#
import codecs, logging, os, sys
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
# Namespaces
ns = {
	'mods' : 'http://www.loc.gov/mods/v3',
	'mets' : 'http://www.loc.gov/METS/',
	'xlink' : 'http://www.w3.org/1999/xlink'
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
	ET.SubElement(docdc, 'title', {'language' : language}).text = tree.find('.//mods:nonSort', ns).text + tree.find('.//mods:title', ns).text
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
	# ToDo
	# Request by Z3950 protocol
	# Ask Yanick
	# ET.SubElement(docdc, 'format', {'language' : language}).text = 
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
	# ToDo
	# Wait for Alexia returns
	# ET.SubElement(docmeta, 'structureDocument').text = 
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
		# ToDo
		# Ask Olesea what to do in this situation : generate the checksum ???
		if file.get('CHECKSUM') is None :
			logging.error('Checksum is missing for file : ' + file.find('.//mets:FLocat', ns).get('{http://www.w3.org/1999/xlink}href'))
			print 'Checksum is missing for file : ' + file.find('.//mets:FLocat', ns).get('{http://www.w3.org/1999/xlink}href')
		else :
			ET.SubElement(fichmeta, 'empreinteOri', {'type' : file.get('CHECKSUMTYPE')}).text = file.get('CHECKSUM')
	writeSipFile(data)

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
	if not os.path.exists(log_folder):
		os.makedirs(log_folder)
	# Init logs
	logging.basicConfig(filename = log_file, filemode = 'w', format = '%(asctime)s  |  %(levelname)s  |  %(message)s', datefmt = '%m/%d/%Y %I:%M:%S %p', level = log_level)
	logging.info('Start')
	# Check that the METS file is passed as argument
	if len(sys.argv) < 2 :
		logging.error('Arguments error')
		print 'Arguments error'
		print 'Correct usage : ' + sys.argv[0] + ' "path/to/METS.xml"'
	else :
		main()