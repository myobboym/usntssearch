# # ## # ## # ## # ## # ## # ## # ## # ## # ## # ## # ## # ## # ## # ## #    
#~ This file is part of NZBmegasearch by pillone.
#~ 
#~ NZBmegasearch is free software: you can redistribute it and/or modify
#~ it under the terms of the GNU General Public License as published by
#~ the Free Software Foundation, either version 3 of the License, or
#~ (at your option) any later version.
#~ 
#~ NZBmegasearch is distributed in the hope that it will be useful,
#~ but WITHOUT ANY WARRANTY; without even the implied warranty of
#~ MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#~ GNU General Public License for more details.
#~ 
#~ You should have received a copy of the GNU General Public License
#~ along with NZBmegasearch.  If not, see <http://www.gnu.org/licenses/>.
# # ## # ## # ## # ## # ## # ## # ## # ## # ## # ## # ## # ## # ## # ## #
import requests
import json
import datetime
import time
import config_settings
import xml.etree.cElementTree as ET
import os
import threading

#~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~

def parse_xmlsearch(s_class, urlParams, tout): 
	parsed_data = []

	try:
		http_result = requests.get(url=s_class.queryURL, params=urlParams, verify=False, timeout=tout)
	except Exception as e:
		print e
		return []
	data = http_result.text
	data = data.replace("<newznab:attr", "<newznab_attr")

	#~ parse errors
	try:
		tree = ET.fromstring(data.encode('utf-8'))
	#~ except BaseException:
		#~ print "ERROR: Wrong API?"
		#~ return parsed_data
	except Exception as e:
		print e
		return parsed_data

	#~ successful parsing
	for elem in tree.iter('item'):
		elem_title = elem.find("title")
		elem_url = elem.find("enclosure")
		elem_pubdate = elem.find("pubDate")
		len_elem_pubdate = len(elem_pubdate.text)
		#~ Tue, 22 Jan 2013 17:36:23 +0000
		#~ removes gmt shift
		elem_postdate =  time.mktime(datetime.datetime.strptime(elem_pubdate.text[0:len_elem_pubdate-6], "%a, %d %b %Y %H:%M:%S").timetuple())
		elem_poster = ''
		
		for attr in elem.iter('newznab_attr'):
			if('name' in attr.attrib):
				if (attr.attrib['name'] == 'poster'): 
					elem_poster = attr.attrib['value']

		d1 = { 
			'title': elem_title.text,
			'poster': elem_poster,
			'size': int(elem_url.attrib['length']),
			'url': elem_url.attrib['url'],
			'filelist_preview': '',
			'group': '',
			'posting_date_timestamp': float(elem_postdate),
			'release_comments': '',
			'ignore':0,
			'provider':s_class.baseURL,
			'providertitle':s_class.name
		}
		parsed_data.append(d1)
	return parsed_data		

#~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~

def loadSearchModules(moduleDir = None):
	global loadedModules
	# Find search modules
	loadedModules = [];
	searchModuleNames = [];
	if moduleDir == None:
		moduleDir = os.path.join(os.path.dirname(__file__),'SearchModules');
	print 'Loading modules from: ' + moduleDir

	for file in os.listdir(moduleDir):
		if file.endswith('.py') and file != '__init__.py':
			searchModuleNames.append(file[0:-3])
	if len(searchModuleNames) == 0:
		print 'No search modules found.'
		return
	else:
		print 'Found ' + str(len(searchModuleNames)) + ' modules'
		
	searchModuleNames = sorted(searchModuleNames)
	# Import the modules that the user has enabled
	print 'Importing: ' + ', '.join(searchModuleNames)
	try:
		for module in searchModuleNames:
			importedModules = __import__('SearchModules.' + module)
	except Exception as e:
		print 'Failed to import search modules: ' + str(e)
		return
	
	print 'instantiating module classes'
	# Instantiate the modules
	for module in searchModuleNames:
		try:
			targetClass = getattr(importedModules, module)
			targetClass = getattr(targetClass, module)
		except Exception as e:
			print 'Unable to load search module ' + module + ': ' + str(e)
		
		try:
			loadedModules.append(targetClass())
		except Exception as e:
			print 'Error instantiating search module ' + module + ': ' + str(e)

# Perform a search using all available modules
def performSearch(queryString,  cfg):
	queryString = queryString.strip()
	# Perform the search using every module
	global globalResults
	if 'loadedModules' not in globals():
		loadSearchModules()
	globalResults = []
	threadHandles = []
	lock = threading.Lock()
	
	for index in xrange(len(cfg)):
		if(cfg[index]['valid']== '1'):
			try:
				t = threading.Thread(target=performSearchThread, args=(queryString,loadedModules,lock,cfg[index]))
				t.start()
				threadHandles.append(t)
			except Exception as e:
				print 'Error starting thread  : ' + str(e)

	for t in threadHandles:
		t.join()
	#~ print '** All Search Threads Finished **'
	return globalResults

def performSearchThread(queryString, loadedModules, lock,cfg):
	localResults = []
	#~ print "Searching w " + cfg['type']
	for module in loadedModules:
		if( module.typesrch == cfg['type']):
			localResults = module.search(queryString, cfg)
	lock.acquire()
	globalResults.append(localResults)
	try:
		lock.release()
	except Exception as e:
		print e
 

# Exception to be raised when a search function is not implemented
class NotImplementedException(Exception):
	def __init__(self, value):
		self.value = value
	
	def __str__(self):
		return repr(self.value)

# All search modules inherit from this class
class SearchModule(object):
	# Set up class variables
	def __init__(self):
		self.name = 'Unnamed'
		self.queryURL = ''
		self.baseURL = ''
		self.nzbDownloadBaseURL = ''
		self.apiKey = ''
	# Show the configuration options for this module
	def configurationHTML(self):
		return ''
	# Perform a search using the given query string
	def search(self, queryString):
		raise NotImplementedException('This scraper does not have a search function.')