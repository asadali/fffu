import sys
import json
import urllib
import urllib2
import httplib2
import time
import urlparse
import oauth2 as oauth

class FlickrApiMethod(object):
    """Base class for Flickr API calls"""

    def __init__( self
    	        , nojsoncallback = True
    	        ,format          = 'json'
    	        ,parameters      = None):

    	app_key      = '496f02eaab89d5b4dd5651a51fcb68bd'
    	app_secret   = '768e8faf9d827aad'

    	token        = '72157649666666753-7e6d65372bc6a390'
        # newToken     = '72157652063976241-07f9b09c99760c7e'
    	token_secret = '0ba4c72a60c67d60'

        self.consumer = oauth.Consumer( key    = app_key
        	                          , secret = app_secret)
        self.token    = oauth.Token( token
        	                       , token_secret)

        if nojsoncallback:
            self.nojsoncallback = 1
        else:
            self.nojsoncallback = 0
        if not parameters:
            parameters = {}

        self.url = "https://api.flickr.com/services/rest"

        defaults = {
            'format'             : format,
            'nojsoncallback'     : self.nojsoncallback,
            'oauth_timestamp'    : str(int(time.time())),
            'oauth_nonce'        : oauth.generate_nonce(),
            'signature_method'   : "HMAC-SHA1",
            'oauth_token'        : self.token.key,
            'oauth_consumer_key' : self.consumer.key,
        }

        defaults.update(parameters)
        self.parameters = defaults

    def makeCall(self):
        self.parameters.update(self.getParameters())
        req                    = oauth.Request(method="GET", url=self.url, parameters=self.parameters)
        req['oauth_signature'] = oauth.SignatureMethod_HMAC_SHA1().sign(req,self.consumer,self.token)
        h                      = httplib2.Http(".cache")
        resp, content          = h.request(req.to_url(), "GET")
        self.content           = content
        self.json              = json.loads(content)

        if self.json["stat"] == "ok":
            return True
        else:
            return False

    def getParameters(self):
        raise NotImplementedError

class FlickrPhotosGetSizes(FlickrApiMethod):
    name ='flickr.photos.getSizes'

    def __init__(self,nojsoncallback=True,format='json',parameters=None,photo_id=None):
        FlickrApiMethod.__init__(self,nojsoncallback,format,parameters)
        self.photo_id = photo_id

    def getParameters(self):
        p ={
            'method':'flickr.photos.getSizes',
            'photo_id':self.photo_id
        }
        return p

    def writePhotos(self):
        for o in self.json["sizes"]["size"]:
            opener = urllib2.build_opener()
            page = opener.open(o["source"])
            my_picture = page.read()
            filename = o["label"].replace(' ', '_') +"_" + self.photo_id + o["source"][-4:]
            print filename
            fout = open(filename,"wb")
            fout.write(my_picture)
            fout.close()

    def postPhoto(self):
        parameters             = {
            'photo' : 'mug.jpeg',
            'title' : 'mugshot',
            'description' : 'test upload'
        }
        url                    = 'https://up.flickr.com/services/upload/'
        req                    = oauth.Request(method="POST", url=url, parameters=parameters)
        req['oauth_signature'] = oauth.SignatureMethod_HMAC_SHA1().sign(req,self.consumer,self.token)
        h                      = httplib2.Http(".cache")
        resp, content          = h.request(req.to_url(), "POST")
        self.content           = content
        print '*'*20
        print resp
        print '*'*20
        # self.json              = json.loads(content)
        # print content
        # print '*'*20
        return True
        # if self.json["stat"] == "ok":
        #     return True
        # else:
        #     return False


def getPhotoById():
    print "Please enter a photo id:",
    photoId = raw_input()
    print "Fetching Photo"

    photoSizes = FlickrPhotosGetSizes(photo_id = photoId)
    if(photoSizes.makeCall()):
        print "API Call Success! Writing Photos to Disk"
        photoSizes.writePhotos()
    else:
        print "API Call Failed"

if __name__ == '__main__':
    flick = FlickrPhotosGetSizes()
    if(flick.postPhoto()):
        print 'success'
    else:
        print 'failure'