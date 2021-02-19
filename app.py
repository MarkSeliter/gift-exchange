from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from tempfile import mkdtemp
from random import randint, shuffle

from helper import login_required, check_email, db

# configure the a flask app
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# constants
PENDING_GAME = 0
ACTIVE_GAME = 1
FINISHED_GAME = 2


@app.route("/dark_mode", methods=["POST"])
@login_required
def dark_mode():
    """toggles darkmode for a logged in user"""

    session["dark_mode"] = session["dark_mode"] * -1
    dark_mode_new = session["dark_mode"]
    db(f"UPDATE users SET dark_mode = {dark_mode_new} \
        WHERE id ={session['user_id']}")

    path = str(request.form.get('cur_path')).strip()

    return redirect(path)


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """The main page (supposed to show only if logged in)"""

    # user subbmited a form via post
    if request.method == "POST":

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


@app.route("/change_pass", methods=["POST"])
@login_required
def change_pass():
    """Update user's password to a new password"""

    # check if user provided password
    if not request.form.get('password'):
        flash("Must provide old password")
        return redirect("/")

    # check if user provided new passwqord
    if not request.form.get('password_1'):
        flash("Must repeat old password")
        return redirect("/")

    # check if user repeated new password
    if not request.form.get('password_2'):
        flash("Must provide new password")
        return redirect("/")

    rows = db(f"SELECT * FROM users WHERE id = {session['user_id']}")
    # check if user provided correct old password
    if not check_password_hash(rows[0]["hash"], request.form.get("password")):
        flash("Incorrect password")
        return redirect("/")

    # check if new and repeated passwords match
    if request.form.get('password_1') != request.form.get('password_2'):
        flash("Passwords dont match")
        return redirect("/")

    # now that passwords match the password can be updated
    db(f"UPDATE users SET hash = '{generate_password_hash(request.form.get('password_1'))}' \
        WHERE id = {session['user_id']}")

    flash("Password updated successfully")
    return redirect("/")


@app.route("/pass_form", methods=["GET"])
@login_required
def pass_form():
    """Loads change_pass form"""

    return render_template("pass_form.html", darkmode=session["dark_mode"])


@app.route("/friends", methods=["GET", "POST"])
@login_required
def friends():
    """Lists all your friends and firend requests"""

    # if its a request to change something
    if request.method == "POST":

        # user requested to remove a friend
        if request.form.get("remove_friend"):

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

        # a request to send friend request
        if request.form.get('send_fr'):

            # checks if the request contains a num
            if not request.form.get("send_fr").isnumeric():
                flash("Invalid request")
                return redirect("/users")

            # a variable that contains the id to make the code readable
            friend_id = int(request.form.get("send_fr"))

            # checks if the id exists in the database
            rows = db(f"SELECT * FROM users WHERE id = {friend_id}")

            # preforming the checks
            if len(rows) == 0:
                flash("Invalid request")
                return redirect("/users")

            # checks if the user is already a friend
            rows= db(f"SELECT * FROM friends \
                WHERE user_id = {session['user_id']} \
                AND friend_id = {friend_id}")


            if len(rows) != 0:
                flash("You're already friends")
                return redirect("/users")


            # Checks if the friend already sent a friend request
            rows = db(f"SELECT * FROM friend_req WHERE \
                reciever_id = {session['user_id']} AND \
                sender_id = {friend_id}")

            # if the user already has a friend request from the designated
            # user, it proceeds to make them friends
            if len(rows) != 0:
                db(f"INSERT INTO friends (user_id, friend_id) \
                    VALUES ({session['user_id']}, {friend_id})")

                db(f"INSERT INTO friends (user_id, friend_id) \
                    VALUES ({friend_id}, {session['user_id']})")

                db(f"DELETE FROM friend_req WHERE \
                reciever_id = {session['user_id']} AND \
                sender_id = {friend_id}")

                flash("Friend request accepted!")
                return redirect("/users")

            # if the user is the first send the friend request
            else:
                db(f"INSERT INTO friend_req (sender_id, reciever_id) \
                    VALUES ({session['user_id']}, {friend_id})")

            # now that it has been added we can notify the user and redirect
            flash(f"Friend request has been sent")
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


