from flask import Flask
from flask import render_template
from flask import request
from flask import session
from flask import redirect
from flask import url_for
import json
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
import sqlite3
from flask import g

"""
OVERVIEW:
This is to be a small, fully functional web application that models the business of a fictional competitor to
TicketMaster (let's call it AdmitOne). We will judge the submission primarily on code quality and system design.
If you are asked in for an interview, we will refer to your submission and ask you to speak to choices that you made
in design and implementation.

NOTE:
The web app has been adapted from this very helpful Flask tutorial:
https://code.tutsplus.com/tutorials/creating-a-web-app-from-scratch-using-python-flask-and-mysql--cms-22972

Use SQLite as lightweight and portable data store (Portable 'cos db lives in a file).
NOTE: For simplicity and brevity we will use raw sql queries rather than build an ORM.
      In real life, this would be unthinkable.  I would almost certainly use SqlAlchemy
      for a Flask app.

Scenario:
A REST service on AdmitOne's servers receives three types of messages: Purchases, Cancellations, and Exchanges.
"""

__author__ = 'bartelby'

app = Flask(__name__)
app.secret_key = "super secret key"
DATABASE='database/admit_one.db'

ADMIN_USERS = ['admin', 'psisk', 'bartelby']

#########################################
###### Database Infrastructure ##########
#########################################
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def add_delete_update_db(query, args=()):
    con = get_db()
    cur = con.cursor()
    cur.execute(query, args)
    con.commit()
    cur.close()


####################################
############## The App #############
####################################
@app.route("/")
def main():
    if not get_session_value('logged_in'):
        return render_template('index.html')
    else:
        return show_search_form()

@app.route('/main')
def call_main():
    return main()

@app.route('/show_sign_up')
def show_sign_up():
    """
    displays the user registration form
    :return: renders the signup template
    """
    return render_template('signup.html')

@app.route('/sign_up', methods=["POST"])
def sign_up():
    # read the posted values from the UI
    name = request.form['inputName']
    email = request.form['inputEmail']
    password = request.form['inputPassword']

    # validate the received values
    if name and email and password:
        #Don't create a new user if user exists
        check_user_stmt = "select 1 from USERS where user_name = ? or email_address = ?"
        args = (name, email)
        user_exists = query_db(check_user_stmt, args)
        if user_exists:
            return render_template('error_page.html',
                                   response_code='400',
                                   error_msg='User Already Exists with this name or email address')
        hashed_password = generate_password_hash(password)
        insert_stm = "INSERT INTO USERS (user_name, email_address, u_password) values(?, ?, ?)"
        args = (name, email, hashed_password)
        add_delete_update_db(insert_stm, args)
        #NOTE: fields not checked for valid input.  Format of email address, strength of pwd, etc. would all
        #       be validated 'in real life'.
        return render_template("signin.html")
    else:
        return json.dumps("400 - All fields are required")

@app.route('/show_sign_in')
def show_sign_in():
    return render_template("signin.html")

@app.route('/sign_in', methods=["POST"])
def sign_in():
    name = request.form['inputName']
    plaintext = request.form['inputPassword']
    hashed = query_db("select u_password from USERS where user_name = ?", (name,))
    if hashed:
        hashed = hashed[0][0]
        session['logged_in'] = check_password(hashed, plaintext)
        if get_session_value('logged_in') and name in ADMIN_USERS:
            session['auth_user'] = name
            #return "% logged in" % name
            return render_template("search_form.html",
                                   user=get_session_value('auth_user'))
        else:
            return render_template("error_page.html",
                                   response_code="401",
                                   error_msg="Unauthorized. Username or password incorrect\n(or maybe you aren't an admin...)")
@app.route('/show_search_form')
def show_search_form():
    if get_session_value('logged_in'):
        return render_template('search_form.html',
                            user=get_session_value('auth_user'))
    else:
        return json.dumps("401 - Unauthorized")

@app.route('/search_events', methods=["POST","GET"])
def search_events():
    if get_session_value('logged_in') and get_session_value('auth_user') in ADMIN_USERS:
        if request.form:
            from_event_id = request.form['fromEventId']
            to_event_id = request.form['toEventId']
        else:
            from_event_id = request.args['fromEventId']
            to_event_id=request.args['toEventId']
        search_stmt = 'select EVENTS.event_id, EVENTS.event_name, USERS.user_name, USERS.email_address, TICKETS.tickets' \
                      ' from EVENTS LEFT OUTER JOIN TICKETS ON EVENTS.event_id = TICKETS.show_id ' \
                      'LEFT JOIN USERS ON TICKETS.customer_id = USERS.user_id ' \
                      'where EVENTS.event_id >= ? and EVENTS.event_id <= ?'
        search_params = (from_event_id, to_event_id)
        events = query_db(search_stmt, search_params)
        return render_template('display_my_events.html',
                               user=get_session_value('auth_user'),
                               events=events)
    else:
        return render_template("error_page.html",
                               response_code="401",
                               error_msg="Unauthorized.")


