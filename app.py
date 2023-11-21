import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_id = session["user_id"]

    db.execute("DROP TABLE homepage")
    #db.execute("CREATE TABLE homepage ( id INTEGER PRIMARY KEY, user_id INTEGER, stock_symbol TEXT, stock_name TEXT, shares FLOAT, price FLOAT, total_purchase_price FLOAT,balance_after FLOAT);")
    #db.execute("INSERT INTO homepage (user_id, stock_symbol, shares, price, total_purchase_price, balance_after) SELECT t.user_id, t.stock_name, SUM(t.shares_number_bought),t.stock_price_at_purchase, SUM(t.total_purchase_price), MIN(t.balance_after) FROM transactions AS t GROUP BY t.user_id, t.stock_name, t.stock_price_at_purchase ORDER BY balance_after DESC;")
    ##for check50 as it only accepts intger for shares number instead of float, ideally i prefer line 41 instead
    db.execute("CREATE TABLE homepage ( id INTEGER PRIMARY KEY, user_id INTEGER, stock_symbol TEXT, stock_name TEXT, shares INT, price FLOAT, total_purchase_price FLOAT,balance_after FLOAT);")

    db.execute("INSERT INTO homepage (user_id, stock_symbol, stock_name, shares, price, total_purchase_price, balance_after) SELECT t.user_id, t.stock_name, t.stock_name, SUM(t.shares_number),t.stock_price_at_transaction, SUM(t.total_purchase_price), MIN(t.balance_after) FROM transactions AS t GROUP BY t.user_id, t.stock_name ORDER BY balance_after DESC;")

    display_table = db.execute("SELECT * from homepage WHERE user_id = (?) ", user_id)
    cash = db.execute("SELECT cash from users WHERE id = (?)", user_id)[0]['cash']

    #line below is to get the total cash user had before buy all stocks
    #as the table - purchases contain unique id in id column, we will grab the only the row with id = 1
    #think of id column as transaction id for each transaction, hence id = 1 is always the first transaction of the user

    if display_table:
        # balance_after_initial_purchase = float(db.execute("SELECT balance_after from transactions WHERE id = ?", user_id)[0]['balance_after'])
        # purchase_price_to_be_added = float(db.execute("SELECT total_purchase_price from transactions WHERE id = ?", user_id)[0]['total_purchase_price'])

        total_purchase_price = round(float(db.execute("SELECT sum(total_purchase_price) FROM transactions where user_id = ?", user_id)[0]["sum(total_purchase_price)"]),2)

        total = total_purchase_price + cash

        return render_template("index.html",table_html = display_table, cash_html = cash, total_html = total )

    else:
        return render_template("index.html",table_html = display_table, cash_html = cash, total_html = cash)


    #return render_template("test.html", table_html = display_table)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    user_id = session["user_id"]
    if request.method == "POST":
        # if not request.form.get("symbol"):
        #     return apology("must provide stock symbol")
        # elif not request.form.get("shares") or int(request.form.get("shares")) <= 0 or int(request.form.get("shares")):
        #     return apology("must provide positive number of shares numbers")

        try:
            stock = request.form.get("symbol")
        except:
            return apology("must provide stock symbol")

        try:
            #number = float(request.form.get("shares"))
            number = int(request.form.get("shares"))
        except:
            return apology("must provide positive number of shares numbers")

        if number <= 0:
            return apology("must provide positive number of shares numbers")


        stock_info = lookup(stock)

        #checking if stock_info is valid
        if stock_info:
            stock_price = round(float(stock_info["price"]),2) #get the price from the lookup() function
            # return render_template("test.html", stock_price = stock_price) - test line to see if stock price has the value we want
            total_price = stock_price * number #total unit price
            user_balance = db.execute("SELECT cash from users WHERE id = (?)", user_id) #grab current user's balance from database
            user_balance = round(float(user_balance[0]['cash']),2) #as the line above gives {"cash" : number}, this line grabs the value -number only

            if user_balance >= total_price: #checking if user is eligible to buy the stock or not
                new_user_balance = user_balance - total_price
                #return render_template("test.html", user_balance_html = total_price)
                db.execute("INSERT INTO transactions (user_id, stock_name, stock_price_at_transaction, shares_number, total_purchase_price, balance_after) VALUES (?, ?, ?, ?, ?, ?)", user_id, stock_info['name'], stock_price, number, total_price, new_user_balance)
                db.execute("UPDATE users SET cash = (?) WHERE id = (?)", new_user_balance, user_id)
            else:
                return apology("you don't have enough cash")

        else:
            return apology("sorry, symbol entered is invalid")


        return redirect("/")

    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session["user_id"]

    table = db.execute("SELECT * FROM transactions WHERE user_id = ?", user_id)
    return render_template("history.html", table_html = table)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/change_password", methods=["GET"])
