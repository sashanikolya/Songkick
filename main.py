import StringIO
import json
import logging
import random
import urllib
import urllib2

from urlparse import urlparse
from pprint import pprint

# for sending images
#from PIL import Image
import multipart

# standard app engine imports
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
import webapp2

TOKEN = "117744366:AAGQYDZ579RQZp6tDgSHPlRFmQv6b3cD_AA"




SONGKICK_API_KEY = "YQ9Q3t1i1HDQHuTY"


BASE_URL = 'https://api.telegram.org/bot' + TOKEN + '/'


#Search for artists's id in Songkick's website.
def search_for_artist_id(search_query):
    o = urllib.urlopen("http://api.songkick.com/api/3.0/search/artists.json?query=" + search_query + "&apikey=" + SONGKICK_API_KEY)
    page = json.loads(o.read())
    a = page.values()
    b = a[0][u'results']
    c = b[u'artist']
    result = c[0][u'id']
    return result

#Receiveing information about certain artist's upcoming events.
def parse_artists_page(artist_id):
    artist_id = str(artist_id)
    o = urllib.urlopen("https://api.songkick.com/api/3.0/artists/" + artist_id + "/calendar.json?apikey=" + SONGKICK_API_KEY)
    page = json.loads(o.read())
    result = {}
    a = page.values()
    b = a[0][u'results']
    c = b[u'event']
    for i in range(0, len(c)):
        try:
            result.setdefault(i, {})
            result[i]['event'] = c[i][u'displayName']
            result[i]['location'] = c[i][u'location'][u'city']
            result[i]['start'] = c[i][u'start'][u'date']
            result[i]['end'] = c[i][u'end'][u'date']
            result[i]['status'] = c[i][u'status']
            result[i]['link'] = c[i][u'uri']
        except KeyError:
            continue
    return result




# ================================

class EnableStatus(ndb.Model):
    # key name: str(chat_id)
    enabled = ndb.BooleanProperty(indexed=False, default=False)


# ================================

def setEnabled(chat_id, yes):
    es = EnableStatus.get_or_insert(str(chat_id))
    es.enabled = yes
    es.put()

def getEnabled(chat_id):
    es = EnableStatus.get_by_id(str(chat_id))
    if es:
        return es.enabled
    return False


# ================================

class MeHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getMe'))))


class GetUpdatesHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getUpdates'))))


class SetWebhookHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        url = self.request.get('url')
        if url:
            self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'setWebhook', urllib.urlencode({'url': url})))))


class WebhookHandler(webapp2.RequestHandler):
    def post(self):
        urlfetch.set_default_fetch_deadline(60)
        body = json.loads(self.request.body)
        logging.info('request body:')
        logging.info(body)
        self.response.write(json.dumps(body))

        update_id = body['update_id']
        message = body['message']
        message_id = message.get('message_id')
        date = message.get('date')
        text = message.get('text')
        fr = message.get('from')
        chat = message['chat']
        chat_id = chat['id']

        if not text:
            logging.info('no text')
            return

        def reply(msg=None, img=None):
            if msg:
                resp = urllib2.urlopen(BASE_URL + 'sendMessage', urllib.urlencode({
                    'chat_id': str(chat_id),
                    'text': msg.encode('utf-8'),
                    'disable_web_page_preview': 'true',
                })).read()
            elif img:
                resp = multipart.post_multipart(BASE_URL + 'sendPhoto', [
                    ('chat_id', str(chat_id)),
                    ('reply_to_message_id', str(message_id)),
                ], [
                    ('photo', 'image.jpg', img),
                ])
            else:
                logging.error('no msg or img specified')
                resp = None

            logging.info('send response:')
            logging.info(resp)

        if text.startswith('/'):
            if text == '/start':
                reply('Bot enabled')
                setEnabled(chat_id, True)
            elif text == '/stop':
                reply('Bot disabled')
                setEnabled(chat_id, False)
            #elif text == '/image':
                #img = Image.new('RGB', (512, 512))
                #base = random.randint(0, 16777216)
                #pixels = [base+i*j for i in range(512) for j in range(512)]  # generate sample image
                #img.putdata(pixels)
                #output = StringIO.StringIO()
                #img.save(output, 'JPEG')
                #reply(img=output.getvalue())
            else:
                reply('What command?')

        # CUSTOMIZE FROM HERE

        elif 'who are you' in text:
            reply('bot created by @annikolaev')
        #elif 'Kasabian' in text:
            #aaaaa = parse_artists_page(search_for_artist_id('Kasabian'))[0]
            #bbbbb = aaaaa['start'] + '\n' + aaaaa['event'] + '\n' + aaaaa['location']
            #reply(str(bbbbb))
        elif 'what time' in text:
            reply('look at the top-right corner of your screen!')
        else:
            rezult = "Hey, you. Here\'s %s\'s upcoming events!\n\n" %text.encode("UTF-8")
            try:
                answer = parse_artists_page(search_for_artist_id(text.encode("UTF-8")))
                for indx in range(0, len(answer.keys())):
                    try:
                        rezult += answer[indx]['start'] + '\n' + answer[indx]['event'] + '\n' + answer[indx]['location'] + '\n\n'
                    except (KeyError, UnicodeDecodeError, urllib2.HTTPError):
                        break
                reply(rezult)
        
            except (KeyError, UnicodeDecodeError, urllib2.HTTPError, ):
                reply('I have no idea what are you talking about. Enter a band\'s name.')
        



app = webapp2.WSGIApplication([
    ('/me', MeHandler),
    ('/updates', GetUpdatesHandler),
    ('/set_webhook', SetWebhookHandler),
    ('/webhook', WebhookHandler),
], debug=True)
