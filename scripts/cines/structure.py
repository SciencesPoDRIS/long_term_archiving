#!/usr/bin/python
# -*- coding: utf-8 -*-


#
# Libs
#

import logging


#
# Functions
#

# Create the tree structure for the archived folder, as wanted by the CINES platform
def create(local_folder_path) :
	# If not exists, create DEPOT folder
	createFolder(os.path.join(local_folder_path, 'DEPOT'))
	# If not exists, create DESC folder into DEPOT folder
	createFolder(os.path.join(local_folder_path, 'DEPOT', 'DESC'))
	# logging.info('Create structure for folder : ' + local_folder_path)
	# If exists, delete "ill" folder
	# removeFolder(os.path.join(local_folder_path, 'ill'))
	# If exists, delete "illview" folder
	# removeFolder(os.path.join(local_folder_path, 'illview'))
	# If exists, delete "view" folder
	# removeFolder(os.path.join(local_folder_path, 'view'))
	
	
	
	# for root, dirs, files in os.walk(local_folder_path):
	# 	for file in files :
	# 		# If exists, delete .pdf file at the root of the folder
	# 		# And if exists, recursively delete ".DS_Store" files (for MAC)
	# 		if file.lower().endswith('.pdf') or file.lower() == '.ds_store' :
	# 			os.remove(os.path.join(root, file))
	# 		# If exists, move METS file into /DEPOT/DESC
	# 		elif file.lower().endswith('.xml') :
	# 			if not 'DEPOT' in root :
	# 				mets_file = file
	# 				shutil.move(os.path.join(local_folder_path, mets_file), os.path.join(local_folder_path, 'DEPOT', 'DESC', mets_file))
	# 		# Else move others files into /DEPOT
	# 		else :
	# 			if not 'DEPOT' in root :
	# 				shutil.move(os.path.join(local_folder_path, file), os.path.join(local_folder_path, 'DEPOT', file))
	# 	# Move all folders into /DEPOT, except those "DEPOT" itself
	# 	for dir in dirs :
	# 		if dir != 'DEPOT' and not root.endswith('/DEPOT') :
	# 			shutil.move(os.path.join(local_folder_path, dir), os.path.join(local_folder_path, 'DEPOT', dir))
	# return mets_file

def checkFolderWithConf(folder, conf) :
	for key in conf.keys() :
		relative_path = unicode(folder, "utf8").replace(sys.argv[1], '')
		if relative_path.startswith(key) :
			return key
	return False

def fill(local_folder_path, remote_folder_path) :
	# Generate log file path
	log_file = os.path.join(log_folder, sys.argv[0].replace('.py', '.log'))
	# Init logs
	logging.basicConfig(filename=log_file, filemode='a+', format='%(asctime)s  |  %(levelname)s  |  %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=log_level)
	logging.info('Start script')
	# Load conf file
	with open(sys.argv[2]) as conf_file :
		conf = json.load(conf_file)
	# Create CINES folder
	cines_folder = 'CINES'
	# Create remote folder
	if not os.path.exists(cines_folder) :
		os.makedirs(cines_folder)
	for root, dirs, files in os.walk(sys.argv[1]) :
		# Check if current folder is listed in the conf
		rank = checkFolderWithConf(root, conf)
		if rank :
			for file in files :
				if file.split('.')[-1] in conf[rank] :
					distdir = os.path.join(cines_folder, root.replace(sys.argv[1], ''))
					if not os.path.exists(distdir) :
						logging.info('Create folder : ' + distdir)
						os.makedirs(distdir)
					logging.info('Copy file : ' + file)
					shutil.copy(os.path.join(root, file), distdir)
	logging.info('End script')