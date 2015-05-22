"""
fffu.py
Flickr FUSE Filesystem for User
Copyright 2015 Sayed Asad Ali <sayedasad@eng.ucsd.edu>

THIS SOFTWARE IS SUPPLIED WITHOUT WARRANTY OF ANY KIND, AND MAY BE
COPIED, MODIFIED OR DISTRIBUTED IN ANY WAY, AS LONG AS THIS NOTICE
AND ACKNOWLEDGEMENT OF AUTHORSHIP REMAIN.

"""

import datetime
import logging
import os
import sys
import errno
import flickrapi
import fs
import fs.base
import fuse
import stat
import time
import argparse
import traceback
import urllib
from fuse import FUSE, FuseOSError, Operations
from lxml import etree
try:
	from config import api_key, api_secret, api_token
except ImportError:
	# TODO make this more presentable
	print '[ERROR] create config.py file with api_key, api_secret, api_token and retry'	
	sys.exit(-1)

# temporary import
import xml.etree.cElementTree as ET

# global logging formatter for this module
# not making this a part of the FFFU class deliberately
def initLogging():
	# logformat = '%(asctime)-12s:[%(levelname)s] %(message)s'
	logformat = '[%(levelname)s] %(message)s'
	logfile = 'logs/' + datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S') + '.log'
	logging.basicConfig( level = logging.INFO
	# , filename = logfile
	, format   = logformat
	)
	formatter = logging.Formatter(logformat, '%Y-%m-%d %H:%M:%S')
	# console   = logging.StreamHandler()
	# console.setLevel(logging.DEBUG)
	# console.setFormatter(formatter)
	# logging.getLogger('').addHandler(console)

