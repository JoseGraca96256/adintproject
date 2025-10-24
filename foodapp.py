from sqlalchemy import create_engine, Column, Integer, String, Date, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from flask import Flask, jsonify, render_template, request, redirect, url_for
from flask_xmlrpcre.xmlrpcre import XMLRPCHandler
import datetime
import time as t
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
from os import path

# -----------------------------
# SQL Access Layer Initialization
# -----------------------------
DATABASE_FILE = "db/fooddb.sqlite"
db_exists = path.exists(DATABASE_FILE)

engine = create_engine(f"sqlite:///{DATABASE_FILE}", echo=False)
Base = declarative_base()

SessionFactory = sessionmaker(bind=engine)

# -----------------------------
# Database Models
# -----------------------------
class Restaurant(Base):
    __tablename__ = 'restaurant'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    nr_reservations = Column(Integer)
    menu = Column(String)
    rating = Column(Float, default=0)
    number_of_ratings = Column(Integer, default=0)

    reservations = relationship("Reservation", order_by="Reservation.date", back_populates="restaurant")

    def __repr__(self):
        return f"<Restaurant(id={self.id}, name='{self.name}', nr_reservations={self.nr_reservations}, menu='{self.menu}', rating={self.rating}, number_of_ratings={self.number_of_ratings})>"


class Reservation(Base):
    __tablename__ = 'reservation'
    id = Column(Integer, primary_key=True)
    restaurant_id = Column(Integer, ForeignKey('restaurant.id'), nullable=False)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    restaurant = relationship("Restaurant", back_populates="reservations")

    def __repr__(self):
        return f"<Reservation(id={self.id}, restaurant_id={self.restaurant_id}, date='{self.date}')>"


Base.metadata.create_all(engine)

# -----------------------------
# Helper Functions (Each Uses Its Own Session)
# -----------------------------
def listRestaurants():
    with SessionFactory() as session:
        return session.query(Restaurant).all()


def getRestaurant(restaurantID):
    with SessionFactory() as session:
        return session.query(Restaurant).filter(Restaurant.id == restaurantID).first()


def getRestaurantByName(restaurantName):
    with SessionFactory() as session:
        return session.query(Restaurant).filter(Restaurant.name == restaurantName).first()


def addRestaurant(name, reservations, menu, rating):
    with SessionFactory() as session:
        if not session.query(Restaurant).filter(Restaurant.name == name).first():
            restaurant = Restaurant(name=name, nr_reservations=reservations, menu=menu, rating=float(rating))
            session.add(restaurant)
            session.commit()


def updateReservations(restaurantID, newReservations):
    with SessionFactory() as session:
        restaurant = session.query(Restaurant).filter(Restaurant.id == restaurantID).first()
        if restaurant:
            restaurant.nr_reservations = newReservations
            session.commit()


def updateMenu(restaurantID, newMenu):
    with SessionFactory() as session:
        restaurant = session.query(Restaurant).filter(Restaurant.id == restaurantID).first()
        if restaurant:
            restaurant.menu = newMenu
            session.commit()


def removeRestaurantByName(name):
    with SessionFactory() as session:
        restaurant = session.query(Restaurant).filter(Restaurant.name == name).order_by(Restaurant.id.desc()).first()
        if restaurant:
            session.delete(restaurant)
            session.commit()
            return True
        return False


def removeRestaurant(restaurantID):
    with SessionFactory() as session:
        restaurant = session.query(Restaurant).filter(Restaurant.id == restaurantID).first()
        if restaurant:
            session.delete(restaurant)
            session.commit()
            return True
        return False


# -----------------------------
# Flask App Setup
# -----------------------------
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
    with SessionFactory() as session:
        restaurant = session.query(Restaurant).filter(Restaurant.id == rest_id).first()
        if restaurant:
            total = restaurant.rating * restaurant.number_of_ratings + new_rating
            restaurant.number_of_ratings += 1
            restaurant.rating = total / restaurant.number_of_ratings
            session.commit()
            return redirect(url_for('restaurant_detail', restId=rest_id))
        else:
            return "Restaurant not found", 404


