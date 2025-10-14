# Python standard libraries
import json
import os
import sys

# Third-party libraries
from flask import Flask, redirect, request, url_for, render_template, jsonify
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user

from oauthlib.oauth2 import WebApplicationClient
import requests
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm.exc import NoResultFound

# Flask app setup
app = Flask(__name__)

FENIX_CLIENT_ID = 1132965128045002
FENIX_CLIENT_SECRET = "3AZQyZGzlf/I3Q8KIYyH9DXlBlWA38kg+6EUWeCgTT2+3pbi+cx5RjumU/nxgVo2UsoyBWryM2/j3bZ+xnSdPw=="



#Sqlalchemy configuration
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///multi.db"
db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(256), unique=True)
    name = db.Column(db.String(256), unique=True)
    email = db.Column(db.String(256), unique=True)

# User session management setup
# https://flask-login.readthedocs.io/en/latest
login_manager = LoginManager()
login_manager.init_app(app)
client = WebApplicationClient(FENIX_CLIENT_ID)

# Flask-Login helper to retrieve a user from our db
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
def frontPage():
    # print(listRooms())
    # rooms = listRooms()
    return render_template("loginScreen.html") 

@app.route("/login")
def login():
    authorization_endpoint = "https://fenix.tecnico.ulisboa.pt/oauth/userdialog"#google_provider_cfg["authorization_endpoint"]
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)

@app.route("/login/callback")
def callback():
    code = request.args.get("code")

    token_endpoint = "https://fenix.tecnico.ulisboa.pt/oauth/access_token"
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(FENIX_CLIENT_ID, FENIX_CLIENT_SECRET),
    )
    client.parse_request_body_response(json.dumps(token_response.json()))

    userinfo_endpoint = "https://fenix.tecnico.ulisboa.pt/api/fenix/v1/person"
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)
    if userinfo_response.json().get("email"):
        username = userinfo_response.json()["username"]
        email = userinfo_response.json()["email"]
        name = userinfo_response.json()["name"]
        user = User(username = username,email = email,name=name)
        print(user.email, user.name, user.username)

        try:
            db.session.add(user)
            db.session.commit()
            # Log in the new local user account
            login_user(user)
        except:
            db.session.rollback()
            user = db.session.query(User).filter(User.username == username).first()
            login_user(user)
        return redirect(url_for("index"))
    else:
        return "User email not available.", 400

def process_qr_data(qr_text):
    # Example logic: decode, fetch info, etc.
    # if qr_text == "room123":
    #     return "Room 123: Capacity 40, Available"
    # elif qr_text == "menu45":
    #     return "Restaurant Menu 45: Today's special - Pasta"
    # else:
    #     return f"Unrecognized QR code: {qr_text}"
    return f"Scanned QR Code Data: {qr_text}"

@app.route("/qrreader")
def qrreader():
    return render_template("QRCodeCamera.html")


@app.route("/public_info")
def public_info():
    qr_data = request.args.get("data", None)
    message = None

    if qr_data:
        message = process_qr_data(qr_data)

    # Render your main page again, with the info included
    return render_template("loginScreen.html", public_info=message)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))
    
# hook up extensions to app
db.init_app(app)

if __name__ == "__main__":
    
    with app.app_context():
        db.create_all()
        db.session.commit()
    print("Database tables created")
    app.run(port=5100, debug=True, ssl_context="adhoc")