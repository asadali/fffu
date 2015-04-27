#!/usr/bin/python

import sys
import json
import urllib
import urllib2
import httplib2
import time
import urlparse
import oauth2 as oauth

print ""
print 'x'*40
print "x Flickr Access Token Script x"
print 'x'*40
print ""

# flickrfs
# Key    : 496f02eaab89d5b4dd5651a51fcb68bd
# Secret : 768e8faf9d827aad
# app_key       = raw_input("1.) Enter your 'App key': ").strip()
# app_secret    = raw_input("2.) Enter your 'App secret': ").strip()
app_key       = '496f02eaab89d5b4dd5651a51fcb68bd'
app_secret    = '768e8faf9d827aad'

url           = "https://www.flickr.com/services/oauth/request_token"
params = {
  'oauth_nonce'            : oauth.generate_nonce(),
  'oauth_timestamp'        : str(int(time.time())),
  'oauth_consumer_key'     : app_key,
  'oauth_signature_method' : "HMAC-SHA1",
  'oauth_version'          : "1.0",
  'oauth_callback'         : "http://localhost"
}

consumer = oauth.Consumer( key   =app_key
                         , secret=app_secret)

# Create our request. Change method, etc. accordingly.
req = oauth.Request(method="GET", url=url, parameters=params)

# Create the signature
signature = oauth.SignatureMethod_HMAC_SHA1().sign(req, consumer, None)

# Add the Signature to the request
req['oauth_signature'] = signature

# Make the request to get the oauth_token and the oauth_token_secret
# I had to directly use the httplib2 here, instead of the oauth library.
h = httplib2.Http(".cache")
resp, result = h.request(req.to_url(), "GET")

# authorize_url = url + "?response_type=code&client_id=" + app_key

# print "3.) Now open this url and confirm the requested permission."
# print ""
# print authorize_url
# print ""
# code = raw_input("4.) Enter the given access code': ").strip()

authorize_url = "http://www.flickr.com/services/oauth/authorize"

request_token = dict(urlparse.parse_qsl(result))

print "Request Token:"
print "    - oauth_token        = %s" % request_token['oauth_token']
print "    - oauth_token_secret = %s" % request_token['oauth_token_secret']
print

# Create the token object with returned oauth_token and oauth_token_secret
token = oauth.Token( request_token['oauth_token']
                   , request_token['oauth_token_secret'])

# You need to authorize this app via your browser.
print "Go to the following link in your browser:"
print "%s?oauth_token=%s&perms=delete" % ( authorize_url
                                        , request_token['oauth_token'])
print

# Once you get the verified pin, input it
accepted = 'n'
while accepted.lower() == 'n':
    accepted = raw_input('Have you authorized me? (y/n) ')
oauth_verifier = raw_input('What is the PIN? ')

#set the oauth_verifier token
token.set_verifier(oauth_verifier)
# url to get access token
access_token_url = "http://www.flickr.com/services/oauth/access_token"

# Now you need to exchange your Request Token for an Access Token
# Set the base oauth_* parameters along with any other parameters required
# for the API call.
access_token_parms = {
  'oauth_consumer_key': app_key,
  'oauth_nonce': oauth.generate_nonce(),
  'oauth_signature_method':"HMAC-SHA1",
  'oauth_timestamp': str(int(time.time())),
  'oauth_token':request_token['oauth_token'],
  'oauth_verifier' : oauth_verifier
}

#setup request
req = oauth.Request(method="GET", url=access_token_url,
  parameters=access_token_parms)

#create the signature
signature = oauth.SignatureMethod_HMAC_SHA1().sign(req,consumer,token)

# assign the signature to the request
req['oauth_signature'] = signature

#make the request
h = httplib2.Http(".cache")
resp, content = h.request(req.to_url(), "GET")

#parse the response
access_token_resp = dict(urlparse.parse_qsl(content))

#write out a file with the oauth_token and oauth_token_secret
with open('token', 'w') as f:
  f.write(access_token_resp['oauth_token'] + '\n')
  f.write(access_token_resp['oauth_token_secret'])
f.closed