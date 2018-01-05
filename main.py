#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import jinja2

import os
import logging

JINJA_ENVIRONMENT = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

import urllib, urllib2, webbrowser, json, time, datetime

#API PROCESSING CODE
apikey = "AIzaSyBw0xtOFShx-54KAXtw1R3evmxu67XHPkM"
monthArray = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

def jsonToDict(myPage):
    if(myPage == None):
        return None
    return json.load(myPage)

def pretty(obj):
    print json.dumps(obj, sort_keys=True, indent=2)


def safeGet(url):
    try:
        return urllib2.urlopen(url)
    except urllib2.HTTPError, e:
        print "The server couldn't fulfill the request." 
        print "Error code: ", e.code
    except urllib2.URLError, e:
        print "We failed to reach a server"
        print "Reason: ", e.reason
    return None

def addressToGeo(location):
    params = {}
    baseurl = "https://maps.googleapis.com/maps/api/geocode/json"
    params["address"] = location
    params["key"] = apikey
    url = baseurl + "?" + urllib.urlencode(params)
    geolocation = jsonToDict(safeGet(url))
    if(geolocation is None):
        return None
    elif(geolocation["status"] == "OK"):
        return geolocation["results"][0]["geometry"]["location"]
    return None
    
    
def getTimeZone(latitude, longitude, date = time.time()):
    params = {}
    baseurl = "https://maps.googleapis.com/maps/api/timezone/json"
    params["location"] = str(latitude) + "," + str(longitude)
    params["timestamp"] = date
    params["key"] = apikey
    url = baseurl + "?" + urllib.urlencode(params)
    return jsonToDict(safeGet(url))

def getInfo(user, location, date = time.time()):
    geo = addressToGeo(location)
    info = {}
    info["user"] = user
    info["location"] = location
    if(geo is None):
        info["status"] = "lost"
    else:
        zoneInfo = getTimeZone(geo["lat"], geo["lng"], date)
        info["status"] = "found"
        info["daylight"] = zoneInfo["dstOffset"]
        info["main"] = zoneInfo["rawOffset"]
        info["date"] = date + info["daylight"] + info["main"]
        info["local"] = datetime.datetime.fromtimestamp(info["date"])
        info["format"] = formatDate(info["local"])
        #pretty(zoneInfo)
    return info
#END API PROCESSING CODE
def setupTime(req):
    when = {}
    when["year"] = req.get("year")
    when["month"] = req.get("month")
    when["day"] = req.get("day")
    when["hour"] = req.get("hour")
    when["minute"] = req.get("minute")
    return when

def setStamp(loc, tstamp):
    zone = getInfo("REFERNCE", loc, tstamp)
    if(zone["status"] is "lost"):
        return None
    utctime = tstamp - (zone["main"] + zone["daylight"])
    return utctime
    
def formatDate(stamp):
    f = {}
    f["time"] = str(stamp.hour) + ":" + twoDigit(stamp.minute)
    f["date"] = twoDigit(stamp.day) + " " + monthArray[stamp.month-1] + " " + str(stamp.year)
    return f

def twoDigit(x):
    if(x < 10):
        return "0" + str(x)
    return str(x)
    
class MainHandler(webapp2.RequestHandler):
    def get(self):
        logging.info("In MainHandler")
        vals={}
        template = JINJA_ENVIRONMENT.get_template('form.html')
        self.response.write(template.render(vals))
        
class ZappResponseHandler(webapp2.RequestHandler):
    def post(self):
        vals = {}
        req = self.request
        page = 'response.html'
        timeInfo = setupTime(req)
        t = {}
        for key in timeInfo.keys():
            t[key] = int(timeInfo[key])
        timeInfo["month"] = monthArray[t["month"] - 1]
        tstamp = time.time()
        vals['message'] = []
        try:
            tstamp = time.mktime(datetime.datetime(t["year"], t["month"], t["day"], t["hour"], t["minute"]).utctimetuple())
        except:
            vals['message'].append("The Date You Have Entered is Not Valid")
            page = 'error.html'
        
        ref = req.get("reference")
        if(ref == ""):
            vals['message'].append("Please Select A Reference Location")
        else:
            ref = int(ref)
        
        vals['t'] = timeInfo
        users = req.get_all("user")
        addresses = req.get_all("address")

        if(len(addresses) > 0):
            refstamp = None
            if(ref != ""):
                vals['reference'] = addresses[ref]
                refstamp = setStamp(vals['reference'], tstamp)
            if(refstamp is None):
                page = 'error.html'
                if(ref != ""):
                    vals['message'].append("We Could Not Find The Reference Location")
            else:
                user_input = dict(zip(users, addresses))
                offsets = [getInfo(x, user_input[x], refstamp) for x in user_input.keys()]
                offsets.sort(key = lambda x : users.index(x["user"]))
                vals['input'] = offsets
                
        else:
            page = 'error.html'
            vals['message'].append("Please Enter At Least One Location")
        template = JINJA_ENVIRONMENT.get_template(page)
        self.response.write(template.render(vals))

# for all URLs except alt.html, use MainHandler
application = webapp2.WSGIApplication([ \
                                      ('/response', ZappResponseHandler),
                                      ('/.*', MainHandler)
                                      ],
                                     debug=True)
