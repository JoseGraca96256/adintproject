from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Date
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from flask import request, redirect, url_for
import datetime
from sqlalchemy.orm import sessionmaker
from os import path
import requests


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

IST_API_SPACES_URL = 'https://fenix.tecnico.ulisboa.pt/api/fenix/v1/spaces/'

engine = create_engine('sqlite:///%s'%(DATABASE_FILE), echo=False) #echo = True shows all SQL calls

Base = declarative_base()


class Room(Base):
    __tablename__ = 'room'
    id = Column(Integer, primary_key=True)
    tecnico_id = Column(Integer, nullable=False) 
    name = Column(String,nullable=False)
    capacity = Column(Integer) 
    schedule= Column(String)
    room_type = Column(String, default='study')
    def __repr__(self):
        return f"<Room(id={self.id} name='{self.name}', capacity='{self.capacity}', schedule='{self.schedule}', room_type='{self.room_type}')>"
    
class Event(Base):
    __tablename__ = 'event'
    id = Column(Integer, primary_key=True)
    course= Column(String, nullable=False)
    start_time= Column(String, nullable=False)
    end_time= Column(String, nullable=False)
    event_type = Column(String, default='lecture')
    room_id = Column(Integer, ForeignKey('room.id'), nullable=False)
    date = Column(Date, nullable=False)
    room = relationship ("Room", back_populates="events")
    def __repr__(self):
        return f"<Event(id={self.id} room_id='{self.room_id}', date='{self.date}', name='{self.name}')>"

Room.events = relationship(
    "Event", order_by=Event.date, back_populates="room")



Base.metadata.create_all(engine) #Create tables for the data models

Session = sessionmaker(bind=engine)
session = Session()

def listRooms():
    return session.query(Room).all()

def getRoom(roomID):
    return session.query(Room).filter(Room.id == roomID).first()

def getRoomByTecnicoID(tecnicoID):
    return session.query(Room).filter(Room.tecnico_id == tecnicoID).first()
def getRoomByName(roomName):
    return session.query(Room).filter(Room.name == roomName).first()

def addRoom(name,  tecnico_id, room_type='study', capacity=0, schedule="0"):
    new_room = Room(name=name, tecnico_id=tecnico_id, room_type=room_type, capacity=capacity, schedule=schedule)
    session.add(new_room)
    session.commit()
    return new_room

def updateSchedule(roomID, newSchedule):
    room = getRoom(roomID)
    if room:
        room.schedule = newSchedule
        session.commit()
        return True
    return False

app = Flask(__name__)

def add_event(course, start_time, end_time, event_type, room_id, date):
    new_event = Event(course=course, start_time=start_time, end_time=end_time, event_type=event_type, room_id=room_id, date=date)
    session.add(new_event)
    session.commit()
    return new_event

def scrape_schedule_from_web(room_tecnico_id):
    rest_url= IST_API_SPACES_URL + str(room_tecnico_id) 
    response= requests.get(
                            url=rest_url,
                            headers={"Content-Type": "application/json"}
                            )
    if response.status_code == 200:
        data = response.json()
        
        # Get or create room
        room = getRoomByName(data.get('name'))

        events = data.get('events', [])

        if not events:
            room_type = 'study'
        else:
            room_type = 'class'

        if not room:
            capacity = data.get('capacity', {}).get('normal', 0)
            room = addRoom(
                name=data.get('name'),
                tecnico_id=int(data.get('id')),
                room_type=room_type,
                capacity=capacity
            )
        
        # Parse events
       
          
        for event_data in events:
            # Parse date from "21/10/2025 10:00" format
            period = event_data.get('period', {})
            start_datetime = period.get('start', '')
            
            # Convert "21/10/2025 10:00" to datetime
            try:
                date_obj = datetime.datetime.strptime(start_datetime.split()[0], '%d/%m/%Y').date()
            except:
                continue
            
            # Get course info
            course_info = event_data.get('course', {})
            if course_info:
                course_name = f"{course_info.get('acronym', '')} - {course_info.get('name', '')}"
            else:
                course_name = event_data.get('title', 'Generic Event')
            
            # Add event
            add_event(
                course=course_name,
                start_time=event_data.get('start', ''),
                end_time=event_data.get('end', ''),
                event_type=event_data.get('type', 'lesson').lower(),
                room_id=room.id,
                date=date_obj
            )
        
        return {'success': True, 'room': room.name, 'events_added': len(events)}
    else:
        print(f"Error fetching schedule for room {room_tecnico_id}: {response.status_code}")
        return {'success': False, 'error': response.status_code}



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

