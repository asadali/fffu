import pickle
from PIL import Image
from StringIO import StringIO
import tempfile
import struct
import flickrapi
import xml.etree.cElementTree as ET
from xml.etree.ElementTree import Element, SubElement, ElementTree
from xml.dom import minidom
import os
import sys
from glob import glob
import difflib
import urllib

from lxml import etree

# favorite_color = { "lion": "yellow", "kitty": "red" }
# pickle.dump( favorite_color, open( "save.p", "wb" ) )
def clump(l, n):
    """Clump a list into groups of length n (the last group may be shorter than n)"""
    return [l[i:i + n] for i in range(0, len(l), n)]

def data_to_png(bytes):
    """Encode a byte buffer as a png, where the buffer is 8 bytes of the data length, then the data"""
    print ("data_to_png")
    length = struct.pack('L', len(bytes))
    clumps = clump(length + bytes, 3)
    # pad last list out to 3 elements
    clumps[-1] += "\x00\x00"
    clumps[-1] = clumps[-1][:3]
    clumps = map(lambda t: tuple(map(ord, t)), clumps)
    # create img
    img = Image.new('RGB', (len(clumps), 1))
    img.putdata(map(tuple, clumps))
    (width, height) = img.size
    print width
    print height
    return img

def png_to_data(imgdata):
    print ("png_to_data")
    img = Image.open(StringIO(imgdata))
    bytes = sum(list(img.getdata()), ())
    length, data = ''.join(map(chr, bytes[:8])), bytes[8:]
    return ''.join(map(chr, data[:struct.unpack('L', length)[0]]))

api_key      = '496f02eaab89d5b4dd5651a51fcb68bd'
api_secret   = '768e8faf9d827aad'
api_token    = '72157652063976241-07f9b09c99760c7e'
flickr       = flickrapi.FlickrAPI(api_key, api_secret, token=api_token)

def atomicUpDownTest(filename):
    print '--- d2p'
    d2p(filename)

    print '--- upload'
    ret = flickr.upload(filename=filename + '.png', is_public=0, callback=callback)

    photo_id = ret.find('photoid').text
    print '--- photoid : %s' % photo_id

    photo_url = getInfoByID(photo_id)
    print '--- url : %s' % photo_url

    print '--- download'
    urllib.urlretrieve(photo_url, filename + '.flickr.png')

    print '--- delete on Flickr'
    ret = flickr.photos_delete(photo_id=photo_id)
    print ret.attrib

    print '--- p2d'
    p2d(filename+'.flickr.png')

    print '--- diff of modified'
    fromLines = open(filename+'.flickr.png', 'U').readlines()
    toLines   = open(filename+'.png', 'U').readlines()
    for line in difflib.context_diff(fromLines, toLines, fromfile=filename + '.flickr.png', tofile=filename+'.png'):
        sys.stdout.write(line) 

    print '--- starting diff of original'
    fromLines = open(filename, 'U').readlines()
    toLines   = open(filename+'.flickr.down', 'U').readlines()
    for line in difflib.context_diff(fromLines, toLines, fromfile=filename, tofile=filename+'.flickr.down'):
        sys.stdout.write(line) 

    print '--- atomicUpDownTest DONE'



def d2p(fname):
    """takes fd of any file and appends file to dummy png and saves resulting file"""
    file(fname + '.png', 'wb').write(file('fffu.png', 'rb').read() + '\n' + file(fname, 'rb').read())
    print 'd2p done'
    # file('C','wb').write(file('A','rb').read()+file('B ','rb').read()) 

def p2d(fname):
    """takes fd of a downloaded png file and converts to original file"""
    # assuming sanitized input
    newfile = fname[:fname.rindex('.')]
    with open(fname, 'rb') as src, open(newfile + '.down', 'wb') as dest:
        contents = src.read()
        dest.write(contents[3975:])
    print 'p2d done'

def callback(progress, done):
    print 'callback'
    print progress
    print done
    print 10*'*'

def delPhotoByID(ids):
    for id in ids:
        ret = flickr.photos_delete(photo_id=id)
        print ET.tostring(ret, encoding = 'utf8')

def getInfoByID(photo_id):
    ret = flickr.photos_getInfo(photo_id=photo_id)
    # print ET.tostring(ret, encoding = 'utf8')
    photo = ret.find('photo')
    # https://farm{farm-id}.staticflickr.com/{server-id}/{id}_{o-secret}_o.(jpg|gif|png)
    farm_id   = photo.attrib['farm']
    server_id = photo.attrib['server']
    photo_id  = photo.attrib['id']
    o_secret  = photo.attrib['originalsecret']
    url       = 'https://farm%s.staticflickr.com/%s/%s_%s_o.png' % (farm_id, server_id, photo_id, o_secret)
    return url

# <rsp stat="ok">
# <photoid>17183990388</photoid>
# </rsp>

# <rsp stat="ok">
# <photoid originalsecret="e8649e3cb3" secret="3dfc14e4a4">17183990388</photoid>
# </rsp>
def replacePhoto():
    ret = flickr.replace(filename='fffu.png', photo_id='17183990388')
    print ET.tostring(ret, encoding='utf8')

