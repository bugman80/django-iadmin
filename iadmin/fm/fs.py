#
from datetime import datetime
from exceptions import OSError
from grp import getgrgid
import mimetypes
from pwd import getpwuid
from django import http
from django.core.urlresolvers import reverse
import os
from iadmin.fm import utils

__author__ = 'sax'


CONFIG = utils.get_fm_config()
ROOT_NAME = ''
perms = ['---', '--x', '-w-', '-wx', 'r--', 'r-x', 'rw-', 'rwx']

class FileSystemObject(object):
    checks = [os.path.exists]

    def __init__(self, fullpath, owner=None):
        for check in self.checks:
            if not check( fullpath):
                raise http.Http404

        self.name = self.basename = os.path.basename(fullpath) or ROOT_NAME
        self.parent = os.path.dirname(fullpath)

        self.absolute_path = fullpath # file system absolute path
        self.relative_path = utils.relpath(fullpath, utils.get_document_root())
        #        self.absolute_url = reverse('admin:iadmin.fm.index', kwargs={'path': self.relative_path})

        self.path = self.relative_path.split('/')
        #        #        self.url = utils.relpath(utils.get_document_root(),  )
        #        #        self.relative_path = os.path.join(owner.relative_path, name)
        #        #        self.absolute_path = os.path.join(utils.get_document_root(), self.relative_path)
        self.mime = mimetypes.guess_type(self.absolute_path, False)[0] or ''
        self.can_read = os.access(self.absolute_path, os.R_OK)
        self.can_write = os.access(self.absolute_path, os.W_OK)
        self.is_link = os.path.islink(self.absolute_path)
        try:
            itemstat = os.stat(self.absolute_path)
            self.user = getpwuid(itemstat.st_uid)[0]
            self.group = getgrgid(itemstat.st_gid)[0]
            self.size = itemstat.st_size
            self.ctime = datetime.fromtimestamp(itemstat.st_ctime)
            self.mtime = datetime.fromtimestamp(itemstat.st_mtime)
            octs = "%04d" % int(oct(itemstat.st_mode & 0777))
            self.perms_numeric = octs
            self.perms = "%s%s%s" % (perms[int(octs[1])],
                                     perms[int(octs[2])],
                                     perms[int(octs[3])])
        except:
            self.user = self.group = self.perms_numeric = self.perms = ''
            self.size = self.ctime = self.mtime = None

    @property
    def absolute_url(self):
        return reverse('admin:iadmin.fm.index', kwargs={'path': self.relative_path})

    def get_absolute_url(self):
        return self.absolute_url
    
    @property
    def hidden(self):
        return self.name[0] == '.'

    def __repr__(self):
        return self.absolute_path

class Dir(FileSystemObject):
    is_directory = True
    can_edit = False
    checks = [os.path.isdir]

    def _scan(self):
    #        if not CONFIG['show'](self):
    #            raise http.Http404
        try:
            return os.listdir(self.absolute_path)
        except OSError:
            raise http.Http404

    def get_file(self, name):
        fullpath = os.path.join( self.absolute_path, name)
        return File( fullpath)

    @property
    def files(self):
        _files = []
        listing = self._scan()
        for entry in listing:
            filesystem_path = os.path.join(self.absolute_path, entry)
            if os.path.isdir(filesystem_path):
                item = Dir(os.path.join(self.absolute_path, entry), self)
            else:
                item = File(os.path.join(self.absolute_path, entry), self)
            if CONFIG['show'](item):
                _files.append(item)
        _files.sort()
        return _files

    @property
    def url(self):
        return utils.clean_path( self.name ) + '/'


    @property
    def breadcrumbs(self):
        elements = []
        for i, el in enumerate(self.path[::-1]):
            elements.insert(0, ['/'.join(self.path[:-i]), el + '/'])
        elements.insert(0, ['', '/'])
        return elements[:-1]

    def __lt__(self, other):
        if other.is_directory:
            return self.name < other.name
        else:
            return True


class File(FileSystemObject):
    is_directory = False
    checks = [os.path.isfile]
    #    def __init__(self, owner, name):
    #        super(File, self).__init__(owner, name)
    #        self.can_edit = self.mime in ['text', ]

    @property
    def absolute_url(self):
        return reverse('admin:iadmin.fm.view', kwargs={'path': self.relative_path})

    def __lt__(self, other):
        if other.is_directory:
            return False
        else:
            return self.name < other.name

    @property
    def icon(self):
        return '%s.png' % self.mime.replace('/', '_')

    def display(self):
        if self.mime in ['image/png', ]:
            return '<a href="%s">%s</a>' % (self.fileurl, self.name)
        else:
            return '-------------'

    def __repr__(self):
        return "%s:%s" % (self.mime, self.name)