@app.route("/create_game", methods=["GET", "POST"])
@login_required
def create_game():
    """handles the game creation form"""
    if request.method == "POST":

        # checking if any input is empty
        if not request.form.get('g_name') or \
        not request.form.get('desc'):
            flash("Please do not leave empty inputs")
            return redirect("/games")

        # checking if at least 2 other players are selected
        if len(request.form.getlist('par')) < 2:
            flash("Please choose at least 2 other participants")
            return redirect("/games")

        # check if an equal game name already exists
        game_name = request.form.get('g_name')

        rows = db(f"SELECT * FROM games WHERE game_name = '{game_name}'")

        if len(rows) > 0:
            flash(f"{game_name} already exists, please try another name")
            return redirect("/games")

        # checking if all participants are in the user's friends list
        par = request.form.getlist('par')

        for p in par:

            rows = db(f"SELECT * FROM friends WHERE \
                user_id = {session['user_id']} AND \
                friend_id = {p}")

            if not rows:
                flash("ERROR, tried inviting user which \
                    is not in your friends list")
                return redirect("/games")

        # insert game details into the db with def status of 0 (pending)
        desc = request.form.get('desc')

        db(f"INSERT INTO games (game_name, game_desc, admin_id) \
            VALUES ('{game_name}', '{desc}', {session['user_id']})")

        # fetching the game details (mainly for the id)
        game = db(f"SELECT * FROM games WHERE game_name = '{game_name}'")

        # adding game requests to all participants
        for p in par:
            db(f"INSERT INTO game_req (admin_id, reciever_id, game_id) VALUES \
                ({session['user_id']}, {p}, {game[0]['id']})")

        # adding the admin of the game to the participants
        db(f"INSERT INTO par (user_id, game_id) VALUES \
            ({session['user_id']}, {game[0]['id']})")

        flash("Game created successfully")
        return redirect("/games")

    # an empty list to load friends into
    friends_unsorted = []

    # gets all the id's of the user's friends
    rows = db(f"SELECT * FROM friends WHERE user_id = {session['user_id']}")

    # loops over all the ids
    for row in rows:

        # looks for the friend in users
        look = db(f"SELECT * FROM users WHERE id = {row['friend_id']}")
        
        friend = {
        'user_id': look[0]['id'],
        'username': look[0]['username'],
        'image_id': look[0]['image_id'],
        }

        # appends the friend dict to the list
        friends_unsorted.append(friend)

        # sorts the friends by username
        friends = sorted(friends_unsorted, key=lambda k: k['username'])

    return render_template("create_game.html", darkmode=session["dark_mode"] ,\
        friends=friends)