@app.route('/api/room/<string:room_name>/schedule', methods=['GET'])
def api_get_schedule_by_name(room_name):
    room = getRoomByName(room_name)
    if room:
        return jsonify({'menu': room.schedule})
    else:
        return jsonify({'error': 'Restaurant not found'}), 404

@app.route('/api/scrape/<int:room_tecnico_id>', methods=['GET'])
def api_scrape_schedule(room_tecnico_id):
    result = scrape_schedule_from_web(room_tecnico_id)
    if result['success']:
        return jsonify({'message': f"Schedule scraped successfully for room {result['room']}", 'events_added': result['events_added']})
    else:
        return jsonify({'error': f"Failed to scrape schedule: {result['error']}"}), 500
    

@app.route('/api/room/<int:room_id>/internal_id', methods=['GET'])
def api_get_events_by_room_id(room_id):
    room = getRoom(room_id)
    for event in room.events:
        print(event.course, event.date, event.start_time, event.end_time)
    return jsonify({'events': [{'course': event.course, 'date': event.date.isoformat(), 'start_time': event.start_time, 'end_time': event.end_time} for event in room.events]})

@app.route('/api/room/<int:room_tecnico_id>/events', methods=['GET', 'POST','DELETE'])
def api_get_events_by_room_tecnico_id(room_tecnico_id):
    if request.method == 'GET':
        room = getRoomByTecnicoID(room_tecnico_id)
        for event in room.events:
            print(event.course, event.date, event.start_time, event.end_time)
        return jsonify({'events': [{'course': event.course, 'date': event.date.isoformat(), 'start_time': event.start_time, 'end_time': event.end_time} for event in room.events]})
    if request.method == 'POST':
        data = request.get_json()
        course = data.get('course')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        event_type = data.get('event_type')
        date_str = data.get('date')
        date = datetime.datetime.fromisoformat(date_str).date()
        room = getRoomByTecnicoID(room_tecnico_id)
        if room:
            new_event = add_event(course, start_time, end_time, event_type, room.id, date)
            if room.room_type != 'class':
                room.room_type = 'class'
                session.commit()    
            return jsonify({'message': 'Event added successfully', 'event_id': new_event.id})
        else:
            return jsonify({'error': 'Room not found'}), 404
    if request.method == 'DELETE':
        data = request.get_json()
        date_str = data.get('date')
        date = datetime.datetime.fromisoformat(date_str).date()
        room = getRoomByTecnicoID(room_tecnico_id)
        start_time = data.get('start_time')
        course = data.get('course')
        if room:
            event = session.query(Event).filter(Event.room_id == room.id, Event.date == date, Event.start_time == start_time, Event.course == course).first()
            if event:
                session.delete(event)
                session.commit()
                if not room.events:
                    room.room_type = 'study'
                    session.commit()
                return jsonify({'message': 'Event deleted successfully'})
            else:
                return jsonify({'error': 'Event not found'}), 404
        else:
            return jsonify({'error': 'Room not found'}), 404


@app.route('/api/room/<int:room_tecnico_id>', methods=['GET','POST'])
def room_info(room_tecnico_id):
    if request.method == 'GET':
        room = getRoomByTecnicoID(room_tecnico_id)
        if room:
            return jsonify({
                'id': room.id,
                'name': room.name,
                'capacity': room.capacity,
                'schedule': room.schedule,
                'room_type': room.room_type
            })
        else:
            return jsonify({'error': 'Room not found'}), 404
        
    if request.method == 'POST':
        data = request.get_json()
        tecnico_id = data.get('tecnico_id')
        name = data.get('name')
        capacity = data.get('capacity')
        schedule = data.get('schedule')
        if getRoomByTecnicoID(room_tecnico_id):
            return jsonify({'error': 'Room with this tecnico_id already exists'}), 400
        if addRoom(name, tecnico_id, capacity=capacity, schedule=schedule):
            return jsonify({'message': 'Room added successfully'})
        else:
            return jsonify({'error': 'Failed to add room'}), 500



@app.route('/api/room/<string:room_name>', methods=['GET'])
def room_info_by_name(room_name):
    room = getRoomByName(room_name)
    if room:
        return jsonify({
            'id': room.id,
            'name': room.name,
            'capacity': room.capacity,
            'schedule': room.schedule,
            'room_type': room.room_type,
            'tecnico_id': room.tecnico_id
        })
    else:
        return jsonify({'error': 'Room not found'}), 404



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

    if not db_exists or session.query(Room).count() == 0:
        print("Creating database")
        addRoom(name="EA1", tecnico_id=2448131362971, room_type='class')
        addRoom(name="EA2", tecnico_id=2448131362979, room_type='class')
        addRoom(name="EA3", tecnico_id=2448131362989, room_type='class')

    #scrape_schedule_from_web(2448131362990)

    app.run(port=5001, debug=True)

        