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

import datetime

# Flask app setup
app = Flask(__name__)

FENIX_CLIENT_ID = 1132965128045002
FENIX_CLIENT_SECRET = "3AZQyZGzlf/I3Q8KIYyH9DXlBlWA38kg+6EUWeCgTT2+3pbi+cx5RjumU/nxgVo2UsoyBWryM2/j3bZ+xnSdPw=="
CALLBACK_URL = "https://localhost:5100/login/callback"  

MESSAGE_API_URL = "http://localhost:5010/api"
MESSAGE_APP_SECRET = "eletrodomesticos_e_computadores_2024"


#Sqlalchemy configuration
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///multi.db"
db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(256), unique=True, nullable=False)
    name = db.Column(db.String(256), unique=True, nullable=False)
    email = db.Column(db.String(256), unique=True, nullable=False)


class Event():
    def __init__(self, title, start_time, end_time):
        self.title = title
        self.start_time = start_time
        self.end_time = end_time 

# User session management setup
# https://flask-login.readthedocs.io/en/latest
login_manager = LoginManager()
login_manager.init_app(app)
client = WebApplicationClient(FENIX_CLIENT_ID)
MAflag = True
# Flask-Login helper to retrieve a user from our db
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
def loginScreen():
    # print(listRooms())
    # rooms = listRooms()
    return render_template("loginScreen.html") 

@app.route("/mainScreen")
@login_required
def mainScreen():
    # print(listRooms())
    # rooms = listRooms()
    return render_template("mainScreen.html") 

@app.route("/messages")
@login_required
def messageScreen():
    # print(listRooms())
    # rooms = listRooms()
    return render_template("messageScreen.html") 

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
        # print(userinfo_response.json())
        username = userinfo_response.json()["username"]
        email = userinfo_response.json()["email"]
        name = userinfo_response.json()["name"]
        user = User(username = username,email = email,name=name)
        print(user.email, user.name, user.username)
        if not User.query.filter(User.email == email).first():
            try:
                db.session.add(user)
                db.session.commit()
                addUserToMessageApp(username)
                # Log in the new local user account
                login_user(user)
            except:
                db.session.rollback()
                user = db.session.query(User).filter(User.username == username).first()
                login_user(user)
        else:
            user = db.session.query(User).filter(User.username == username).first()
            login_user(user)
            MAuser =    messageAppIsUser(username)
            if MAuser==1:
                addUserToMessageApp(username)
                MAflag=True
            elif MAuser==2:
                print("Error connecting to Message App")
                MAflag=False
            else:
                MAflag=True
            
                

        return redirect(url_for("mainScreen"))
    else:
        return "User email not available.", 400


def process_qr_data(qr_text):
    """
    Example QR text:
      - restaurant:IST_Canteen
      - room:1234
      - USER:someusername
      - checkin:username-location
      - checkout:username
    Always return an object with a 'type' key when possible.
    """
    # --- Restaurant: "restaurant:<name>"
    if qr_text.startswith("restaurant:"):
        restaurant_name = qr_text.split("restaurant:", 1)[1].strip()
        try:
            response = requests.get(f"http://localhost:5000/api/{restaurant_name}/menu")
            if response.status_code == 200:
                data = response.json()
                menu = data.get("menu", "No menu found.")

                # Normalize menu to a list so the UI can iterate safely
                if isinstance(menu, str):
                    menu_list = [menu]
                elif isinstance(menu, list):
                    menu_list = menu
                else:
                    menu_list = []

                return {
                    "type": "restaurant",
                    "name": restaurant_name,
                    "menu": menu_list,
                    "actions": [
                        {"label": "Reserve Meal", "endpoint": "/api/user/reserve"},
                        {"label": "Rate Restaurant", "endpoint": "/api/user/rate"}
                    ]
                }
            else:
                return {"type": "error", "error": f"Error fetching menu ({response.status_code})."}
        except Exception as e:
            return {"type": "error", "error": f"Error connecting to API: {e}"}

    # --- Classroom: "room:<room_name>"
    if qr_text.startswith("room:"):
        room_name = qr_text.split("room:", 1)[1].strip()
        try:
            response = requests.get(f"http://localhost:5001/api/room/{room_name}/events")
            if response.status_code == 200:
                data = response.json()

                # Accept either {"events":[...]} or {"schedule":[...]}
                raw_events = data.get("events") or data.get("schedule") or []
                events = []
                for ev in raw_events:
                    # Keep HH:MM strings; UI will format/status them
                    start = ev.get("start_time")
                    end = ev.get("end_time")
                    events.append({
                        "course": ev.get("course"),
                        "start_time": start,
                        "end_time": end
                    })

                # Return a typed payload (also include `schedule` for templates that expect it)
                return {
                    "type": "classroom",
                    "name": room_name,
                    "events": events,
                    "schedule": events
                }
            else:
                return {"type": "error", "error": f"Error fetching schedule ({response.status_code})."}
        except Exception as e:
            return {"type": "error", "error": f"Error connecting to API: {e}"}

    # --- Add friend: "USER:<username>"
    if qr_text.startswith("USER:"):
        scanned_username = qr_text.split("USER:", 1)[1].strip()
        if addFriendToMessageApp(current_user.username, scanned_username):
            return {"type": "info", "message": f"Friend request sent to {scanned_username}."}
        else:
            return {"type": "error", "error": f"Error sending friend request to {scanned_username}."}

    # --- Fallback
    return {"type": "unknown", "raw": qr_text, "error": "Unrecognized QR code format."}

    
