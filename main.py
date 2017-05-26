import logging
import cgi
import os
import urllib

from flask import Flask, render_template, request, redirect, Response, make_response
from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.api import images


app = Flask(__name__)


# [START model]
class Greeting(ndb.Model):
    """Models a Guestbook entry with an author, content, avatar, and date."""
    author = ndb.StringProperty()
    content = ndb.TextProperty()
    avatar = ndb.BlobProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
# [END model]

def guestbook_key(guestbook_name=None):
    """Constructs a Datastore key for a Guestbook entity with name."""
    return ndb.Key('Guestbook', guestbook_name or 'default_guestbook')


@app.route('/')
def home():
    guestbook_name = request.args.get('guestbook_name')
    greetings = Greeting.query(
        ancestor=guestbook_key(guestbook_name)) \
        .order(-Greeting.date) \
        .fetch(10)

    user = users.get_current_user()
    if user:
        url = users.create_logout_url(request.url)
        url_linktext = 'Logout'
    else:
        url = users.create_login_url(request.url)
        url_linktext = 'Login'

    return render_template('index.html', user=user, url=url, url_linktext=url_linktext, guestbook_name=guestbook_name, greetings=greetings, form_url="/sign?{}".format(urllib.urlencode({'guestbook_name': guestbook_name})))


@app.route("/sign", methods=['post'])
def sign():
    guestbook_name = request.args.get('guestbook_name')
    greeting = Greeting(parent=guestbook_key(guestbook_name))

    if users.get_current_user():
        greeting.author = users.get_current_user().nickname()
        greeting.content = request.form.get('content')
        uploaded_file = request.files.get('img')
        image_data = uploaded_file.stream.read()
        avatar = images.resize(image_data, 32, 32)
        greeting.avatar = avatar
        greeting.put()
        return redirect('/?' + urllib.urlencode(
            {'guestbook_name': guestbook_name}))


@app.route('/img')
def display_image():
    greeting_key = ndb.Key(urlsafe=request.args.get('img_id'))
    greeting = greeting_key.get()
    if greeting.avatar:
        response = make_response(greeting.avatar)
        response.headers['Content-Type'] = 'image/png'
        return response
    else:
        return make_response('No image')


@app.errorhandler(500)
def server_error(e):
    # Log the error and stacktrace
    logging.exception('An error occured during a request.')
    return 'An internal error occurred.', 500