# -----------------------------
# XMLRPC API
# -----------------------------
handler = XMLRPCHandler('api')
handler.connect(app, '/api')


@handler.register
def get_menu_by_id(restaurant_id):
    with SessionFactory() as session:
        restaurant = session.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
        return restaurant.menu if restaurant else "Restaurant not found"


@handler.register
def get_rating_by_id(restaurant_id):
    with SessionFactory() as session:
        restaurant = session.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
        return restaurant.rating if restaurant else "Restaurant not found"


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
        result += f"{r.id} {r.name} {r.menu} {r.rating:.2f}\n"
    return result


@handler.register
def show_ratings():
    restaurants = listRestaurants()
    result = ''
    for r in restaurants:
        result += f"name: {r.name}, rating: {r.rating:.2f}\n"
    return result


@handler.register
def remove_restaurant_by_name(name):
    if removeRestaurantByName(name):
        return "Restaurant removed successfully"
    else:
        return "Restaurant not found"


# -----------------------------
# REST API
# -----------------------------
@app.route('/api/<string:restaurant_name>/menu', methods=['GET'])
def api_get_menu_by_name(restaurant_name):
    restaurant = getRestaurantByName(restaurant_name)
    if restaurant:
        return jsonify({'menu': restaurant.menu})
    else:
        return jsonify({'error': 'Restaurant not found'}), 404


@app.route('/api/restaurant/<string:restaurant_name>/<int:rating>', methods=['GET'])
def api_update_rating(restaurant_name, rating):
    with SessionFactory() as session:
        restaurant = session.query(Restaurant).filter(Restaurant.name == restaurant_name).first()
        if restaurant:
            total = restaurant.rating * restaurant.number_of_ratings + rating
            restaurant.number_of_ratings += 1
            restaurant.rating = total / restaurant.number_of_ratings
            session.commit()
            return jsonify({'message': 'Rating updated successfully', 'new_rating': restaurant.rating})
        else:
            return jsonify({'error': 'Restaurant not found'}), 404


@app.route('/api/restaurants/<string:restaurant_name>/reserve', methods=['POST'])
def api_reserve_table(restaurant_name):
    with SessionFactory() as session:
        restaurant = session.query(Restaurant).filter(Restaurant.name == restaurant_name).first()
        if not restaurant:
            return jsonify({'error': 'Restaurant not found'}), 404

        try:
            data = request.get_json()
            time_str = data.get('date')
            clean_time = time_str.replace("Z", "+00:00")
            reservation_date = datetime.datetime.fromisoformat(clean_time)

            restaurant.nr_reservations = (restaurant.nr_reservations or 0) + 1
            new_reservation = Reservation(restaurant_id=restaurant.id, date=reservation_date)
            session.add(new_reservation)
            session.commit()

            return jsonify({'message': 'Reservation added successfully', 'total_reservations': restaurant.nr_reservations})
        except Exception as e:
            session.rollback()
            print("Error reserving table:", e)
            return jsonify({'error': str(e)}), 500


def cleanup_old_reservations():
    with SessionFactory() as session:
        old_reservations = session.query(Reservation).filter(Reservation.date < datetime.datetime.utcnow()).all()
        for reservation in old_reservations:
            reservation.restaurant.nr_reservations -= 1
            session.delete(reservation)
        session.commit()


scheduler = BackgroundScheduler()
# scheduler.add_job(func=cleanup_old_reservations, trigger="interval", hours=1)

# -----------------------------
# Startup
# -----------------------------
if __name__ == "__main__":
    with SessionFactory() as session:
        if not db_exists or session.query(Restaurant).count() == 0:
            addRestaurant("segredo", 0, "picanha", 3.0)
            addRestaurant("india", 0, "tikamassala", 4.0)
            addRestaurant("sushi", 0, "sashimi", 5.0)
        else:
            print("\t database ready to use")

    app.run(port=5000, debug=True)
