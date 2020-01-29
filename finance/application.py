import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
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


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    cash = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])
    stocks = db.execute("SELECT stock, shares FROM history WHERE id = :id", id=session["user_id"])
    dec = {}
    dc = {}
    lis = []
    ls = []
    total = cash[0]["cash"]
    for raw in stocks:
        if raw["stock"] in dec:
            dec[raw["stock"]] += raw["shares"]
        else:
            dec[raw["stock"]] = raw["shares"]

    for raw in stocks:
        if raw["stock"] not in ls:
            ls.append(raw["stock"])
            name = lookup(raw["stock"])
            dc["name"] = name["name"]
            dc["price"] = name["price"]
            dc["symbol"] = raw["stock"]
            dc["shares"] = dec[raw["stock"]]
            if dc["shares"] == 0:
                dc = {}
                continue
            dc["total"] = dc["price"] * dc["shares"]
            lis.append(dc)
            total += dc["total"]
            dc = {}
    return render_template("index.html", cash=cash[0]["cash"], lis=lis, total=total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        if not request.form.get("symbol") or not request.form.get("shares"):
            return apology("blank field", 400)
        elif int(request.form.get("shares")) < 1:
            return apology("enter a positive nubmer", 400)

        symbol = lookup(request.form.get("symbol"))
        if not symbol:
            return apology("invalid symbol", 400)
        cash = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])
        if symbol["price"] * int(request.form.get("shares")) > cash[0]["cash"]:
            return apology("u don't have enough cash", 400)
        db.execute("UPDATE users SET cash = cash - :symbol WHERE id = :id",
                   symbol=symbol["price"] * int(request.form.get("shares")), id=session["user_id"])
        db.execute("INSERT INTO history (id, stock, shares, price) VALUES(:id, :stock, :shares, :price)",
                   id=session["user_id"], stock=request.form.get("symbol").upper(),
                   shares=int(request.form.get("shares")), price=symbol["price"])
        return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""
    name = db.execute("SELECT username FROM users")
    for i in name:
        if i["username"] == request.args.get("username"):
            return jsonify(False)
    return jsonify(True)


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    history = db.execute("SELECT * FROM history WHERE id = :id", id=session["user_id"])
    return render_template("history.html", history=history)


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
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

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
        stock = lookup(request.form.get("symbol"))
        if not stock:
            return apology("invalid stock symbol", 400)
        return render_template("stock.html", stock=stock)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 400)
        elif not request.form.get("password"):
            return apology("must provide password", 400)
        elif not request.form.get("confirmation"):
            return apology("must confirm password", 400)
        elif request.form.get("confirmation") != request.form.get("password"):
            return apology("password don't match", 400)

        hash = generate_password_hash(request.form.get("password"))
        result = db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)",
                            username=request.form.get("username"),
                            hash=hash)
        if not result:
            return apology("username already exist", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    stocks = db.execute("SELECT * FROM history WHERE id = :id", id=session["user_id"])
    if request.method == "POST":
        if not request.form.get("symbol") or not request.form.get("shares"):
            return apology("please input things", 403)
        elif int(request.form.get("shares")) < 1:
            return apology("please enter positive number")

        symbol = lookup(request.form.get("symbol"))
        shares = db.execute("SELECT shares FROM history WHERE id= :id AND stock = :stock",
                            id=session["user_id"], stock=symbol["symbol"])
        i = 0
        for share in shares:
            i += share["shares"]
        if int(request.form.get("shares")) > i:
            return apology("u don't have enough shares")

        db.execute("UPDATE users SET cash = cash + :symbol WHERE id = :id",
                   symbol=symbol["price"] * int(request.form.get("shares")), id=session["user_id"])
        db.execute("INSERT INTO history (id, stock, shares, price) VALUES(:id, :stock, :shares, :price)",
                   id=session["user_id"], stock=request.form.get("symbol"),
                   shares=-int(request.form.get("shares")), price=symbol["price"])

        return redirect("/")

    else:
        ls = []
        for raw in stocks:
            if raw["stock"] not in ls:
                ls.append(raw["stock"])
        return render_template("sell.html", ls=ls)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