def validUpload():
    fname        = 'vsfs.py.png'
    # d2p(fname)    
    # ret = flickr.upload(filename=fname + '.png', is_public=0, callback=callback)
    ret = flickr.upload(filename=fname, is_public=0)
    # ret = flickr.replace(filename=fname + '.png', photo_id='17104952349')
    # ret = flickr.photos_delete(photo_id='17104731428')
    # ret = flickr.photos_delete(photo_id='17104810970')
    # print ret
    # print ret.attrib
    # secret   = ret.find('photoid').attrib['secret']
    # o_secret = ret.find('photoid').attrib['originalsecret']

    # print secret, o_secret

    # info = flickr.photos_getInfo(photo_id='17104952349')
    
    # d = ElementTree.tostring(ret, encoding='utf8', method='xml')
    d = ET.tostring(ret, encoding='utf8')
    print d
    # print ret.attrib['stat']
    # photo = flickr.photos_getRecent(per_page='1')
    # print photo

# https://farm{farm-id}.staticflickr.com/{server-id}/{id}_{o-secret}_o.(jpg|gif|png)
# e42c0477bd 0707050a6c
# https://farm8.staticflickr.com/7719/17104952349_0707050a6c_o.png
# https://farm8.staticflickr.com/7719/17104952349_9eeec42c1c_o.png

# <?xml version='1.0' encoding='utf8'?>
# <rsp stat="ok">
# <photo dateuploaded="1430153569" farm="8" id="17104952349" isfavorite="0" license="0" media="photo" originalformat="png" originalsecret="9eeec42c1c" rotation="0" safety_level="0" secret="b700db1c74" server="7719" views="0">
#     <owner iconfarm="9" iconserver="8702" location="" nsid="68767188@N06" path_alias="" realname="" username="thundrdog" />
#     <title>vsfs.py</title>
#     <description />
#     <visibility isfamily="0" isfriend="0" ispublic="0" />
#     <dates lastupdate="1430153571" posted="1430153569" taken="2015-04-27 09:52:49" takengranularity="0" takenunknown="1" />
#     <permissions permaddmeta="2" permcomment="3" />
#     <editability canaddmeta="1" cancomment="1" />
#     <publiceditability canaddmeta="0" cancomment="1" />
#     <usage canblog="1" candownload="1" canprint="1" canshare="1" />
#     <comments>0</comments>
#     <notes />
#     <people haspeople="0" />
#     <tags />
#     <urls>
#         <url type="photopage">https://www.flickr.com/photos/68767188@N06/17104952349/</url>
#     </urls>
# </photo>
# </rsp>

def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def xmlSandbox():
    root = Element('root')
    # doc  = ET.SubElement(root, 'doc')
    # ET.SubElement(doc, 'field1', name='blah').text = 'some value1'
    # ET.SubElement(doc, 'field2', name='halb').text = 'some value2'

    one = Element('one')

    SubElement(root, 'two')
    root.append(one)
    one.text = 'just for fun'
    SubElement(one, 'abcd')
    root.append(Element("three"))

    print prettify(root)

def lxmlSandbox():
    root = etree.Element('root', owner='blah', group='belh', perm='0755')
    # if not len(root):
    #     print 'empty'

    root.append(etree.Element('child1', owner='asad'))
    root.append(etree.Element('child1'))
    child2 = etree.SubElement(root, 'child2')
    child21 = etree.SubElement(child2, 'child21')
    child3 = etree.SubElement(root, 'child3')
    child4 = etree.SubElement(root, 'child4')

    # print len(root)
    # print root[1][0].tag

    # print etree.tostring(root, pretty_print=True) 
    # root[0] = root[-1]
    print etree.tostring(root, pretty_print=True) 

    # print child21.getparent().tag
    # print len(root)
    # print root[1].getprevious().tag
    # print root[1].getnext().tag
    # print root.attrib['owner']

    # for el in root.iter():
    #     print (el.tag)

    res = root.find('.//child1')
    print res.tag
    res.tag = 'abracadabra'
    print res.tag
    print res.attrib['owner']

    # for child in root.iterchildren('*'):
    #     print child.tag

    # print
    # tree = etree.ElementTree(root)
    # print tree.getelementpath(res)    

    # print tree.find('/child2/child21').tag

def dummyFS():
   with open('fs.xml', 'r') as fs:
    tree = etree.parse(fs)
    for child in tree.getroot().iterchildren('*'):
        print child.tag

def fsyncTW(rootDir):
    for dirname, dirnames, filenames in os.walk(rootDir):
        for filename in filenames:
            filePath = os.path.join(dirname, filename)
            print filePath
            os.fsync(os.open(filePath, os.O_RDONLY))

def lxmllen():
    new_node = etree.Element('root', st_type  = 'test')
    new_node.append(etree.Element('test'))
    print etree.tostring(new_node, pretty_print=True)
    print len(new_node)


if __name__ == '__main__':
    # lxmllen()
    fsyncTW(sys.argv[1])
    # atomicUpDownTest(sys.argv[1])
    # replacePhoto()
    # ids = [ '17624666888'
    #       , '17812466085'
    #       , '17809712442'
    #       ]
    # delPhotoByID(ids)
    # getInfoByID(3)
    # validUpload()
    # lxmlSandbox()
    # dummyFS()
    # d2p('vsfs.py')
    # p2d('vsfs.py.png')