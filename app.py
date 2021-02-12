from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from tempfile import mkdtemp
from random import randint

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

# for i in range(2, 10, 1):
#     db("INSERT INTO friends (user_id, friend_id) VALUES(1, {})".format(i))
#     db("INSERT INTO friends (user_id, friend_id) VALUES({}, 1)".format(i))


def dark_mode_toggler():
    """toggles darkmode for a logged in user"""

    session["dark_mode"] = session["dark_mode"] * -1
    dark_mode_new = session["dark_mode"]
    db("UPDATE users SET dark_mode = {} WHERE id ={}"\
                .format(dark_mode_new, session['user_id']))


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """The main page (supposed to show only if logged in)"""

    # user subbmited a form via post
    if request.method == "POST":

        # user used toggle_dark_mode
        if request.form.get('toggle_dark_mode'):
            dark_mode_toggler()

        # if it was a request to change pic
        if request.form.get("change_pp"):
            rows = db(f"SELECT * FROM users WHERE id = {session['user_id']}")
            image_id = rows[0]["image_id"]
            change = int(request.form.get("change_pp").strip())
            # left arrow
            if change == -1 :
                if image_id == 1:
                    image_id = 22
                else:
                    image_id -= 1
            # right arrow
            elif change == 1:
                if image_id == 22:
                    image_id = 1
                else:
                    image_id += 1
            # there was an exploit
            else:
                flash("Invalid request")
                return redirect("/")

            db(f"UPDATE users SET image_id = {image_id} \
                WHERE id ={session['user_id']}")

        return redirect("/")

    # Gets data to display in profile
    rows = db(f"SELECT * FROM users WHERE id = {session['user_id']}")
    username = rows[0]['username']
    image_id = rows[0]['image_id']
    
    return render_template("index.html", username=username,\
        image=image_id, darkmode=session["dark_mode"])


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
        rows = db(f"SELECT * FROM users WHERE \
            username = '{request.form.get('username')}'")

        # Ensure username exists and password is correct
        if len(rows) != 1 or not \
        check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("invalid username and/or password")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Remember if the users has darkmode on or off
        session["dark_mode"] = rows[0]["dark_mode"]

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
        if not request.form.get("username"):
            flash("Must provide username")
            return redirect("/register")

        # Checks if username already exists
        rows = db(f"SELECT * FROM users WHERE \
            username = '{request.form.get('username')}'")

        if len(rows) != 0:
            flash(f"Sorry, '{request.form.get('username')}' \
                is already taken")
            return redirect("/register")


        # Checks if email is empty
        if not request.form.get("email"):
            flash("Must provide email")
            return redirect("/register")

        # Checks if email is valid
        if not check_email(request.form.get("email")):
            flash("Email is invalid")
            return redirect("/register")

        # checks if password is empty
        if not request.form.get("password1"):
            flash("Must provide password")
            return redirect("/register")

        # checks if user repeated the password
        if not request.form.get("password2"):
            flash("Must repeat password")
            return redirect("/register")

        # chekcs if both passwords match
        if request.form.get("password1") != request.form.get("password2"):
            flash("Password and Repeat password do not match")
            return redirect("/register")

        # now that everything checks out that we can insert into the database
        db(f"INSERT INTO users (username, hash, email, image_id) \
            VALUES ('{request.form.get('username')}', \
            '{generate_password_hash(request.form.get('password1'))}', \
            '{request.form.get('email')}', {randint(1, 22)})")

        # to improve user experience it logs in the user right after registering
        rows = db(f"SELECT * FROM users \
            WHERE username = '{request.form.get('username')}'")
        
        # remember which user is logged in
        session["user_id"] = rows[0]["id"]

        # remember which darkmode preference the user has
        session["dark_mode"] = rows[0]["dark_mode"]
        
        flash("You've registered successfully!")
        return redirect("/")

    # if its a get method (load the register page to register)
    return render_template("register.html")