def reserveMeal(restaurant_name, date=None):
    """Reserve a meal at a restaurant."""
    if not date:
        date = datetime.datetime.utcnow().isoformat()
    response = requests.post(
        url=f"http://localhost:5000/api/restaurants/{restaurant_name}/reserve",
        json={"date": date},
        headers={"Content-Type": "application/json"}
    )
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Failed to reserve meal ({response.status_code})"}

@app.route("/user_courses", methods=["GET"])
@login_required
def getUserCourses():
    try:
        
        courses_endpoint = "https://fenix.tecnico.ulisboa.pt/api/fenix/v1/person/courses"
        uri, headers, body = client.add_token(courses_endpoint)
        response = requests.get(uri, headers=headers, data=body)

        enrolled_courses = response.json().get("enrolments", [])
        course_acronym = [course["acronym"] for course in enrolled_courses]
        return course_acronym
    except:
        return {"error": "Failed to fetch courses"}
        

def rateRestaurant(restaurant_name, rating):
    """Rate a restaurant by name."""
    response = requests.get(
        url=f"http://localhost:5000/api/restaurant/{restaurant_name}/{rating}"
    )
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Failed to rate restaurant ({response.status_code})"}

@app.route("/qrreaderout")
def qrreaderout():
    return render_template("QRCodeCameraOut.html")

@app.route("/qrreaderin")
def qrreaderin():
    return render_template("QRCodeCameraIn.html")

@app.route("/public_info")
def public_info():
    qr_data = request.args.get("data", None)
    message = None

    if qr_data:
        message = process_qr_data(qr_data)

    # Render your main page again, with the info included
    return render_template("loginScreen.html", public_info=message)

@app.route("/private_info")
@login_required
def private_info():
    qr_data = request.args.get("data", None)
    message = None

    if qr_data:
        message = process_qr_data(qr_data)

    # Render your main page again, with the info included
    return render_template("mainScreen.html", private_info=message)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("loginScreen"))
    
# hook up extensions to app
db.init_app(app)


@app.route("/api/user/profile", methods=["GET"])
# @login_required
def get_user_profile():
    user_data = {
        "username": current_user.username,
        "name": current_user.name
    }
    return jsonify(user_data), 200

@app.route("/api/friends", methods=["GET"])
# @login_required
def get_friends_list():
    response = requests.get(
        url=f"{MESSAGE_API_URL}/{current_user.username}/friends",
        headers={"Content-Type": "application/json"}
    )
    if response.status_code == 200:
        return response.json(), 200
    else:
        return jsonify({"error": "Failed to fetch friends list"}), 500

def addUserToMessageApp(username):
    response = requests.post(
        url=f"{MESSAGE_API_URL}/add_user",
        json={"username": username,
              "pwd": MESSAGE_APP_SECRET
        },
        headers={"Content-Type": "application/json"}
    )
    return response.status_code == 200
    
def addFriendToMessageApp(username, friendUsername):
    response = requests.post(
        url=f"{MESSAGE_API_URL}/add_friend",
        json={"username": username,
              "friend_username": friendUsername,
              "pwd": MESSAGE_APP_SECRET
        },
        headers={"Content-Type": "application/json"}
    )
    return response.status_code == 200