@app.route("/load_games", methods=["GET"])
@login_required
def load_games():
    """loads the games associated with the logged in user"""

    # if its a request to load pending games
    if int(request.args.get('s')) == PENDING_GAME:
        load_status = PENDING_GAME

    # if its a request to see active games
    elif int(request.args.get('s')) == ACTIVE_GAME:
        load_status = ACTIVE_GAME

    # if its a request to see finished games
    elif int(request.args.get('s')) == FINISHED_GAME:
        load_status = FINISHED_GAME

    else:
        return ""

    # an empty list of games
    games = []

    rows = db(f"SELECT * FROM games WHERE status = {load_status} AND id IN \
            (SELECT game_id FROM par WHERE user_id = {session['user_id']}) \
            ORDER BY game_name")


    for row in rows:

        # a dict containing game info
        game = {
        'game_id': row['id'],
        'status': row['status'],
        'game_name': row['game_name'],
        'game_desc': row['game_desc']
        }

        # list of participants

        participants = []

        # look for participants in this game
        rows_2 = db(f"SELECT * FROM users WHERE id IN \
            (SELECT user_id FROM par WHERE game_id = {game['game_id']}) \
            ORDER BY username")

        for row_2 in rows_2:

            # dict containing participant's info
            par = {
            'user_id': row_2['id'],
            'username': row_2['username'],
            'image_id': row_2['image_id']
            }

            # add the user to the list
            participants.append(par)

        # add participants to the game info
        game['par'] = participants

        # if its a pending game, it loads game requests and availabe inviteable friends
        if load_status == PENDING_GAME:

            # a list for all the already invited friends
            game_req = []

            # get a list of all friends with a game request
            rows_2 = db(f"SELECT * FROM users WHERE id IN \
                (SELECT reciever_id FROM game_req WHERE \
                game_id = {game['game_id']}) ORDER BY username")

            for row_2 in rows_2:

                # add the the requested user's info
                req = {
                'user_id': row_2['id'],
                'username': row_2['username'],
                'image_id': row_2['image_id']
                }

                # add the friend to the list
                game_req.append(req)

            # add the list to the game's info
            game['game_req'] = game_req

            # a list for all inviteable friends
            invite = []

            # get a list of all friends that can be invited
            rows_2 = db(f"SELECT * FROM users WHERE id IN \
                (SELECT friend_id FROM friends WHERE \
                user_id = {session['user_id']} AND friend_id NOT IN \
                (SELECT user_id FROM par WHERE \
                game_id = {game['game_id']}) AND friend_id NOT IN \
                (SELECT reciever_id FROM game_req WHERE \
                game_id = {game['game_id']})) ORDER BY username")

            for row_2 in rows_2:

                # add the inviteable friend's info
                inv = {
                'user_id': row_2['id'],
                'username': row_2['username'],
                'image_id': row_2['image_id']
                }

                # add the friend to the list
                invite.append(inv)

            # add the list to the game's info
            game['invite'] = invite

        # if its an active game it loads the gifted's info
        if load_status == ACTIVE_GAME:
        
            # add the gifted's info
            rows_2 = db(f"SELECT * FROM users WHERE id IN \
                (SELECT gifted_id FROM par WHERE user_id = {session['user_id']} \
                AND game_id = {game['game_id']})")

            game['gifted_u'] = rows_2[0]['username']

        # if its a finished game it loads the gifted's info
        if load_status == FINISHED_GAME:

            # a list of gifted users
            gifted = []

            # itirate over the list of participabts
            for p in participants:

                # get the participant's gifted'd id
                rows_2 = db(f"SELECT * FROM users WHERE id = \
                    (SELECT gifted_id FROM par WHERE user_id = {p['user_id']} \
                    AND game_id = {game['game_id']})")

                # a dict of info relevant to the gifted
                user = {
                'user_id': rows_2[0]['id'],
                'username': rows_2[0]['username'],
                'image_id': rows_2[0]['image_id']
                }

                print(user)

                # add the user to the gifted list
                gifted.append(user)

            # add the list to the game's info
            game['gifted'] = gifted

        # look for the creator of the game
        rows_2 = db(f"SELECT * FROM users WHERE id IN \
            (SELECT admin_id FROM games WHERE id = {row['id']})")

        game['creator'] = rows_2[0]['username']

        # check if user is the admin of the game
        if rows_2[0]['id'] == session['user_id']:
            game['admin'] = True
        else:
            game['admin'] = False

        games.append(game)

    # choose the correct template
    if load_status == PENDING_GAME:
        template = "pending_games.html"

    elif load_status == ACTIVE_GAME:
        template = "active_games.html"

    elif load_status == FINISHED_GAME:
        template = "/finished_games.html"
    else:
        flash("Invalid request")
        template = "/"

    return render_template(template, darkmode=session["dark_mode"], games=games)


