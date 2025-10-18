from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Date
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from flask import request, redirect, url_for
import datetime
from sqlalchemy.orm import sessionmaker
from os import path

from flask import Flask, jsonify
from flask import render_template
from flask_xmlrpcre.xmlrpcre import *
import time as t

#SLQ access layer initialization
DATABASE_FILE = "db/roomdb.sqlite"
db_exists = False
if path.exists(DATABASE_FILE):
    db_exists = True
    print("\t database already exists")

engine = create_engine('sqlite:///%s'%(DATABASE_FILE), echo=False) #echo = True shows all SQL calls

Base = declarative_base()

class Room(Base):
    __tablename__ = 'room'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    capacity = Column(Integer) 
    schedule= Column(String)
    def __repr__(self):
        return "<Room(id=%d name='%s', capacity='%d', schedule='%s')>" % (
                                self.id, self.name, self.capacity, self.schedule)
    
Base.metadata.create_all(engine) #Create tables for the data models

Session = sessionmaker(bind=engine)
session = Session()

def listRooms():
    return session.query(Room).all()

def getRoom(roomID):
    return session.query(Room).filter(Room.id == roomID).first()

def getRoomByName(roomName):
    return session.query(Room).filter(Room.name == roomName).first()

def addRoom(name, capacity, schedule):
    if  not getRoomByName(name):
        room = Room(name=name, capacity=capacity, schedule=schedule)
        session.add(room)
        session.commit()

def updateSchedule(roomID, newSchedule):
    room = getRoom(roomID)
    if room:
        room.schedule = newSchedule
        session.commit()
        return True
    return False

app = Flask(__name__)

@app.route("/")
def index():
    print(listRooms())
    rooms = listRooms()
    return render_template("roomLayout.html", rooms=rooms)  # Ensure the file exists in the templates folder

handler = XMLRPCHandler('api')
handler.connect(app, '/api')

@handler.register
def add_room(name, capacity, room_schedule):
    addRoom(name=name, capacity=int(capacity),schedule=room_schedule)
    return "Room added successfully"

@handler.register
def list_all_rooms():
    rooms = listRooms()
    result = ''
    for r in rooms:
        result += '%s %s %s %s\n' % (str(r.id), r.name, str(r.capacity), r.schedule)
    return result

@handler.register
def update_schedule(roomName, newSchedule):
    room = getRoomByName(roomName)
    if room:
        updateSchedule(int(room.id), newSchedule)
        return "Schedule updated successfully"
    else:
        return "Room not found"

@app.route("/submit_room", methods=["POST"])
def submit_room():
    
    room_name = request.form.get("roomName")
    room_capacity = request.form.get("roomCapacity")
    room_schedule = request.form.get("roomSchedule")
    addRoom(name=room_name, capacity=int(room_capacity), schedule=room_schedule)
    return redirect(url_for('index'))

@app.route("/update_schedule", methods=["POST"])
def update_schedule_form():
    room_id = request.form.get("roomID")
    new_schedule = request.form.get("newSchedule")
    if updateSchedule(name, new_schedule):
        return redirect(url_for('index'))
    else:
        return "Room not found", 404

#project 2 - REST API


@app.route('/api/<string:room_name>/schedule', methods=['GET'])
def api_get_schedule_by_name(room_name):
    room = getRoomByName(room_name)
    if room:
        return jsonify({'menu': room.schedule})
    else:
        return jsonify({'error': 'Restaurant not found'}), 404

# @app.route('/api/restaurant/<string:restaurant_name>/<int:rating> ', methods=['GET'])
# def api_update_rating(restaurant_name, rating):
#     restaurant = getRoomByName(restaurant_name)
#     if restaurant:
#         total = restaurant.rating * restaurant.number_of_ratings + rating
#         restaurant.number_of_ratings += 1
#         restaurant.rating = total / restaurant.number_of_ratings
#         session.commit()
#         return jsonify({'message': 'Rating updated successfully', 'new_rating': restaurant.rating})
#     else:
#         return jsonify({'error': 'Restaurant not found'}), 404
    
# @app.route('/api/reserve/<string:restaurant_name>', methods=['POST'])
# def api_reserve_table(restaurant_name):
#     restaurant = getRestaurantByName(restaurant_name)
    
#     if restaurant:
#         restaurant.nr_reservations += 1
#         time = request.get_json('date')['date']
#         new_reservation = Reservation(restaurant_id=restaurant.id, date=datetime.datetime.fromisoformat(time))
#         session.add(new_reservation)
        
#         session.commit()
#         return jsonify({'message': 'Reservation added successfully', 'total_reservations': restaurant.reservations})
#     else:
#         return jsonify({'error': 'Restaurant not found'}), 404

if __name__ == "__main__":

    if not db_exists:
        print("Creating database")
        addRoom(name="1.1'", capacity=20, schedule="9-20")
        addRoom(name="1.2", capacity=30, schedule="10-18")
        addRoom(name="1.3", capacity=22, schedule="10-18")
    
    app.run(port=5001, debug=True)

        