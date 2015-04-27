import pickle
from PIL import Image
from StringIO import StringIO
import tempfile
import struct
import flickrapi
import xml.etree.cElementTree as ET
from xml.etree.ElementTree import Element, SubElement, ElementTree
from xml.dom import minidom

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

def upload():
	with open('save.p') as f:
		data = f.read()
		data_to_png(data).save('mug.png', 'png')
	with open('mug.png') as f:
		data = f.read()
		imgData = png_to_data(data)
		with open('ss.p', 'w') as m:
			m.write(imgData)

def d2p(fname):
    """takes fd of any file and appends file to dummy png and saves resulting file"""
    file(fname + '.png', 'wb').write(file('fffu.png', 'rb').read() + '\n' + file(fname, 'rb').read())
    # file('C','wb').write(file('A','rb').read()+file('B ','rb').read()) 

def p2d(fname):
    """takes fd of a downloaded png file and converts to original file"""
    # assuming sanitized input
    newfile = fname[:fname.rindex('.')]
    with open(fname, 'rb') as src, open(newfile + '.down', 'wb') as dest:
        contents = src.read()
        print contents.index('usr')
        dest.write(contents[3975:])
    print 'p2d done'

def callback(progress, done):
    print 'callback'
    print progress
    print done
    print 10*'*'

def validUpload():
    api_key      = '496f02eaab89d5b4dd5651a51fcb68bd'
    api_secret   = '768e8faf9d827aad'
    api_token    = '72157652063976241-07f9b09c99760c7e'
    fname        = 'vsfs.py'
    d2p(fname)    
    flickr       = flickrapi.FlickrAPI(api_key, api_secret, token=api_token)
    # ret          = flickr.test_echo()
    ret = flickr.upload(filename=fname + '.png', is_public=0, callback=callback)
    print ret
    print ret.attrib
    photoid = ret.find('photoid').text
    
    # d = ElementTree.tostring(ret, encoding='utf8', method='xml')
    d = ET.tostring(ret, encoding='utf8')
    print d
    # print ret.attrib['stat']
    # photo = flickr.photos_getRecent(per_page='1')
    # print photo

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

if __name__ == '__main__':
    validUpload()
    # lxmlSandbox()
    # dummyFS()
    # d2p('vsfs.py')
    # p2d('vsfs.py.png')