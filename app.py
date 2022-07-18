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

    total = 0
    results = db.execute("SELECT * FROM purchases WHERE id = ?", session["user_id"])
    personal = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

    cash = personal[0]['cash']

    result = results[0]
    ticker = result['ticker'].upper()
    shares = result['shares']
    bought = result['price']

    exchange = lookup(ticker)
    name = exchange['name']
    price = exchange['price']


    for i in range(len(results)):
        total += results[i]['shares'] * results[i]['price']

        ticker = results[i]['ticker']
        results[i]['name'] = lookup(ticker)['name']
        results[i]['price'] = lookup(ticker)['price']
        results[i]['difference'] = usd(-1 * (bought - price))

    profile = usd(cash + total)
    cash = usd(cash)
    price = usd(price)

    return render_template("index.html", results=results, ticker=ticker, cash=cash, profile=profile, shares=shares, name=name, price=price)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":

        ticker = request.form.get("symbol")
        shares = request.form.get("shares")
        amounts = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        print(amounts)
        amount = amounts[0]['cash']
        if not ticker:
            return apology("Please input a stock ticker symbol")
        elif not shares:
            return apology("Please indicate how many shares you want to buy")
        elif int(shares) < 0:
            return apology("Please input a positive number of shares")
        elif len(ticker) > 5:
            return apology("Ticker cannot be more than 5 letters")

        try:
            result = lookup(ticker)
        except:
            return apology("Not a valid ticker")
        else:
            price = result["price"]
            name = result["name"]
            if price * int(shares) > int(amount):
                return apology("You do not have enough $$ to buy that")
            final = amount - (price * int(shares))
            remaining = db.execute("UPDATE users SET cash = ? WHERE id = ?", final, session["user_id"])
            db.execute("INSERT INTO purchases (id, ticker, shares, price, date, time) VALUES(?, ?, ?, ?, ?, ?)",
            session["user_id"], ticker.upper(), shares, price, date, time)

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

        if not ticker:
            return apology("Please enter a Stock ticker symbol")
        elif len(ticker) > 5:
            return apology("Not a valid ticker symbol, needs to be less than 5 letters")

        try:
            result = lookup(ticker)
        except:
            return apology("Not a valid ticker")
        else:
            name = result["name"]
            price = result["price"]
            symbol = result["symbol"]

            return render_template("quoted.html", name=name, price=price, symbol=symbol)

    return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        confirm = request.form.get("confirm")

        if password != confirm:
            return apology("The password you've typed does not match")

        if db.execute("SELECT username FROM users WHERE username = ?", username):
            return apology("This username is not available")
        elif not username:
            return apology("Please input a username")
        elif not password:
            return apology("Please input a password")
        elif not confirm:
            return apology("Please confirm your password")

        password2 = generate_password_hash(password)

        db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, password2)

        session["user_id"] = username

        return redirect("/")

    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    have = 0
    purchase_symbols = {}
    sales_symbols = {}
    finals = {}
    purchases = db.execute("SELECT * FROM purchases WHERE id = ?", session['user_id'])
    sales = db.execute("SELECT * FROM sales WHERE id = ?", session['user_id'])

    for i in range(len(purchases)):
        if purchases[i]['ticker'] in purchase_symbols:
            purchase_symbols[purchases[i]['ticker']] += purchases[i]['shares']
            continue
        purchase_symbols[purchases[i]['ticker']] = purchases[i]['shares']

    for j in range(len(sales)):
        if sales[j]['ticker'] in sales_symbols:
            sales_symbols[sales[j]['ticker']] += sales[j]['shares']
            continue
        sales_symbols[sales[j]['ticker']] = sales[j]['shares']

    for key, value in purchase_symbols.items():
        for k, v in sales_symbols.items():
            if key in sales_symbols:
                finals[key] = value - v
                break
            finals[key] = value

    if request.method == "POST":
        ticker = request.form.get("symbol")

        exchange = lookup(ticker)
        price = exchange['price']
        ticker = ticker.upper()

        amount = int(request.form.get("amount"))
        if not amount:
            return apology("Please input the amount of shares you want to sell")
        elif amount < 0:
            return apology("Please enter in a positive value")

        selected = db.execute("SELECT shares FROM purchases WHERE ticker = ?", ticker)

        for k in range(len(selected)):
            have += selected[k]['shares']
        if amount > have:
            return apology(f"You do not have enough shares, you only have {have}")

        db.execute("INSERT INTO sales (id, ticker, shares, price, date, time) VALUES(?, ?, ?, ?, ?, ?)",
        session["user_id"], ticker, amount, price, date, time)

        cashes = db.execute("SELECT cash FROM users WHERE id = ?", session['user_id'])
        cash = cashes[0]['cash']
        current = cash + price

        db.execute("UPDATE users SET cash = ? WHERE id = ?", current, session['user_id'])

        return render_template("sell.html", purchases=purchases, finals=finals)

    return render_template("sell.html", purchases=purchases, finals=finals)