@app.route("/game_requests", methods=["GET"])
@login_required
def game_requests():
    """Loads a template with all user's game requests"""

    # looks for all games that the user is requested to join
    rows = db(f"SELECT * FROM games WHERE id IN \
        (SELECT game_id FROM game_req WHERE reciever_id = {session['user_id']}) \
        ORDER BY game_name")

    requests = []

    # create a dict for each game and append to list of requests
    for row in rows:

        creator = db(f"SELECT * FROM users WHERE id = {row['admin_id']}")

        temp = {
        'game_id': int(row['id']),
        'creator': creator[0]['username'],
        'game_name': row['game_name'],
        'game_desc': row['game_desc']
        }

        requests.append(temp)

    return render_template("game_requests.html", darkmode=session["dark_mode"], \
        requests=requests)


@app.route("/handle_game_request", methods=["GET"])
@login_required
def handle_game_request():
    """Accepts or deny game request"""

    # check if game_id exists
    if not request.args.get('game_id'):
        flash("Invalid request")
        return redirect("/games")

    # check if accept or deny exists
    if not request.args.get('a_o_d'):
        flash("Invalid request")
        return redirect("/games")

    a_o_d = int(request.args.get('a_o_d'))

    # checks of a_o_d has expected values
    if a_o_d < 0 or a_o_d > 1:
        flash("Invalid request")
        return redirect("/games")

    # get the game id
    game_id = int(request.args.get('game_id'))

    rows = db(f"SELECT * FROM game_req WHERE game_id = {game_id} \
        AND reciever_id = {session['user_id']}")

    # check if the game request exists
    if len(rows) == 0:
        flash("Invalid request")
        return redirect("/games")

    # check if the game is still pending
    rows = db(f"SELECT * FROM games WHERE id = {game_id}")

    if rows[0]['status'] != 0:
        flash("sorry, game already started")

    # checks if its a request to accept or deny
    elif a_o_d == 1:
        db(f"INSERT INTO par (user_id, game_id) \
            VALUES ({session['user_id']}, {game_id})")
        flash("Game request accepted")

    else:
        flash("Game request denied")

    # removes the request
    db(f"DELETE FROM game_req WHERE game_id ={game_id} \
        AND reciever_id = {session['user_id']}")

    return redirect("/games")


@app.route("/invite", methods=["POST"])
@login_required
def invite():
    """Invite participants to a pending game"""

    # check if game_id and invited friends exist
    if not request.form.get('game_id'):
        print(request.form.get('game_id') + " was the game_id")
        flash("Invalid request")
        return redirect("/games")

    # check if user is the admin
    game_id = request.form.get('game_id')

    admin_check = db(f"SELECT * FROM games WHERE id = {game_id}")

    if int(session['user_id']) != int(admin_check[0]['admin_id']):
        flash("You dont have permission")
        return redirect("/games")

    friends = request.form.getlist('friends')

    for i in friends:

        # check if it's an inviteable friend
        look = db(f"SELECT friend_id FROM friends WHERE \
            user_id = {session['user_id']} AND friend_id NOT IN \
            (SELECT user_id FROM par WHERE \
            game_id = {game_id}) AND friend_id NOT IN \
            (SELECT reciever_id FROM game_req WHERE \
            game_id = {game_id}) AND friend_id = {i}")

        # once its an inviteable friend it proceeds to add it to the game
        # requests table
        if len(look) == 1:
            db(f"INSERT INTO game_req (admin_id, reciever_id, game_id) VALUES \
                ({session['user_id']}, {i}, {game_id})")
    
    return redirect("/games")


