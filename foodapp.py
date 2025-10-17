from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Date, Float, DateTime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, declarative_base
from flask import Flask, jsonify

import datetime
from sqlalchemy.orm import sessionmaker
from os import path

from flask import render_template
from flask_xmlrpcre.xmlrpcre import *
from flask import request, redirect, url_for
import time as t
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

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
    nr_reservations = Column(Integer) 
    menu= Column(String)
    rating = Column(Float, default=0)
    number_of_ratings = Column(Integer, default=0)
    def __repr__(self):
        return "<Restaurant(id=%d name='%s', nr_reservations='%d', menu='%s', rating='%f',number_of_ratings='%d')>" % (
                                self.id, self.name, self.nr_reservations, self.menu, self.rating, self.number_of_ratings)
    
class Reservation(Base):
    __tablename__ = 'reservation'
    id = Column(Integer, primary_key=True)
    restaurant_id = Column(Integer, ForeignKey('restaurant.id'), nullable=False)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    restaurant = relationship ("Restaurant", back_populates="reservations")
    def __repr__(self):
        return "<Reservation(id=%d restaurant_id='%d', date='%s')>" % (
                                self.id, self.restaurant_id, str(self.date))
    
    
Restaurant.reservations = relationship(
    "Reservation", order_by=Reservation.date, back_populates="restaurant")


Base.metadata.create_all(engine) #Create tables for the data models

Session = sessionmaker(bind=engine)
session = Session()


def listRestaurants():
    return session.query(Restaurant).all()

def getRestaurant(restaurantID):
    return session.query(Restaurant).filter(Restaurant.id == restaurantID).first()

def addRestaurant(name, reservations, menu, rating):
    if  not getRestaurantByName(name):
        restaurant = Restaurant(name=name, nr_reservations=reservations, menu=menu, rating=float(rating))
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
    
@app.route('/api/reserve/<string:restaurant_name>', methods=['POST'])
def api_reserve_table(restaurant_name):
    restaurant = getRestaurantByName(restaurant_name)
    
    if restaurant:
        restaurant.nr_reservations += 1
        time = request.get_json('date')['date']
        new_reservation = Reservation(restaurant_id=restaurant.id, date=datetime.datetime.fromisoformat(time))
        session.add(new_reservation)
        
        session.commit()
        return jsonify({'message': 'Reservation added successfully', 'total_reservations': restaurant.reservations})
    else:
        return jsonify({'error': 'Restaurant not found'}), 404

def cleanup_old_reservations():
    old_reservations = session.query(Reservation).filter(Reservation.date < datetime.datetime.utcnow() ).all()
    for reservation in old_reservations:
        reservation.restaurant.nr_reservations -= 1
        session.delete(reservation)
    session.commit()

scheduler = BackgroundScheduler()

scheduler.add_job(func=cleanup_old_reservations(), trigger="interval", hours=1)


if __name__ == "__main__":
    
    if not db_exists:
        addRestaurant("segredo", 0, "picanha",3.0)
        addRestaurant("india", 0, "tikamassala",4.0)
        addRestaurant("sushi", 0, "sashimi",5.0)
    elif session.query(Restaurant).count() == 0:
        addRestaurant("segredo", 0, "picanha",3.0)
        addRestaurant("india", 0, "tikamassala",4.0)
        addRestaurant("sushi", 0, "sashimi",5.0)
    else:
        print("\t database ready to use")
 
    app.run(port=5000, debug=True)

    


    