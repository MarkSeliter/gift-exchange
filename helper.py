from flask import redirect, render_template, request, session
from functools import wraps
import re

"""
Helping application.py operate
"""

def check_email(email):
    """
    Checks validitiy of email

    https://www.geeksforgeeks.org/check-if-email-address-valid-or-not-in-python/
    """
    regex = "^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$"

    if (re.search(regex, email)):
        return true
    return false


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