def messageAppIsUser(username):
    try:
        response = requests.get(
            url=f"{MESSAGE_API_URL}/User/{username}",
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            return 0
        else:
            return 1
    except:
        return 2

@app.route("/api/user/add_friend", methods=["POST"])
# @login_required
def add_friend():
    data = request.get_json()
    friend_username = data.get("friend_username")
    current_username = current_user.username
    if addFriendToMessageApp(current_username, friend_username):
        return jsonify({"message": "Friend added successfully"}), 200
    else:
        return jsonify({"error": "Failed to add friend"}), 500
    
@app.route("/api/send_message_resquest", methods=["POST"])
# @login_required
def send_message_request():
    data = request.get_json()
    sender= current_user.username
    receiver = data.get("receiver")
    message_text = data.get("message_text")
    response = requests.post(
        url=f"{MESSAGE_API_URL}/send_message",
        json={
            "sender": sender,
            "receiver": receiver,
            "content": message_text,
            "pwd": MESSAGE_APP_SECRET
        },
        headers={"Content-Type": "application/json"}
    )
    if response.status_code == 200:
        return jsonify({"message": "Message sent successfully"}), 200
    else:
        return jsonify({"error": "Failed to send message"}), 500
    
@app.route("/api/chat/<friend_username>", methods=["GET"])
# @login_required
def get_chat_with_friend(friend_username):
    current_username = current_user.username
    response = requests.get(
        url=f"{MESSAGE_API_URL}/chat/{current_username}/{friend_username}",
        headers={"Content-Type": "application/json"}
    )
    if response.status_code == 200:
        return response.json(), 200
    else:
        return jsonify({"error": "Failed to fetch chat messages"}), 500
    
@app.route("/api/user/reserve", methods=["POST"])
# @login_required
def user_reserve_meal():
    data = request.get_json()
    restaurant_name = data.get("restaurant_name")
    date = data.get("date")
    result = reserveMeal(restaurant_name, date)
    return jsonify(result)

@app.route("/api/user/rate", methods=["POST"])
# @login_required
def user_rate_meal():
    data = request.get_json()
    restaurant_name = data.get("restaurant_name")
    rating = data.get("rating")
    result = rateRestaurant(restaurant_name, rating)
    return jsonify(result)

# ---------- Attendance: explicit endpoints the UI can call ----------

@app.route("/api/user/checkin", methods=["POST"])
def api_user_checkin():
    """
    Body JSON: { "username": "<user>", "location": "<room or place>" }
    Proxies to http://localhost:8000/api/checkin and returns a uniform JSON:
    { "type": "info"|"error", "message"?: str, "error"?: str }
    """
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    location = (payload.get("location") or "").strip()

    if not username or not location:
        return jsonify({"type": "error", "error": "username and location are required"}), 400

    try:
        result = requests.post(
            url="http://localhost:8000/api/checkin",
            json={"username": username, "location": location},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
    except Exception as e:
        return jsonify({"type": "error", "error": f"Upstream error: {e}"}), 502

    if result.status_code == 200:
        now_hhmm = datetime.datetime.now().strftime("%H:%M")
        return jsonify({
            "type": "info",
            "message": f"✅ Check-in successful for {username} at **{location}** ({now_hhmm})."
        }), 200
    else:
        # be defensive if upstream isn't JSON
        try:
            err_msg = result.json().get("error", result.text)
        except Exception:
            err_msg = result.text
        return jsonify({"type": "error", "error": err_msg}), result.status_code


@app.route("/api/user/checkout", methods=["POST"])
def api_user_checkout():
    """
    Body JSON: { "username": "<user>" }
    Proxies to http://localhost:8000/api/checkout and returns a uniform JSON:
    { "type": "info"|"error", "message"?: str, "error"?: str }
    """
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()

    if not username:
        return jsonify({"type": "error", "error": "username is required"}), 400

    try:
        result = requests.post(
            url="http://localhost:8000/api/checkout",
            json={"username": username},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
    except Exception as e:
        return jsonify({"type": "error", "error": f"Upstream error: {e}"}), 502

    if result.status_code == 200:
        now_hhmm = datetime.datetime.now().strftime("%H:%M")
        return jsonify({
            "type": "info",
            "message": f"✅ Check-out successful for {username} ({now_hhmm})."
        }), 200
    else:
        try:
            err_msg = result.json().get("error", result.text)
        except Exception:
            err_msg = result.text
        return jsonify({"type": "error", "error": err_msg}), result.status_code

#################################UTILITY FUNCTIONS####################################

def deleteUser(id):
    user = User.query.get(id)
    if user:
        db.session.delete(user)
        db.session.commit()
        return True
    return False

@app.route("/bots/create/<int:number_of_bots>")
def create_bots(number_of_bots):
    
    for i in range(number_of_bots):
        bot_username = f"bot{i}"
        bot_name = f"Bot{i} Botson"
        bot_email = f"bot{i}@bot"
        bot = User(username=bot_username, name=bot_name, email=bot_email)
        db.session.add(bot)
        addUserToMessageApp(bot_username)

    db.session.commit()
    return 

def removeBots():
    users = db.session.query(User).filter(User.username.startswith("bot")).all()
    for user in users:

        db.session.delete(user)
    db.session.commit()
    return

if __name__ == "__main__":
    app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

    with app.app_context():
        db.create_all()
        db.session.commit()

    
    #removeBots()


    # print("Database tables created")
    app.run(port=5100, debug=True, ssl_context="adhoc")