@app.route("/activate_game", methods=["POST"])
@login_required
def activate_game():
    """turns the game to an active one, assigns to each player a gifter"""

    # check if game_id is missing
    if not request.form.get('game_id'):
        flash("Invalid request")
        return redirect("/games")
    
    # check if game_id is a number
    if not request.form.get('game_id').isnumeric():
        flash("Invalid request")
        return redirect("/games")

    game_id = int(request.form.get('game_id'))
    
    rows = db(f"SELECT * FROM games WHERE id = {game_id}")

    # checks if game_id exists
    if len(rows) == 0:
        flash("Invalid request")
        return redirect("/games")

    # check if the user is the admin
    if int(rows[0]['admin_id']) != int(session['user_id']):
        flash("You dont have permission")
        return redirect("/games")

    # check if there are enough participants
    rows = db(f"SELECT * FROM par WHERE game_id = {game_id}")

    if len(rows) < 3:
        flash("There has to be at least 3 participants in order to play")
        return redirect("/games")

    # now that the user is confirmed as an admin and the game exists
    # game is changed to active status
    db(f"UPDATE games SET status = {ACTIVE_GAME} WHERE id = {game_id}")

    # get all the participants' id
    rows = db(f"SELECT * FROM par WHERE game_id = {game_id}")

    # a list to insert participants to
    par_list = []

    for row in rows:
        par_list.append(row['user_id'])

    # randomize participant's order
    shuffle(par_list)

    # a rotation variable
    rot = int(len(par_list) / 2)

    # an empty list to insert gited's id into
    gifted_list = par_list

    print(f"(MARK) the rot is : {rot}")

    # construct the rotated list
    gifted_list = gifted_list[rot:] + gifted_list[:rot]

    # assign each player a gifted player
    for i in range(len(par_list)):
        db(f"UPDATE par SET gifted_id = {gifted_list[i]} WHERE \
            user_id = {par_list[i]} AND game_id = {game_id}")

    # delete all game requests
    db(f"DELETE FROM game_req WHERE game_id = {game_id}")

    flash("Game has started")
    return redirect("/games")

@app.route("/games", methods=["GET"])
@login_required
def games():
    """Loads the games page"""

    return render_template("games.html", darkmode=session["dark_mode"])


@app.route("/delete_game", methods=["POST"])
@login_required
def delete_game():
    """grants the admin the ability to delete the game 
    and everything associated with it"""

    # check if there was an html manipulation
    if not request.form.get('game_id') or not request.form.get('game_id').isnumeric():
        flash("Invalid request")
        return redirect("/games")

    game_id = int(request.form.get('game_id'))

    # check if the game exists
    rows = db(f"SELECT * FROM games WHERE id = {game_id}")

    if len(rows) == 0:
        flash("Invalid request")
        return redirect("/games")

    # check if the user is the admin of the game
    if not rows[0]['admin_id'] == session['user_id']:
        flash("You dont have permission to do that")
        return redirect("/games")

    # after confirming admin, proceeding to delete everything associated with the game
    db(f"DELETE FROM games WHERE id = {game_id}")
    db(f"DELETE FROM game_req WHERE game_id = {game_id}")
    db(f"DELETE FROM par WHERE game_id = {game_id}")

    flash("Game deleted successfully")
    return redirect("/games")


@app.route("/end_game", methods=["POST"])
@login_required
def end_game():
    """changes the status of the game to FINISHED_GAME"""

    # check if there was an html manipulation
    if not request.form.get('game_id') or not request.form.get('game_id').isnumeric():
        flash("Invalid request")
        return redirect("/games")

    game_id = int(request.form.get('game_id'))

    # check if the game exists
    rows = db(f"SELECT * FROM games WHERE id = {game_id}")

    if len(rows) == 0:
        flash("Invalid request")
        return redirect("/games")

    # check if the user is the admin of the game
    if not rows[0]['admin_id'] == session['user_id']:
        flash("You dont have permission to do that")
        return redirect("/games")

    db(f"UPDATE games SET status = {FINISHED_GAME} WHERE id = {game_id}")

    flash("The game has finished!")
    return redirect("/games")


if __name__ == '__main__':
    app.run(debug=True)
