import logging
import cgi
import os
import urllib

from flask import Flask, render_template, request, redirect, Response, make_response
from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.api import images


app = Flask(__name__)


DEFAULT_GUESTBOOK_NAME = 'default_guestbook'

# We set a parent key on the 'Greetings' to ensure that they are all
# in the same entity group. Queries across the single entity group
# will be consistent. However, the write rate should be limited to
# ~1/second.


def guestbook_key(guestbook_name=DEFAULT_GUESTBOOK_NAME):
    """Constructs a Datastore key for a Guestbook entity.
    We use guestbook_name as the key.
    """
    return ndb.Key('Guestbook', guestbook_name)

# [START greeting]


class Author(ndb.Model):
    """Sub model for representing an author."""
    identity = ndb.StringProperty(indexed=False)
    email = ndb.StringProperty(indexed=False)


class Greeting(ndb.Model):
    """A main model for representing an individual Guestbook entry."""
    author = ndb.StructuredProperty(Author)
    content = ndb.StringProperty(indexed=False)
    avatar = ndb.BlobProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
# [END greeting]


@app.route('/')
def home():
    guestbook_name = request.args.get('guestbook_name', DEFAULT_GUESTBOOK_NAME)
    greetings_query = Greeting.query(
        ancestor=guestbook_key(guestbook_name)).order(-Greeting.date)
    greetings = greetings_query.fetch(10)

    user = users.get_current_user()
    if user:
        url = users.create_logout_url(request.url)
        url_linktext = 'Logout'
    else:
        url = users.create_login_url(request.url)
        url_linktext = 'Login'
    return render_template('index.html', **{
        'user': user,
        'greetings': greetings,
        'guestbook_name': urllib.quote_plus(guestbook_name),
        'url': url,
        'url_linktext': url_linktext,
    })


@app.route('/img')
def image():
    greeting_key = ndb.Key(urlsafe=request.form.get('img_id'))
    greeting = greeting_key.get()
    if greeting.avatar:
        response = make_response(greeting.avatar)
        response.headers['Content-Type'] = 'img/png'
        return response
    else:
        return 'No image'


@app.route('/sign', methods=['POST'])
def sign():
    guestbook_name = request.form.get('guestbook_name',
                                      DEFAULT_GUESTBOOK_NAME)
    greeting = Greeting(parent=guestbook_key(guestbook_name))

    if users.get_current_user():
        greeting.author = Author(
            identity=users.get_current_user().user_id(),
            email=users.get_current_user().email())

    greeting.content = request.form.get('content')

    avatar = request.form.get('img')
    # avatar = images.resize(avatar, 32, 32)
    greeting.avatar = avatar

    greeting.put()

    query_params = {'guestbook_name': guestbook_name}
    return redirect('/?' + urllib.urlencode(query_params))


@app.errorhandler(500)
def server_error(e):
    # Log the error and stacktrace
    logging.exception('An error occured during a request.')
    return 'An internal error occurred.', 500