@app.route("/friends", methods=["GET", "POST"])
@login_required
def friends():
    """Lists all your friends and firend requests"""

    # if its a request to change something
    if request.method == "POST":

        # user used toggle_dark_mode
        if request.form.get('toggle_dark_mode'):
            dark_mode_toggler()
            return redirect("/friends")

        # user requested to remove a friend
        elif request.form.get("remove_friend"):

            # checks if the request is a num
            if not request.form.get("remove_friend").isnumeric():
                flash("Invalid request")
                return redirect("/friends")

            # putting the id into a variable to make it more readable
            friend_id = int(request.form.get("remove_friend"))

            # looks for user's side friendship if it exists (to avoid manipulation)
            rows = db(f"SELECT * FROM friends WHERE \
                user_id = {session['user_id']} \
                AND friend_id = {friend_id}")
            
            # if it doesnt exist in the friend table it exits
            if len(rows) == 0:
                flash("Invalid request")
                return redirect("/friends")

            # now that the request was validated it proceeds to delete
            f_u = db(f"SELECT username FROM users WHERE \
                id = '{friend_id}'")

            rows = db(f"DELETE FROM friends WHERE user_id = \
                {session['user_id']} AND friend_id = \
                {friend_id}")
            
            rows = db(f"DELETE FROM friends WHERE \
                user_id = {friend_id} \
                AND friend_id = {session['user_id']}")

            flash(f"{f_u[0]['username']} \
                was removed from the friends list")
            return redirect("/friends")

        # user requested to accept a friend request
        elif request.form.get("accept_fr"):

            # checks if the request is a num
            if not request.form.get('accept_fr').isnumeric():
                flash("Invalid request")
                return redirect("/friends")

            # put the id into a var to make the code readable
            friend_id = int(request.form.get('accept_fr'))

            # checking if friend request exists
            rows = db(f"SELECT * FROM friend_req WHERE \
                sender_id = {friend_id} AND \
                reciever_id = {session['user_id']}")

            # if the request doesnt exist it returns
            if len(rows) != 0:

                # put info in the user's friend list
                db(f"INSERT INTO friends (user_id, friend_id) \
                    VALUES ({session['user_id']}, {friend_id})")

                # put info in the friend's friend list
                db(f"INSERT INTO friends (user_id, friend_id) \
                    VALUES ({friend_id}, {session['user_id']})")

                # deleting the request
                db(f"DELETE FROM friend_req WHERE \
                    sender_id = {friend_id} AND \
                    reciever_id = {session['user_id']}")

                flash("Friend request accepted!")
                return redirect("/friends")

            flash("Invalid request")
            return redirect("/friends")

        # user requested to deny a friend request
        elif request.form.get("deny_fr"):

            # checks if the request is a num
            if not request.form.get('deny_fr').isnumeric():
                flash("Invalid request")
                return redirect("/friends")

            # put the id into a var to make the code readable
            friend_id = int(request.form.get('deny_fr'))

            # checking if friend request exists
            rows = db(f"SELECT * FROM friend_req WHERE \
                sender_id = {friend_id} AND \
                reciever_id = {session['user_id']}")

            # if the request doesnt exist it returns
            if len(rows) != 0:

                # deleting the request
                db(f"DELETE FROM friend_req WHERE \
                    sender_id = {friend_id} AND \
                    reciever_id = {session['user_id']}")

                flash("Friend request denied!")
                return redirect("/friends")

            flash("Invalid request")
            return redirect("/friends")

        # none of the post request are relevant
        else:
            flash("Invalid request")
            return redirect("/friends")
    
    #  makes a list of dicts for friends table
    friends_unsorted = []
    rows = db(f"SELECT * FROM friends WHERE user_id = {session['user_id']}")

    for row in rows:
        look = db(f"SELECT * FROM users WHERE id = {row['friend_id']}")
        
        friend = {
        'user_id': look[0]['id'],
        'username': look[0]['username'],
        'image_id': look[0]['image_id'],
        }
        friends_unsorted.append(friend)

    # make a list of dicts for friend requests
    friend_req_unsorted = []
    rows = db(f"SELECT * FROM friend_req WHERE \
        reciever_id = {session['user_id']}")

    for row in rows:
        look = db(f"SELECT * FROM users WHERE id = {row['sender_id']}")
        
        req = {
        'user_id': look[0]['id'],
        'username': look[0]['username'],
        'image_id': look[0]['image_id'],
        }
        friend_req_unsorted.append(req)

    friends = sorted(friends_unsorted, key=lambda k: k['username'])
    friend_req = sorted(friend_req_unsorted, key=lambda k: k['username'])

    return render_template("friends.html",friends=friends,\
        friend_req=friend_req ,darkmode=session["dark_mode"])