class FFFU(Operations):
	""" FFFU system object """
	def __init__(self, rootpath, mntpoint, fs_id=None):
		super(FFFU, self).__init__()

		# get the formatted logger from initLogging()	
		self.logger  = logging.getLogger('FFFU')
		self.logger.debug('init')

		# this is a magic number for now
		# represents the length of the characters in the reference PNG image
		self.png_offset = 3975

		# flag to know which mode fffu is operating in
		# True  : will sync with flickr after every file/metadata operation
		# False : local changes only
		self.online = True
		# this will come in handy for initialising
		self.mntpoint = mntpoint
		self.rootpath = rootpath
		self.fstree  = None

		#TODO search for fs.xml.png 
		# https://www.flickr.com/services/api/flickr.photos.search.html
		self.fsname     = 'fs.xml'
		self.fspath     = self._full_path(self.fsname)
		self.ref_file   = 'fffu.png'

		#TODO caching data locally
		self._cache   = {}


		# instantiate a flickrapi instance, abort if not online
		#TODO base this on online value
		self.flickr       = flickrapi.FlickrAPI(api_key, api_secret, token=api_token)
		if not self._test_echo():
			raise RuntimeError('flickr.test.echo failed - aborting mount')


		# restore mode
		# will create ./cache/fs.xml which self._load_fs_from_xml() will pick up
		if fs_id is not None:
			self._restore_fs_from_flickr(fs_id)

		# if fresh start
		# since restore has executed by now
		# absence of file indicates fresh start
		# 16877 is the decimal representaiton of 40755 in octal
		if (not os.path.exists(self.fspath)):
			# add the root node and write it to file with starting inode = 100000000
			# self._add_node when called with st_inode will add the root node!
			#TODO this is cryptic behaviour and needs to be refactored
			self._add_node('root', 16877, st_type='d', st_inode='100000000')

		# the fs.xml file should be in place by now
		# perform load
		self._load_fs_from_xml()

	def destroy(self, private_data):
		# can't sync here as the directory is unmounted and then provided
		self.logger.info('FFFU terminated')
		return

	# Filesystem methods
	# ==================

	def getattr(self, path, fh=None):
		# fffu implementation
		# TODO dig deeper into the extended attributes for '/._.'
		# extended attributes not supported for now
		# will raise ValueError: Invalid tag name u'._*'
		self.logger.debug('getattr - %s' % (path))
		curdir = self._get_dir(path)

		# dir/file entry doesn't exist
		# raise appropriate error so that mkdir does its thing
		if curdir is None:
			raise FuseOSError(errno.ENOENT)

		#TODO transition from usage of 'f' 'd' etc to numbers
		# xmld  = dict((key, int(curdir.attrib[key])) for key in curdir.attrib.keys())
		xmld  = dict((key, int(curdir.attrib[key])) for key in ('st_atime', 'st_ctime',
				'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))
		return xmld

	def access(self, path, mode):
		self.logger.debug('access')
		cur_file = self._get_dir(path)
		cur_file.attrib['st_atime'] = str(int(time.time()))
		#TODO fffu equivalent
		# full_path = self._full_path(path)
		# if not os.access(full_path, mode):
		# 	raise FuseOSError(errno.EACCES)
		return 0

	def readlink(self, path):
		self.logger.info('readlink')
		#TODO fffu equivalent
		# pathname = os.readlink(self._full_path(path))
		# if pathname.startswith("/"):
		# 	# Path name is absolute, sanitize it.
		# 	return os.path.relpath(pathname, self.rootpath)
		# else:
		# 	return pathname
		raise FuseOSError(errno.ENOSYS)

	def opendir(self, path):
		self.logger.debug('opendir')
		return 0

	def readdir(self, path, fh):
		dirs = ['.', '..']
		curdir = self._get_dir(path)
		if curdir is not None:
			for child in curdir.iterchildren('*'):
				dirs.append(child.tag)

		# this is an optimization
		# dirs.sort()
		self.logger.debug('readdir - path: %s dirs: %s' % (path, str(dirs)))
		for r in dirs:
			yield r

	def mknod(self, path, mode, dev):
		self.logger.info('mknod')
		#TODO fffu equivalent
		# rarely accessed
		# return os.mknod(self._full_path(path), mode, dev)
		raise FuseOSError(errno.ENOSYS)

	def mkdir(self, path, mode):
		# fffu initial implementation only supports mkdir -p
		self.logger.debug('mkdir %s %s'%(path, str(mode)))
		curdir = self._get_dir(path)
		if curdir is None:
			self._add_node(path, mode, st_type='d')
		return 0

	def unlink(self, path):
		self.logger.debug('unlink - %s' % path)
		# FFFU
		# first-pass just remove
		cur_file = self._get_dir(path)
		# delete copy on flickr
		if self.online:
			self.flickr.photos_delete(photo_id=cur_file.attrib['photo_id'])
		# delete local copy
		os.remove(self._full_path(cur_file.attrib['st_inode'] + '.png'))
		self._del_node(path)
		# return os.unlink(self._full_path(path))

	def rmdir(self, path):
		self.logger.debug('rmdir %s'%path)
		self._del_node(path)
		return 0

	def symlink(self, name, target):
		# this can get complex, come back to it later
		self.logger.info('symlink')
		raise FuseOSError(errno.ENOSYS)
		# return os.symlink(name, self._full_path(target))

	def link(self, target, name):
		# same as symlink
		self.logger.info('link')
		raise FuseOSError(errno.ENOSYS)
		# return os.link(self._full_path(target), self._full_path(name))


	def rename(self, old, new):
		self.logger.debug('rename %s %s' %(old, new))
		olddir = self._get_dir(old)
		olddir.getparent().remove(olddir)
		newpar = self._get_parent(new)

		#change the name
		olddir.tag = new[new.rindex('/') + 1:]
		newpar.append(olddir)
		self._save_fs_state_local()

		return 0

	def chmod(self, path, mode):
		# fffu implementation
		self.logger.debug('chmod')
		curdir = self._get_dir(path)
		self.logger.debug('chmod - cur: %s new: %s' % (curdir.attrib['st_mode'], mode))
		curdir.attrib['st_mode'] = str(mode)
		curdir.attrib['st_ctime'] = str(int(time.time()))

		self._save_fs_state_local()

		return 0

	def chown(self, path, uid, gid):
		#TODO
		self.logger.info('chown')
		curdir = self._get_dir(path)
		curdir.attrib['st_ctime'] = str(int(time.time()))
		raise FuseOSError(errno.ENOSYS)

	def utimens(self, path, times=None):
		curdir = self._get_dir(path)
		new_time = str(int(time.time()))
		self.logger.debug('utimens - path: %s new_time: %s old_time %s' % (path, new_time, curdir.attrib['st_atime']))
		curdir.attrib['st_atime'] = new_time

		self._save_fs_state_local()
		return 0

	def statfs(self, path):
		# fffu implementation
		# ideally this should let user know
		# about the space left on the flickr account
		self.logger.debug('statfs - %s rootpath: %s' % (path, self.rootpath))

		# not implementing now as it is a very frequent function call
		# ret = self.flickr.test_echo()		
		# retstr = ET.tostring(ret, encoding='utf8', method='xml')
		# print retstr

		stats = { 'f_bavail' : 0
				, 'f_bfree'  : 0
				, 'f_blocks' : 0
				, 'f_bsize'  : 0
				, 'f_avail'  : 0
				, 'f_ffree'  : 0
				, 'f_files'  : 0
				, 'f_flag'   : 0
				, 'f_frsize' : 0
				, 'f_namemax': 0
				}

		return stats

	# File methods
	# ============

	def open(self, path, flags):
		# download file
		# open file
		# if file is already downloaded just open it
		# no need to store it in a directory etc.

		cur_file = self._get_dir(path)
		full_path = self._full_path(cur_file.attrib['st_inode'] + '.png')
		self.logger.info('open - %s %s %d' % (path, full_path, flags))
		if not os.path.isfile(full_path):
			self._download_from_flickr(cur_file)
		return os.open(full_path, flags)

	def create(self, path, mode, fi=None):
		# create a local file
		# get inode number 
		# create local file in local directory
		new_node  = self._add_node(path, mode, st_type='f')
		full_path = self._full_path(new_node.attrib['st_inode'])
		tmpfile = full_path + '.png'

		# binary merge of two files
		with open(self.ref_file, 'rb') as src, open(tmpfile, 'wb') as dest:
			dest.write(src.read())

		if self.online:
			ret = self.flickr.upload(filename=tmpfile, is_public=0)
			new_node.attrib['photo_id'] = ret.find('photoid').text
			new_node.attrib['url']      = self._get_url_by_id(new_node.attrib['photo_id'])
			self.logger.info('create - path %s mode %s full_path %s url %s' % (path, mode, full_path, new_node.attrib['url']))

		self._save_fs_state_local()

		# does not need O_CREAT file should already have been created
		return os.open(full_path + '.png', os.O_WRONLY, mode)

	def read(self, path, length, offset, fh):
		self.logger.info('read - path: %s length: %s offset: %s' % (path, length, offset))
		os.lseek(fh, offset + self.png_offset, os.SEEK_SET)
		return os.read(fh, length)

	def write(self, path, buf, offset, fh):
		# self.logger.info('write - %s buf: %s' % (path, buf))
		self.logger.info('write - %s' % (path))
		os.lseek(fh, offset + self.png_offset, os.SEEK_SET)
		cur_file = self._get_dir(path)
		cur_file.attrib['st_mtime'] = str(int(time.time()))

		return os.write(fh, buf)

	def truncate(self, path, length, fh=None):
		self.logger.info('truncate - path: %s length: %s' % (path, length))
		cur_file = self._get_dir(path)
		cur_file.attrib['st_mtime'] = str(int(time.time()))
		full_path = self._full_path(cur_file.attrib['st_inode'] + '.png')
		with open(full_path, 'r+') as f:
			f.truncate(length + self.png_offset)

	def flush(self, path, fh):
		self.logger.info('flush')
		return os.fsync(fh)

	def release(self, path, fh):
		self.logger.info('release - path %s' % path)

		cur_file  = self._get_dir(path)
		cur_file.attrib['st_size'] = str(max(0, os.fstat(fh).st_size - self.png_offset))
		self._save_fs_state_local()

		return os.close(fh)

	def fsync(self, path, fdatasync, fh):
		os.fsync(fh)
		cur_file  = self._get_dir(path)

		self._replace_on_flickr(cur_file)
		self.logger.info('fsync - path: %s url: %s' % (path, cur_file.attrib['url']))
		# may be causing infinite loop
		self._save_fs_state_flickr()

		return self.flush(path, fh)

	# Helpers
	# =======
	def _full_path(self, partial):
		self.logger.debug('_full_path: %s'% partial)
		if partial.startswith("/"):
			partial = partial[1:]
		path = os.path.join(self.rootpath, partial)
		return path

	def _get_dir(self, path):
		if path == '/':
			return self.fstree.getroot()
		else:
			return self.fstree.find(path)

	def _get_parent(self, path):
		# use only if child node doesn't exist
		# else use getparent()
		# assuming / as directory separator
		parentPath = path[:path.rfind('/')]
		if parentPath == '':
			parentPath = '/'
		return self._get_dir(parentPath)

	def _test_echo(self):
		ret = self.flickr.test_echo()		
		# retstr = ET.tostring(ret, encoding='utf8', method='xml')
		# print retstr
		if ret.attrib and ret.attrib['stat'] == 'ok':
			return True
		return False

	def _restore_fs_from_flickr(self, fs_id):
		self.logger.info("RESTORE MODE")
		try:
			url       = self._get_url_by_id(fs_id)
		except Exception, e:
			self.logger.error(traceback.format_exc())
			sys.exit(-1)
		urllib.urlretrieve(url, self._full_path(self.fsname + '.down'))
		# png to data
		with open(self._full_path(self.fsname + '.down'), 'rb') as src, open(self._full_path('fs.xml'), 'wb') as dest:
			contents = src.read()
			dest.write(contents[self.png_offset:])	
		#remove fs.xml.down
		os.remove(self._full_path(self.fsname + '.down'))

	def _load_fs_from_xml(self):
		fsfile = open(self.fspath, 'r')
		self.fstree = etree.parse(fsfile)
		fsfile.close()

	def _download_from_flickr(self, cur_file):
		try:
			self.logger.info('on-demand from flickr - url : %s file : %s' % (cur_file.attrib['url'], cur_file.attrib['st_inode'] + '.png'))
			# don't rely on url, maybe outdated
			urllib.urlretrieve(self._get_url_by_id(cur_file.attrib['photo_id']), self._full_path(cur_file.attrib['st_inode'] + '.png'))
		except Exception, e:
			logging.error(traceback.format_exc())

	def _replace_on_flickr(self, cur_file):
		if self.online:
			file_name = cur_file.attrib['st_inode'] + '.png'
			photo_id  = cur_file.attrib['photo_id']
			ret = self.flickr.replace(filename=self._full_path(file_name), photo_id = photo_id)
			cur_file.attrib['url']   = self._get_url_by_id(photo_id)
		self.logger.info('replace %s' % file_name)

	def _save_fs_state_local(self):
		# save the FS locally
		with open(self.fspath, 'w') as fsfile:
			self.fstree.write(fsfile)
		# fsfile.write(etree.tostring(self.fstree, pretty_print=True))

	def _save_fs_state_flickr(self):
		# convert xml to png
		self._data_to_png(self.fspath)

		# if there is no key called 'photo_id'
		# it means that the fs.xml has never been saved!
		if (not 'photo_id' in self.fstree.getroot().attrib):
			# store the fs on flickr for the first time
			ret = self.flickr.upload(filename=self.fspath + '.png', is_public=0)
			self.fstree.getroot().attrib['photo_id'] = ret.find('photoid').text
			# storing url is meaningless for program
			# can be used to locate file in worst case
			self.fstree.getroot().attrib['url']      = self._get_url_by_id(self.fstree.getroot().attrib['photo_id'])
			self.logger.info('_store_fs photo_id %s url %s' % (self.fstree.getroot().attrib['photo_id'], self.fstree.getroot().attrib['url']))

			# save the FS locally
			fsfile = open(self.fspath, 'w')
			self.fstree.write(fsfile)
			# fsfile.write(etree.tostring(self.fstree, pretty_print=True))
			fsfile.close()
			# replace it once again on flickr
			# this way we will have the photo_id
			# the url can be constructed on the fly
			self._data_to_png(self.fspath)
			ret = self.flickr.upload(filename=self.fspath + '.png', is_public=0)

		else:
			# replace the existing fs file on flickr
			photo_id  = self.fstree.getroot().attrib['photo_id']
			ret = self.flickr.replace(filename=self.fspath + '.png', photo_id = photo_id)
			self.fstree.getroot().attrib['url']   = self._get_url_by_id(photo_id)
			# remove temporary .png
			os.remove(self.fspath + '.png')
			self.logger.info('_replace_fs photo_id %s url %s' % (self.fstree.getroot().attrib['photo_id'], self.fstree.getroot().attrib['url']))

	def _data_to_png(self, fname):
		"""takes fd of any file
		   appends file to dummy png
		   saves resulting file
		"""
		file(fname + '.png', 'wb').write(file(self.ref_file, 'rb').read() + '\n' + file(fname, 'rb').read())

	def _get_url_by_id(self, id):
		ret = self.flickr.photos_getInfo(photo_id=id)
		photo = ret.find('photo')
		# sample original url format
		# https://farm{farm-id}.staticflickr.com/{server-id}/{id}_{o-secret}_o.(jpg|gif|png)
		farm_id   = photo.attrib['farm']
		server_id = photo.attrib['server']
		photo_id  = photo.attrib['id']
		o_secret  = photo.attrib['originalsecret']
		url       = 'https://farm%s.staticflickr.com/%s/%s_%s_o.png' % (farm_id, server_id, photo_id, o_secret)
		return url

	def _get_inode(self):
		""" temporary function to return dummy inodes to create files. seed value based on rootpath"""
		cur_inode = self.fstree.getroot().attrib['st_inode']
		self.fstree.getroot().attrib['st_inode'] = str(int(cur_inode) + 1)
		return cur_inode

	def _add_node(self, path, mode, st_type=None, st_inode=None):
		self.logger.info('_add_node path: %s mode: %s st_type: %s st_inode: %s'%(path, str(mode), st_type, st_inode))

		# convert all attributes to string
		ctx = fuse.fuse_get_context()
		if st_type == 'd':
			st_size  = str(64) # standard size of directory entry
		if st_type == 'f':
			st_size = '0'
		st_mode  = str(mode)
		st_uid   = str(ctx[0])
		st_gid   = str(ctx[1])
		st_dev   = str(0)
		if(st_inode is None):
			st_inode = self._get_inode()
		st_nlink = str(0)
		st_time  = str(int(time.time()))

		# create new node in the xml tree
		new_node = etree.Element(path[path.rfind('/') + 1:], st_type  = st_type
			                                               , st_size  = st_size 
			                                               , st_mode  = st_mode 
			                                               , st_uid   = st_uid
			                                               , st_gid   = st_gid
			                                               , st_dev   = st_dev
			                                               , st_inode = st_inode
			                                               , st_nlink = st_nlink
			                                               , st_atime = st_time
			                                               , st_mtime = st_time
			                                               , st_ctime = st_time
			                                               )
		if(self.fstree):
			self.logger.debug('_add_node adding to fs path : %s', path)
			parentDir  = self._get_parent(path)
			parentDir.append(new_node)
		else:
			self.logger.debug('_add_node creating root')
			# this is the root tree
			self.fstree = etree.ElementTree(new_node)

		self._save_fs_state_local()
		return new_node

	def _del_node(self, path):
		curdir = self._get_dir(path)
		if curdir is not None:
			self.logger.debug('removing node: %s' % path)
			parentDir = self._get_parent(path)
			parentDir.remove(curdir)

		self._save_fs_state_local()
		return 0

if __name__ == '__main__':
	initLogging()

	lw = 44
	logging.info('*' * lw)
	logging.info('*' + 'FFFU (FUSE Flickr Filesystem for User)'.center(lw-2) + '*')
	logging.info('*' * lw)

	parser = argparse.ArgumentParser()
	parser.add_argument('-i' , '--init'          , help='initialize FFFU', action='store_true', default=False)
	parser.add_argument('-fr', '--flickr-restore', help='restore a filesystem from Flickr by providing the fs.xml photo_id', type=int)
	parser.add_argument('mountpoint'             , help='mountpoint for FFFU')
	parser.add_argument('cache'                  , help='local file store point')
	args = parser.parse_args()

	# check if mountpoint is a valid directory
	if not os.path.isdir(args.mountpoint):
		logging.error('Invalid mountpoint (not a directory)')
		sys.exit(-1)

	# check if cache is directory
	if not os.path.isdir(args.cache):
		logging.error('Invalid cache (not a directory)')
		sys.exit(-1)

	# everything went well. starting FFFU	
	# TODO print usage data
	logging.info('Starting FFFU')
	try:
		FUSE(FFFU(args.cache, args.mountpoint, args.flickr_restore), args.mountpoint, foreground=True)
	except Exception, e:
		logging.error(traceback.format_exc())
		sys.exit(-1)