def change_password():
    return render_template("change_password.html")

@app.route("/update_password", methods=["POST"])
def update_password():
    """UPDATING and CHANGNING PASSWORD"""

    if request.method == "POST":
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("username doesn't exist")

        else:
            db.execute("UPDATE users SET hash = ? where username = ?", generate_password_hash(request.form.get("new_password")), request.form.get("username"))
            return ("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "POST":

        symbol = request.form.get("symbol")
        stock = lookup(symbol)
        if not stock:
            return apology("invalid symbol")

        return render_template("quoted.html", stock = stock)
    else:
        return render_template("quote.html")




@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        users_table = db.execute("SELECT username FROM users")

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        username = request.form.get("username")

        for name in users_table:
            if name['username'] == username:
                return apology("username is taken, try a new username")

        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if password == confirmation:

            hashed_password = generate_password_hash(password) #hashing the password input by the user

            db.execute("INSERT INTO users (username,hash) VALUES(?,?)", username, hashed_password)

            # Redirect user to home page
            return redirect("/")
        else:
            return apology("passwords entered do not match")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    user_id = session["user_id"]

    users_transactions_table = db.execute("SELECT DISTINCT stock_name FROM transactions WHERE user_id = ?" , user_id)

    if request.method == "POST":
        try:
            stock = request.form.get("symbol")
        except:
            return apology("must provide stock symbol")

        try:
            number = float(request.form.get("shares"))
        except:
            return apology("must provide positive number of shares numbers")

        if number <= 0:
            return apology("must provide positive number of shares numbers")

        #checking if stock_info is valid
        try:
            stock_info = lookup(stock)
        except:
            return apology("must provide valid stock symbol")

        users_transactions_table = db.execute("SELECT DISTINCT stock_name FROM transactions WHERE user_id = ?" , user_id)

        for stock_name in users_transactions_table:
            if stock_name['stock_name'] != stock:
                return apology("you do not own any provided stock shares")

            user_shares = db.execute("SELECT sum(shares_number) from transactions WHERE stock_name = (?) and user_id = (?)", stock, user_id)[0]["sum(shares_number)"]
            if user_shares < number :
                    return apology("you don't have enough number of shares to sell!")

            stock_price = round(float(stock_info["price"]),2) #get the price from the lookup() function
            # return render_template("test.html", stock_price = stock_price) - test line to see if stock price has the value we want
            total_price = stock_price * number #total unit price
            user_balance = db.execute("SELECT cash from users WHERE id = (?)", user_id) #grab current user's balance from database
            user_balance = round(float(user_balance[0]['cash']),2) #as the line above gives {"cash" : number}, this line grabs the value -number only
            new_user_balance = total_price + user_balance
            insert_shares_number = 0.0 - number
            insert_total_sell_price = 0.0 - total_price

            db.execute("UPDATE users SET cash = ? where id = ?", new_user_balance , user_id)
            db.execute("INSERT INTO transactions(user_id, stock_name, stock_price_at_transaction, shares_number, total_purchase_price, balance_after) VALUES (?, ?, ?, ?, ?, ?)", user_id, stock_info['name'], stock_price, insert_shares_number, insert_total_sell_price, new_user_balance)


            return redirect("/")
        #return render_template("test.html", table_html = test) # for testing

    return render_template("sell.html", stock_table = users_transactions_table)
