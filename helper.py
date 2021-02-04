from flask import redirect, render_template, request, session
from functools import wraps
import re
import sqlite3


"""
Helping application.py operate
"""

# the name of the db used in the app
database = "database.db"


def check_email(email):
    """
    Checks validitiy of email

    https://www.geeksforgeeks.org/check-if-email-address-valid-or-not-in-python/
    """
    regex = "^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$"

    if (re.search(regex, email)):
        return True
    return False

def db(statement):
    """
    Simplified way to query the database
    I only need to metion db followed by sqlite3 statement.
    The func takes care of connecting, executing, commiting and returning
    value if needed.
    In addition the func takes care of always closing the connection when
    the usage is over so theres no need to worry about closing.
    """
    with sqlite3.connect(database) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(statement)
        conn.commit()
        return cur.fetchall()

    return 0


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            # makes sure the user is logged in before executing the
            # decorated func
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function
