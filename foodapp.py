from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Date, Float
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from flask import Flask, jsonify

import datetime
from sqlalchemy.orm import sessionmaker
from os import path

from flask import render_template
from flask_xmlrpcre.xmlrpcre import *
from flask import request, redirect, url_for
import time as t


#SLQ access layer initialization
DATABASE_FILE = "db/fooddb.sqlite"
db_exists = False
if path.exists(DATABASE_FILE):
    db_exists = True
    print("\t database already exists")

engine = create_engine('sqlite:///%s'%(DATABASE_FILE), echo=False) #echo = True shows all SQL calls

Base = declarative_base()



class Restaurant(Base):
    __tablename__ = 'restaurant'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    reservations = Column(Integer) 
    menu= Column(String)
    rating = Column(Float, default=0)
    number_of_ratings = Column(Integer, default=0)
    def __repr__(self):
        return "<Restaurant(id=%d name='%s', reservations='%d', menu='%s', rating='%f',number_of_ratings='%d')>" % (
                                self.id, self.name, self.reservations, self.menu, self.rating, self.number_of_ratings)
    
class Reservation:
    __tablename__ = 'reservation'
    id = Column(Integer, primary_key=True)
    restaurant = relationship ("Restaurant")


Base.metadata.create_all(engine) #Create tables for the data models

Session = sessionmaker(bind=engine)
session = Session()


def listRestaurants():
    return session.query(Restaurant).all()

def getRestaurant(restaurantID):
    return session.query(Restaurant).filter(Restaurant.id == restaurantID).first()

def addRestaurant(name, reservations, menu, rating):
    if  not getRestaurantByName(name):
        restaurant = Restaurant(name=name, reservations=reservations, menu=menu, rating=rating)
        session.add(restaurant)
        session.commit()

def updateReservations(restaurantID, newReservations):
    restaurant = getRestaurant(restaurantID)
    if restaurant:
        restaurant.reservations = newReservations
        session.commit()

def updateMenu(restaurantID, newMenu):
    restaurant = getRestaurant(restaurantID)
    if restaurant:
        restaurant.menu = newMenu
        session.commit()

def getRestaurantByName(restaurantName):
    return session.query(Restaurant).filter(Restaurant.name == restaurantName).first()

def removeRestaurantByName(name):
    restaurant = (session.query(Restaurant)
                  .filter(Restaurant.name == name)
                  .order_by(Restaurant.id.desc())
                  .first())
    if restaurant:
        session.delete(restaurant)
        session.commit()
        return True
    return False
    
def removeRestaurant(restaurantID):
    restaurant = getRestaurant(restaurantID)
    if restaurant:
        session.delete(restaurant)
        session.commit()
        return True
    return False

""" 
def getBooksfromAuthor(authorID):
    author = session.query(Author).filter(Author.id==1).first()
    return author.books

def newAuthor(name , year, mounth, day):
    auth = Author(name = name, dateBirth = datetime.date(year, mounth, day))
    session.add(auth)
    session.commit()
"""
""" 
def newBook(authorID, isbn, title , publisher):
    book1 = Book(isbn = isbn, title = title, publisher=publisher, reserved = False, author_id = authorID)
    session.add(book1)
    session.commit()

def changeReserveState(bookID, newState):
    b = getBook(bookID)
    b.reserved = newState
    session.commit()
 """

app = Flask(__name__)
innit_time = t.time()
@app.route('/')
def hello_world():
    restaurants = listRestaurants()
    return render_template("foodAppIndex.html", restaurants=restaurants)  
 
@app.route('/restaurant/<int:restId>')
def restaurant_detail(restId):
    restaurant = getRestaurant(restId)
    if restaurant:
        return render_template("foodAppRestDetails.html", restaurant=restaurant)
    else:
        return "Restaurant not found", 404


@app.route('/rate', methods=["POST"])
def rate_restaurant():
    rest_id = int(request.form.get("restId"))
    new_rating = int(request.form.get("rating"))
    restaurant = getRestaurant(rest_id)
    if restaurant:
        total = restaurant.rating * restaurant.number_of_ratings + new_rating
        restaurant.number_of_ratings += 1
        restaurant.rating = total / restaurant.number_of_ratings
        session.commit()
        return redirect(url_for('restaurant_detail', restId=rest_id))
    else:
        return "Restaurant not found", 404
    
