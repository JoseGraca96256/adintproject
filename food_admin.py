
from flask import Flask
from flask import render_template
from flask import request, redirect, url_for

import time as t
from xmlrpc import client
proxy =client.ServerProxy("http://localhost:5000/api")


app = Flask(__name__)
innit_time = t.time()

class Restaurant:
    def __init__(self, id, name, menu, rating):
        self.id = id
        self.name = name
        self.menu = menu
        self.rating = rating

@app.route('/')
def hello_world():
    result = proxy.list_all_restaurants()

    rests = []
    for line in result.strip().split('\n'):
        id, name, menu, rating = line.split()
        rests.append(Restaurant(id, name, menu, float(rating)))

    print(rests)
    return render_template("foodAdminIndex.html",restaurants=rests)

@app.route('/list')
def list_restaurants():
    result = proxy.list_all_restaurants()

    rests = []
    for line in result.strip().split('\n'):
        id, name, menu, rating = line.split()
        rests.append(Restaurant(id, name, menu, float(rating)))

    print(rests)
    return render_template("foodAdminList.html",restaurants=rests)


@app.route('/add')
def add_rest():
    return render_template("foodAdminAddRestaurant.html")

@app.route("/addRestaurant", methods=["POST"])
def submit_restaurant():
    restaurant_name = request.form.get("name")
    restaurant_menu = request.form.get("menu")
    restaurant_reservation = request.form.get("reservations")
    restaurant_rating = request.form.get("rating")
    proxy.add_restaurant(restaurant_name, int(restaurant_reservation), restaurant_menu, float(restaurant_rating))
    print('done')
    return redirect(url_for('add_rest'))



@app.route('/update')
def update_restaurant():
    return render_template("foodAdminUpdateMenu.html")

@app.route("/update_menu", methods=["POST"])
def update_schedule_form():
    restaurant_name = request.form.get("name")
    new_menu = request.form.get("menu")
    rID = proxy.get_id_by_name(restaurant_name)
    if rID == -1:
        redirect(url_for('update_restaurant'))
    proxy.update_menu(int(rID), new_menu)
    return redirect(url_for('update_restaurant'))
    
@app.route('/showRating')
def show_ratings():
    result = proxy.list_all_restaurants()
    print(result)
    rests = []
    for line in result.strip().split('\n'):
        id, name, menu, rating = line.split()
        rests.append(Restaurant(id, name, menu, float(rating)))
    return render_template("foodAdminShowRatings.html",restaurants=rests)


if __name__ == "__main__":
    app.run(port=5003, debug=True)