def check_password(hashed, plaintext):
    return check_password_hash(hashed, plaintext)

def get_session_value(val):
    if val in session:
        return session[val]
    else:
        return None

@app.route('/sign_out', methods=["GET","POST"])
def clear_session():
    session['auth_user'] = None
    session['logged_in'] = None
    return main()

###########################################
############## The REST API ###############
###########################################
@app.route('/purchase/<user_name>/<num_tix>/<event_id>', methods=['POST','GET'])
def purchase(user_name, num_tix, event_id):
    if num_tix > 0:
        # FIXME: there ought to be a txn around this entire method
        iNum_tix = int(num_tix)
        results = get_user_id(user_name)
        user_id = results[0][0] if results else None
        if not user_id:
            return json.dumps('400 - Unknown user %s' % user_name)
        sql_stm = "INSERT OR IGNORE INTO TICKETS(customer_id, show_id, tickets) values (?,?, ?);"
        tix_stm = "UPDATE TICKETS set tickets = (tickets + ?) where customer_id = ? and show_id = ?;"
        tix = get_ticket_count(user_id, event_id)
        if tix == 0:
            add_delete_update_db(sql_stm, (user_id, event_id, tix))
        add_delete_update_db(tix_stm, (iNum_tix, user_id, event_id))
        return json.dumps({'response_code':"200"})
    return json.dumps({'response_code':"400"})

@app.route('/cancel/<user_name>/<num_tix>/<event_id>', methods=['POST','GET'])
def cancel(user_name, num_tix, event_id):
    if num_tix > 0:
        # FIXME: there ought to be a txn around this entire method
        iNum_tix = int(num_tix)
        results = get_user_id(user_name)
        user_id = results[0][0] if results else None
        if not user_id:
            return json.dumps({'response_code':"400"})
        sql_stm = "INSERT OR IGNORE INTO TICKETS(customer_id, show_id, tickets) values (?,?, ?);"
        tix_stm = "UPDATE TICKETS set tickets = (tickets - ?) where customer_id = ? and show_id = ?;"
        tix = get_ticket_count(user_id, event_id)
        if tix < iNum_tix:
            return json.dumps({"response_code":"400"})
        if num_tix == 0:
            add_delete_update_db(sql_stm, (user_id, event_id, tix))
        add_delete_update_db(tix_stm, (iNum_tix, user_id, event_id))
        return json.dumps({"response_code":"200"})
    return json.dumps({"response_code":"400"})


@app.route('/exchange/<user_name>/<num_tix>/<old_event_id>/<new_event_id>', methods=['POST','GET'])
def exchange(user_name, num_tix, old_event_id, new_event_id):
    if num_tix > 0:
        # FIXME: Of these three methods, this one most severely needs to be transactionalized
        iNum_tix = int(num_tix)
        results = get_user_id(user_name)
        user_id = results[0][0] if results else None
        if not user_id:
            return json.dumps('400 - Unknown user %s' % user_name)
        sql_stm = "INSERT OR IGNORE INTO TICKETS(customer_id, show_id, tickets) values (?,?, ?);"
        old_tix_stm = "UPDATE TICKETS set tickets = (tickets - ?) where customer_id = ? and show_id = ?;"
        new_tix_stm = "UPDATE TICKETS set tickets = (tickets + ?) where customer_id = ? and show_id = ?;"
        tix = get_ticket_count(user_id, old_event_id)
        nu_tix = get_ticket_count(user_id, new_event_id)
        if tix < iNum_tix:
            return json.dumps({"response_code":"400"})
        add_delete_update_db(old_tix_stm, (iNum_tix, user_id, old_event_id))
        if nu_tix == 0:
            add_delete_update_db(sql_stm, (user_id, new_event_id, nu_tix))
        add_delete_update_db(new_tix_stm, (iNum_tix, user_id, new_event_id ))
        return json.dumps({"response_code":"200"})
    return json.dumps({'response_code':"400"})

def get_user_id(user_name):
    sql_stm = "SELECT USERS.user_id FROM USERS WHERE USERS.user_name = ?"
    return query_db(sql_stm, (user_name,))

def get_ticket_count(user_id, event_id):
    cur_stm = "SELECT tickets FROM TICKETS WHERE show_id = ? and customer_id = ?;"
    cur_tix = query_db(cur_stm, (event_id, user_id))
    return cur_tix[0][0] if cur_tix else 0

#############################################
############ The app's main #################
#############################################
if __name__ == "__main__":
    app.run()

