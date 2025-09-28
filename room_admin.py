
from flask import Flask
from flask import render_template
from flask import request, redirect, url_for

import time as t
from xmlrpc import client

from xmlrpc import client
proxy =client.ServerProxy("http://localhost:5001/api")

""" 
while True:
    print("\nChoose an option:")
    print("1. Create Restaurant")
    print("2. List Restaurants")
    print("3. Update Menu")
    print("4. Show Evaluations")
    print("q. Quit")
    
    choice = input("Enter your choice: ")
    
    if choice == 'q':
        break
    elif choice == '1':
        name, capacity, schedule = input("Enter the name, capacity, and schedule (separated by spaces): ").split()
        print(proxy.add_room((name, int(capacity), schedule)))
    elif choice == '2':
        print(proxy.list_all_rooms())
    elif choice == '3':
        room_id = input("Enter the room ID to update the schedule: ")
        new_schedule = input("Enter the new schedule: ")
        print(proxy.update_schedule(int(room_id), new_schedule))
    else:
        print("Invalid choice. Please try again.")
 """



class Room:
    def __init__(self, name, capacity, schedule):
        self.name = name
        self.capacity = capacity
        self.schedule = schedule
        


app = Flask(__name__)
innit_time = t.time()

@app.route('/')
def hello_world():
    return render_template("roomAdminIndex.html")


@app.route('/createRoom')
def create_room():
    return render_template("roomAdminCreate.html")

@app.route('/create', methods=["POST"])
def submit_room():
    
    room_name = request.form.get("name")
    room_capacity = request.form.get("capacity")
    room_schedule = request.form.get("schedule")
    proxy.add_room(room_name, int(room_capacity), room_schedule)
    return redirect(url_for('create_room'))

@app.route('/list')
def list_rooms():
    result = proxy.list_all_rooms()

    rooms = []
    for line in result.strip().split('\n'):
        id, name, capacity, schedule = line.split()
        rooms.append(Room(name, int(capacity), schedule))

    print(rooms)
    return render_template("roomAdminList.html",rooms=rooms)

@app.route('/updateSchedule')
def update_room():
    return render_template("roomAdminUpdateSchedule.html")

@app.route('/update_room_schedule', methods=["POST"])
def update_schedule_form():
    room_name = request.form.get("room_name")
    new_schedule = request.form.get("schedule")
    print(room_name, new_schedule)
    print(proxy.update_schedule(room_name, new_schedule))
    return redirect(url_for('update_room'))

if __name__ == '__main__':
    app.run(port=5007, debug=True)


