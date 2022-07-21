import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import re

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

# Get the current date and time
times = re.search("^(.+) (.+)\.", str(datetime.now()))
date = times.group(1)
time = times.group(2)

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

    if request.method == "GET":
        total = 0
        sales_count = {}
        purchase_count = {}
        final_count = {}
        output = {}
        results = []

        # Grab data from SQL database
        purchases = db.execute("SELECT * FROM purchases WHERE id = ?", session["user_id"])
        cash = db.execute("SELECT cash FROM users WHERE id = ?", session['user_id'])[0]['cash']
        sales = db.execute("SELECT * FROM sales WHERE id = ?", session['user_id'])

        # Put all stocks sold in the sales SQL database into a dictionary
        for i in range(len(sales)):
            if sales[i]['ticker'] in sales_count:
                sales_count[sales[i]['ticker']] += sales[i]['shares']
                continue
            sales_count[sales[i]['ticker']] = sales[i]['shares']

        # Put all purchases in the purchase SQL database into a dictionary
        for j in range(len(purchases)):
            if purchases[j]['ticker'] in purchase_count:
                purchase_count[purchases[j]['ticker']] += purchases[i]['shares']
                continue
            purchase_count[purchases[j]['ticker']] = purchases[j]['shares']

        # Combine the two dictionaries: purchase minus sales, into one dictionary
        for key, value in purchase_count.items():
            if key in sales_count and purchase_count[key] - sales_count[key] == 0:
                continue
            elif key in sales_count and purchase_count[key] - sales_count[key] != 0:
                final_count[key] = purchase_count[key] - sales_count[key]
                continue
            final_count[key] = value

        # Grab general information about each specific stock in the final dictionary
        for k, v in final_count.items():
            output['ticker'] = k
            exchange = lookup(k)
            name = exchange['name']
            price = exchange['price']
            output['name'] = name
            output['shares'] = v
            output['price'] = price
            results.append(output.copy())

            # Add up each stock's value
            total += v * price

        # The amount of cash you have plus the total value of all your stocks
        profile = cash + total

        # Generate the index homepage
        return render_template("index.html", results=results, profile=profile, cash=cash)

    # Returns user to login page if not logged in
    return login()


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":

        # Grab user input data
        ticker = request.form.get("symbol")
        shares = request.form.get("shares")
        amounts = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        amount = amounts[0]['cash']

        # Checks user input
        if not ticker:
            return apology("Please input a stock ticker symbol")
        elif not shares:
            return apology("Please indicate how many shares you want to buy")
        elif int(shares) < 0:
            return apology("Please input a positive number of shares")
        elif len(ticker) > 5:
            return apology("Ticker cannot be more than 5 letters")

        if lookup(ticker) == None:
            return apology("Not a valid ticker")
        else:
            result = lookup(ticker)
            price = result["price"]
        name = result["name"]
        if price * int(shares) > int(amount):
            return apology("You do not have enough $$ to buy that")
        final = amount - (price * int(shares))
        remaining = db.execute("UPDATE users SET cash = ? WHERE id = ?", final, session["user_id"])
        db.execute("INSERT INTO purchases (id, ticker, shares, price, date, time) VALUES(?, ?, ?, ?, ?, ?)",
        session["user_id"], ticker.upper(), shares, price, date, time)

        # Generate a page to tell you which stock you have bought
        return render_template("bought.html", ticker=ticker, shares=shares, price=price, name=name, total=final, remain=remaining)

    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    results = db.execute("SELECT * FROM purchases WHERE id = ?", session['user_id'])
    sales = db.execute("SELECT * FROM sales WHERE id = ?", session['user_id'])

    return render_template("history.html", results=results, sales=sales)


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
    rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

    # Ensure username exists and password is correct
    if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
        return apology("invalid username and/or password", 403)

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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "POST":

        ticker = request.form.get("symbol")

        # Checks if user inputed a valid ticker
        if not ticker:
            return apology("Please enter a Stock ticker symbol")
        elif len(ticker) > 5:
            return apology("Not a valid ticker symbol, needs to be less than 5 letters")

        if lookup(ticker) == None:
            return apology("Not a valid ticker")
        else:
            result = lookup(ticker)
            name = result["name"]
            price = result["price"]
            symbol = result["symbol"]

        # Generate page that tells you basic information about the ticker inputed
        return render_template("quoted.html", name=name, price=price, symbol=symbol)

    return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":

        # Grab user input data
        username = request.form.get("username")
        password = request.form.get("password")
        confirm = request.form.get("confirmation")

        # Checks user input data
        if password != confirm:
            return apology("The password you've typed does not match")
        elif db.execute("SELECT username FROM users WHERE username = ?", username):
            return apology("This username is not available")
        elif not username:
            return apology("Please input a username")
        elif not password:
            return apology("Please input a password")
        elif not confirm:
            return apology("Please confirm your password")

        # Generate hash password
        password2 = generate_password_hash(password)

        # Store user data into SQL database call users
        db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, password2)
        latest = db.execute("SELECT * FROM users")
        last = latest[-1]['id']
        session["user_id"] = last

        # Redirects the user to the index page
        return redirect("/")

    # Brings user to register page
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    # Grabs user data in database
    have = 0
    purchase_symbols = {}
    sales_symbols = {}
    finals = {}
    purchases = db.execute("SELECT * FROM purchases WHERE id = ?", session['user_id'])
    sales = db.execute("SELECT * FROM sales WHERE id = ?", session['user_id'])

    # Grabs all purchases from user in SQL database and put it into a dictionary
    for i in range(len(purchases)):
        if purchases[i]['ticker'] in purchase_symbols:
            purchase_symbols[purchases[i]['ticker']] += purchases[i]['shares']
            continue
        purchase_symbols[purchases[i]['ticker']] = purchases[i]['shares']

    # Grabs all stock sold from user in SQL database and put it into a dictionary
    for j in range(len(sales)):
        if sales[j]['ticker'] in sales_symbols:
            sales_symbols[sales[j]['ticker']] += sales[j]['shares']
            continue
        sales_symbols[sales[j]['ticker']] = sales[j]['shares']

    # Combine the two dictionaries, purchase - sales, and put it into a dictionary
    for key, value in purchase_symbols.items():
        for k, v in sales_symbols.items():
            if key in sales_symbols:
                finals[key] = value - v
                break
            finals[key] = value

    # If user wants to sell specific stock
    if request.method == "POST":
        ticker = request.form.get("symbol")

        # Grab stock information from exchange
        exchange = lookup(ticker)
        name = exchange['name']
        price = exchange['price']
        ticker = ticker.upper()

        # Grabs the number of shares the user wants to sell
        amount = int(request.form.get("amount"))
        if not amount:
            return apology("Please input the amount of shares you want to sell")
        elif amount < 0:
            return apology("Please enter in a positive value")

        # Grab user data from SQL database on the specific stock the user wants to sell
        selected = db.execute("SELECT shares FROM purchases WHERE ticker = ?", ticker)

        # Iterates through the number of shares of stocks the user has
        for k in range(len(selected)):
            have += selected[k]['shares']
        if amount > have:
            return apology(f"You do not have enough shares, you only have {have}")

        # Input the sales data into a separate SQL database
        db.execute("INSERT INTO sales (id, ticker, shares, price, date, time) VALUES(?, ?, ?, ?, ?, ?)",
        session["user_id"], ticker, amount, price, date, time)

        # Grab the amount of cash the user current has
        cashes = db.execute("SELECT cash FROM users WHERE id = ?", session['user_id'])
        cash = cashes[0]['cash']
        current = cash + price * amount

        # Change the amount of cash the user has after purchasing of stock
        db.execute("UPDATE users SET cash = ? WHERE id = ?", current, session['user_id'])

        # Generate a page where it shows what stock the user sold
        return render_template("sold.html", ticker=ticker, name=name, shares=amount, price=price, total=current)

    return render_template("sell.html", purchases=purchases, finals=finals)