handler = XMLRPCHandler('api')
handler.connect(app, '/api')


@handler.register
def get_menu_by_id(restaurant_id):
    restaurant = getRestaurant(restaurant_id)
    if restaurant:
        return restaurant.menu
    else:
        return "Restaurant not found"

@handler.register
def get_rating_by_id(restaurant_id):
    restaurant = getRestaurant(restaurant_id)
    if restaurant:
        return restaurant.rating
    else:
        return "Restaurant not found"
    
@handler.register
def add_restaurant(name, reservations, menu, rating):
    addRestaurant(name, reservations, menu, rating)
    return "Restaurant added successfully"

@handler.register
def update_menu(restaurantID, newMenu):
    updateMenu(restaurantID, newMenu)
    return "Menu updated successfully"



@handler.register
def list_all_restaurants():
    restaurants = listRestaurants()
    result = ''
    
    for r in restaurants:
        result += '%s %s %s %.2f\n' % (str(r.id), r.name, r.menu, r.rating)
    
    return result
@handler.register
def get_id_by_name(restaurant_name):
    restaurant = session.query(Restaurant).filter(Restaurant.name == restaurant_name).first()
    if restaurant:
        return restaurant.id
    else:
        return -1


@handler.register
def show_ratings():
    restaurants = listRestaurants()
    result = ''
    for r in restaurants:
        result += ' name: %s, rating: %.2f\n' % ( r.name, r.rating)
    return result

@handler.register
def remove_restaurant_by_name(name):
    if removeRestaurantByName(name):
        return "Restaurant removed successfully"
    else:
        return "Restaurant not found"
    
@handler.register
def remove_restaurant_by_id(restaurantID):
    if removeRestaurant(restaurantID):
        return "Restaurant removed successfully"
    else:
        return "Restaurant not found"


#project 2 - REST API


@app.route('/api/<string:restaurant_name>/menu', methods=['GET'])
def api_get_menu_by_name(restaurant_name):
    restaurant = getRestaurantByName(restaurant_name)
    if restaurant:
        return jsonify({'menu': restaurant.menu})
    else:
        return jsonify({'error': 'Restaurant not found'}), 404

@app.route('/api/restaurant/<string:restaurant_name>/<int:rating> ', methods=['GET'])
def api_update_rating(restaurant_name, rating):
    restaurant = getRestaurantByName(restaurant_name)
    if restaurant:
        total = restaurant.rating * restaurant.number_of_ratings + rating
        restaurant.number_of_ratings += 1
        restaurant.rating = total / restaurant.number_of_ratings
        session.commit()
        return jsonify({'message': 'Rating updated successfully', 'new_rating': restaurant.rating})
    else:
        return jsonify({'error': 'Restaurant not found'}), 404
    
@app.route('/api/reserve/<string:restaurant_name>', methods=['PUT'])
def api_reserve_table(restaurant_name):
    restaurant = getRestaurantByName(restaurant_name)
    if restaurant:
        restaurant.reservations += 1
        time = request.get_json()

        
        session.commit()
        return jsonify({'message': 'Reservation added successfully', 'total_reservations': restaurant.reservations})
    else:
        return jsonify({'error': 'Restaurant not found'}), 404

        

        


if __name__ == "__main__":
    
    if not db_exists:
        addRestaurant("segredo", 0, "picanha",3)
        addRestaurant("india", 0, "tikamassala",4)
        addRestaurant("sushi", 15, "sashimi",5)

    print("\nall restaurants")
    lRestaurants = session.query(Restaurant).all()
    print(lRestaurants)
    print(listRestaurants())
    print("\nrestaurants with reservations greater than 10")
    busyRestaurants = session.query(Restaurant).filter(Restaurant.reservations > 10).all()
    for r in busyRestaurants:
        print(r.id, r.name, r.reservations, r.menu)
    app.run(port=5000, debug=True)

    


    