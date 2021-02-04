import sqlite3
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from tempfile import mkdtemp

# my helper func
from helper import login_required, check_email

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

# connect to the database within the app folder
conn = sqlite3.connect("database.db")
# the cursor for the database
c = conn.cursor()


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """The main page (supposed to show only if logged in)"""
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = c.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

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
        rows = c.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        if len(rows) != 0:
            flash(f"Sorry, {username} is already taken")
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
        c.execute("INSERT INTO users (username, hash, email) VALUES (?, ?)", \
            request.form.get("username"), \
            generate_password_hash(request.form.get("password1")), \
            request.form.get("email"))

        # to improve user experience it logs in the user right after registering
        rows = c.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        session["user_id"] = rows[0]["id"]
        flash("You've registered successfully!")
        return redirect("/")

    # if its a get method (load the register page to register)
    return render_template("register.html")
