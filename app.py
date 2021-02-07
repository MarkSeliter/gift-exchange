import sqlite3
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from tempfile import mkdtemp

from helper import login_required, check_email, db

# configure the a flask app
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """The main page (supposed to show only if logged in)"""

    if request.method == "POST":

        # meaning the user wants to change the theme
        # if the html was manipulated
        if request.form.get("toggle_darkmode"):
            darkmode = int(request.form.get("toggle_darkmode").strip())
            if darkmode < 0 or darkmode > 1:
                return redirect("/")

            # now that everything checks out
            db("UPDATE users SET darkmode = {} WHERE id ={}"\
                .format(darkmode, session['user_id']))

            return redirect("/")

        # if it was a request to change pic
        # also checks if its empty (manipulated)
        if request.form.get("change_pp"):
            rows = db("SELECT * FROM users WHERE id = {}".format(session['user_id']))
            image = rows[0]["image_id"]
            change = int(request.form.get("change_pp").strip())
            # left arrow
            if change == -1 :
                if image == 1:
                    image = 22
                else:
                    image -= 1
            # right arrow
            elif change == 1:
                if image == 22:
                    image = 1
                else:
                    image += 1

            db("UPDATE users SET image_id = {} WHERE id ={}"\
                .format(image, session['user_id']))

            return redirect("/")

        return redirect("/")

    # request to see your own profile
    rows = db("SELECT * FROM users WHERE id = {}".format(session['user_id']))
    username = rows[0]['username']
    image = rows[0]['image_id']
    darkmode = rows[0]['darkmode']

    rows = db("SELECT * FROM friends WHERE user_id = {}".format(session['user_id']))
    
    if not rows:
        friend_num = 0
    else:
        friend_num = len(rows)

    return render_template("index.html", username=username,\
        image=image, friend_num=friend_num, darkmode=darkmode)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if request.form.get("username") == "":
            flash("Must provide username")
            return render_template("login.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("must provide password")
            return render_template("login.html")

        # Query database for username
        rows = db("SELECT * FROM users WHERE username = '{}'".format(request.form.get("username")))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("invalid username and/or password")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    return render_template("login.html")


@app.route("/logout")
def logout():
    """logs user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # if its a post method (send the server the register data)
    if request.method == "POST":

        # checks if username is empty
        if request.form.get("username") == "":
            flash("Must provide username")
            return redirect("/register")

        # Checks if username already exists
        rows = db("SELECT * FROM users WHERE username = '{}'".format(request.form.get("username")))
        if len(rows) != 0:
            flash("Sorry, that '{}' is already taken".formant(request.form.get("username")))
            return redirect("/register")


        # Checks if email is empty
        if request.form.get("email") == "":
            flash("Must provide email")
            return redirect("/register")

        # Checks if email is valid
        if not check_email(request.form.get("email")):
            flash("Email is invalid")
            return redirect("/register")

        # checks if password is empty
        if request.form.get("password1") == "":
            flash("Must provide password")
            return redirect("/register")

        # checks if user repeated the password
        if request.form.get("password2") == "":
            flash("Must repeat password")
            return redirect("/register")

        # chekcs if both passwords match
        if request.form.get("password1") != request.form.get("password2"):
            flash("Password and Repeat password do not match")
            return redirect("/register")

        # now that everything checks out that we can insert into the database
        db("INSERT INTO users (username, hash, email) VALUES ('{}', '{}', '{}')".format(\
            request.form.get("username"), \
            generate_password_hash(request.form.get("password1")), \
            request.form.get("email")\
            ))

        # to improve user experience it logs in the user right after registering
        rows = db("SELECT * FROM users WHERE username = '{}'".format(request.form.get("username")))
        session["user_id"] = rows[0]["id"]
        flash("You've registered successfully!")
        return redirect("/")

    # if its a get method (load the register page to register)
    return render_template("register.html")


@app.route("/friends", methods=["GET", "POST"])
@login_required
def friends():
    """Lists all your friends and firend requests"""

    rows = db("SELECT * FROM users WHERE id = {}".format(session['user_id']))
    darkmode = rows[0]['darkmode']
    rows = db("SELECT * FROM friends WHERE user_id = {}".format(session['user_id']))

    friends = []

    for row in rows:
        look = db("SELECT * FROM users WHERE id = '{}'".format(row['friend_id']))
        
        friend = {
        'username': look[0]['username'],
        'image_id': look[0]['image_id'],
        }
        friends.append(friend)

    friends.sort()
    
    return render_template("friends.html",friends=friends, darkmode=darkmode)