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
DATABASE_FILE = "fooddb.sqlite"
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
    rating = Column(Integer)
    def __repr__(self):
        return "<Restaurant(id=%d name='%s', reservations='%d', menu='%s', rating='%d')>" % (
                                self.id, self.name, self.reservations, self.menu, self.rating)
    


Base.metadata.create_all(engine) #Create tables for the data models

Session = sessionmaker(bind=engine)
session = Session()


def listRestaurants():
    rating = Column(Integer)
    return session.query(Restaurant).all()

def getRestaurant(restaurantID):
    return session.query(Restaurant).filter(Restaurant.id == restaurantID).first()

def addRestaurant(name, reservations, menu, rating):
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
    return render_template("index.html")
 
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
        result += '%s %s %s %d\n' % (str(r.id), r.name, r.menu, r.rating)
    
    return result

@handler.register
def get_id_by_name(restaurant_name):
    restaurant = session.query(Restaurant).filter(Restaurant.name == restaurant_name).first()
    if restaurant:
        return restaurant.id
    else:
        return "Restaurant not found"

@handler.register
def show_ratings():
    restaurants = listRestaurants()
    result = ''
    for r in restaurants:
        result += ' name: %s, rating: %d\n' % ( r.name, r.rating)
    return result

if __name__ == "__main__":
    
    if not db_exists:
        addRestaurant("segredo", 0, "picanha",3)
        addRestaurant("india", 0, "tikamassala",4)
        addRestaurant("sushi", 15, "sashimi",5)

    """ 
    #queries
    print("\nall restaurants")
    lRestaurants = session.query(Restaurant).all()
    print(lRestaurants)
    print(listRestaurants())
 """
    print("\nall restaurants")
    lRestaurants = session.query(Restaurant).all()
    print(lRestaurants)
    print(listRestaurants())
    print("\nrestaurants with reservations greater than 10")
    busyRestaurants = session.query(Restaurant).filter(Restaurant.reservations > 10).all()
    for r in busyRestaurants:
        print(r.id, r.name, r.reservations, r.menu)
    app.run()

    


    