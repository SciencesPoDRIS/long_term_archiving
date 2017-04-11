#!/usr/bin/python
# -*- coding: utf-8 -*-


#
# Libs
#

import logging
import os
import shutil


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