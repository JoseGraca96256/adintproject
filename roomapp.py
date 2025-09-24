from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Date
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

import datetime
from sqlalchemy.orm import sessionmaker
from os import path

from flask import Flask
from flask import render_template
from flask_xmlrpcre.xmlrpcre import *
import time as t

#SLQ access layer initialization
DATABASE_FILE = "roomdb.sqlite"
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

def addRoom(name, capacity, schedule):
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

@app.route("/index")
def index():
    rooms = listRooms()
    return render_template("roomLayout.html", rooms)  # Ensure the file exists in the templates folder

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
        result += 'id: %d, name: %s, capacity: %d, schedule: %s\n' % (r.id, r.name, r.capacity, r.schedule)
    return result

@handler.register
def update_schedule(roomID, newSchedule):
    if updateSchedule(int(roomID), newSchedule):
        return "Schedule updated successfully"
    else:
        return "Room not found"
    
if __name__ == "__main__":

    if not db_exists:
        print("Creating database")
        addRoom(name="1.1'", capacity=20, schedule="9-20")
        addRoom(name="1.2", capacity=30, schedule="10-18")
        addRoom(name="1.3", capacity=22, schedule="10-18")
    
    app.run(port=5001)

        