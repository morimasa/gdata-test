
import os
import logging
from google.appengine.ext.webapp import template

import wsgiref.handlers
from google.appengine.ext import webapp
from google.appengine.api import users

import gdata.service
import gdata.photos.service
import gdata.spreadsheet.service
import gdata.alt.appengine

def getPhotolist(client,username):
	photolist=[]
	photos=None 
	#logging.info( 'user/%s' % ( username ))
	albums = client.GetUserFeed(user=username)
	for album in albums.entry:
		photos = client.GetFeed( '/data/feed/api/user/%s/albumid/%s?kind=photo' % ( username, album.gphoto_id.text))
		for photo in photos.entry:
			photolist.append( photo.media.thumbnail[2].url )
		
	return photolist

def getSSlist(gd_client,username):
	list=[]

	feeds = gd_client.GetSpreadsheetsFeed()
	for i, entry in enumulate(feeds.entry):
		if isinstance(feed, gdata.spreadsheet.SpreadsheetCellsFeed):
			list.append('cell: %s %s' % (entry.title.text, entry.content.text))
		elif isinstance(feed, gdata.spreadsheet.SpreadsheetListFeed):
			list.append('list: %s %s %s' % (i, entry.title.text, entry.content.text))
		else:
			list.append('else: %s %s' % (i, entry.title.text))
		
	return list

class MainPage(webapp.RequestHandler):
	def get(self):
		self.response.headers['Content-Type'] = 'text/html'

		user = users.get_current_user()
		template_values = {
			'user':user,
			'login':users.create_login_url(self.request.uri),
			'logout':users.create_logout_url('/')
			}
		path = os.path.join(os.path.dirname(__file__), 'index.html')
		self.response.out.write(template.render(path, template_values))

class PhotoPage(webapp.RequestHandler):
	def get(self):
		self.response.headers['Content-Type'] = 'text/html'

		user = users.get_current_user()
		if user==None:
			self.redirect(users.create_login_url(self.request.uri))
			return 

		client = gdata.photos.service.PhotosService()
		gdata.alt.appengine.run_on_appengine(client)
		gdata.service.http_request_handler = gdata.urlfetch
		photolist=getPhotolist(client,user)

		url=None
		url_linktext=None
    		if users.get_current_user(): 
			url = users.create_logout_url(self.request.uri) 
			url_linktext = 'Logout' 
		else: 
			url = users.create_login_url(self.request.uri) 
			url_linktext = 'Login'

		template_values={
				'user':user,
				'photolist': photolist,
				'url': url,
				'url_linktext': url_linktext,
			}
		path = os.path.join(os.path.dirname(__file__), 'photo.html')
		self.response.out.write(template.render(path, template_values))

class SSPage(webapp.RequestHandler):
	GD_CLIENT = None

	def __init__(self):
		if self.GD_CLIENT==None:
			self.GD_CLIENT = gdata.spreadsheet.service.SpreadsheetsService()
			gdata.alt.appengine.run_on_appengine(self.GD_CLIENT)

	def get(self):
		user = users.get_current_user()
		if user==None:
			self.redirect(users.create_login_url(self.request.uri))
			return 

		self.response.headers['Content-Type'] = 'text/html'

		token = self.request.get('token')
		if not token:
			authSubUrl = GetAuthSubUrl(self.GD_CLIENT, self.request.uri);
			logging.info( 'authSubUrl:%s' % ( authSubUrl ))
			self.response.set_status(301)
			self.response.headers['Location'] = str(authSubUrl)
			self.response.clear()
			#self.redirect(authSubUrl)
			return
		logging.info( 'token:%s' % ( token ))

		#gd_client = gdata.service.GDataService() #gdata.spreadsheet.service.SpreadsheetsService()
		#gdata.alt.appengine.run_on_appengine(gd_client)

		self.GD_CLIENT.auth_token = token
		self.GD_CLIENT.SetAuthSubToken(token)
		authsubtoken = gdata.auth.AuthSubToken(token)
		self.GD_CLIENT.UpgradeToSessionToken(authsubtoken)

		list=getSSlist(self.GD_CLIENT, user)

		path = os.path.join(os.path.dirname(__file__), 'spreadsheet.html')
		self.response.out.write(template.render(path, {'list':list}))

def GetAuthSubUrl(gd_client, next):
	scope = 'http://docs.google.com/feeds/'
	secure = False
	session = True
	#gd_client = gdata.service.GDataService()
	#gd_client = gdata.spreadsheet.service.SpreadsheetsService()
	return gd_client.GenerateAuthSubURL(next, scope, secure, session);

def main():
	application = webapp.WSGIApplication(
		[
		('/', MainPage),
		('/photo', PhotoPage),
		('/spreadsheet', SSPage)
		],
		debug=True
		)
	wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
	main()