@app.route("/users", methods=["GET", "POST"])
@login_required
def users():
    """lists all the users"""

    # users filled in/used a form in a post method
    if request.method == "POST":

        # user used toggle_dark_mode
        if request.form.get('toggle_dark_mode'):
            dark_mode_toggler()

        # a request to send friend request
        elif request.form.get('send_fr'):

            # checks if the request contains a num
            if not request.form.get("send_fr").isnumeric():
                flash("Invalid request")
                return redirect("/users")

            # a variable that contains the id to make the code readable
            friend_id = int(request.form.get("send_fr"))

            # checks if the user is already a friend
            rows_f = db(f"SELECT * FROM friends \
                WHERE user_id = {session['user_id']} \
                AND friend_id = {friend_id}")

            # checks if the id exists in the database
            rows_u = db(f"SELECT * FROM users WHERE id = {friend_id}")

            # preforming the checks
            if len(rows_u) == 0 or len(rows_f) != 0:
                flash("Invalid request")
                return redirect("/users")

            # Checks if the friend already sent a friend request
            rows = db(f"SELECT * FROM friend_req WHERE \
                reciever_id = {session['user_id']} AND \
                sender_id = {friend_id}")

            # if the user already has a friend request from the designated
            # user, it proceeds to make them friends
            if rows != 0:
                db(f"INSERT INTO friends (user_id, friend_id) \
                    VALUES ({session['user_id']}, {friend_id})")

                db(f"INSERT INTO friends (user_id, friend_id) \
                    VALUES ({session['user_id']}, {friend_id})")

                db(f"DELETE FROM friend_req WHERE \
                reciever_id = {session['user_id']} AND \
                sender_id = {friend_id}")

                flash("Friend request accepted!")
                return redirect("/users")

            # now that the id is valid the app can proceed to add to the
            # friend_req table
            db(f"INSERT INTO friend_req (sender_id, reciever_id) \
                VALUES ({session['user_id']}, {friend_id})")

            # now that it has been added we can notify the user and redirect
            flash(f"Friend request has been sent to {rows_u[0]['username']}")
            return redirect("/users")

        # if none of the requests got called
        else:
            flash("Invalid request.")
            return redirect("/users")

    return render_template("users.html", darkmode=session["dark_mode"])


@app.route("/search_users")
@login_required
def search_users():
    """used to dynamically search users in /users"""

    # if an empty search bar was requested
    if not request.args.get('q'):
        return ""

    # fetch  usernames like the one typed
    rows = db(f"SELECT * FROM users WHERE username \
        LIKE '{request.args.get('q')}%' ORDER BY username")

    # checks if there are any users like the one typed
    if len(rows) == 0:
        return ""

    # an empty list to be populated by data
    users = []

    # if there are results it organaizes them in a list of dicts
    for row in rows:

        # prevents from seeing yourself in users
        if not row['id'] == session['user_id']:
            user = {
            'user_id': row['id'],
            'username': row['username'],
            'image_id': row['image_id']
            }

            # add the user dict to the users list
            users.append(user)

    return render_template("user.html", users=users, \
        darkmode=session["dark_mode"])
