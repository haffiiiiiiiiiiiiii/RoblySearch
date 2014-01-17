"""
Name 			: Robbie Lynch

Student Number 	: C00151101

"""
from flask import Flask, request, send_file, abort, make_response, session, escape, url_for, redirect, render_template
from functools import wraps
import logging
from mymongo import MyMongo
import bson
from robcrawler import get_website_object, get_html
from website import Website


#Constants
_PORT = 9200
_HOST = '0.0.0.0'
_DEBUG = True

APP_NAME = "robbiesearch"

webapp = Flask(__name__)


def check_loggied_in(func):
    @wraps(func)
    def wrapped_function(*args, **kwargs):
        if 'logged-in' in session:
            return func(*args, **kwargs)
        else:
            return redirect(url_for('login'))

    return wrapped_function


@webapp.route('/')
@check_loggied_in
def root():
    return render_template('index.html', title=APP_NAME, stylesheet='main.css')


@webapp.route('/index')
@check_loggied_in
def index():
    return render_template('index.html', title=APP_NAME, stylesheet='main.css')


@webapp.route('/signup')
def signup():
    """
    Displays the signup form for potential new users.
    """
    return render_template('signup.html', title="Sign Up", stylesheet="main.css")


@webapp.route('/login', methods=["GET", "POST"])
def login():
    """
    Displays the login form for potential new users.
    """
    if request.method == "GET":
        return render_template('login.html', title="Login", stylesheet="main.css")
    else:
        mongo = MyMongo()
        email = request.form['email']
        password = request.form['password']
        user = mongo.read_user(email, password)
        if user:
            session['logged-in'] = True
            session['username'] = user.__getitem__("name")
            session['useremail'] = user.__getitem__("email")
            return redirect(url_for('index'))
        else:
            return "User not found"


@webapp.route('/logout')
@check_loggied_in
def logout():
    """
    Logs users out. Deletes the current session.
    Returns:
        Redirect - redirects to the login page.
    """
    session.pop('logged-in', None)
    session.pop('useremail', None)
    session.pop('username', None)
    return redirect(url_for('login'))


@webapp.route('/create_new_user', methods=["POST"])
def create_new_user():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    mongo = MyMongo()
    if mongo.create_user(name, email, password):
        return "User created successfully"
    else:
        return "User not created"


def is_empty(any_structure):
    """
    Simple helper function to help determin if a data
    structure is empty.
    Parameters:
        Object - Any object
    Returns:
        True - if the object is empty
        False - if the object is not empty
    """
    if any_structure:
        return False
    else:
        return True


@webapp.route('/crawlall')
def crawlall():
    website = get_website_object("http://roblynch.info")
    output = test_website_contents(website)
    return output


def test_website_contents(website):
    string = ""
    string += "URL = " + website.url
    string += "<br />Title = " + website.title
    string += "<br />=============================LINKS===============================================<br />"
    for link in website.links:
        string += link
        string += "<br />"
    string += "<br />==============================END LINKS==========================================<br />"
    string += "<br />=============================IMAGES===============================================<br />"
    for img in website.images:
        string += img
        string += "<br />"
    string += "<br />==============================END IMAGES==========================================<br />"
    return string


#If it's run directly by the python web system, start it
if __name__ == '__main__':
    #the secret key to encrypt and decrypt cookies
    webapp.secret_key = b'_0\xa5L\x0e\xd3"f\xfe\xbb\x07\xee\xebB?@\xaf.\xa6\xf0\xec\x19\x92\x95\xe6\xb2\xb4\xd1[ \xfad\x8bh\x93\xbf<b\xa5\xccV\xa4$%K4\xa8\xc4'
    webapp.run(host=_HOST, debug=_DEBUG, port=_PORT)
    #We do that because if we use app engine or tornado server
    #it calls it automatically, and uses different ports and namespaces