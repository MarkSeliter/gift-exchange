import sqlite3

# connect to the database within the app folder
conn = sqlite3.connect("gift-exchange.db")
# the cursor for the database
c = conn.cursor()
