from sqlalchemy import create_engine, Column, Integer, String, Date
from sqlalchemy.orm import sessionmaker, declarative_base

from flask import Flask, request
from flask import render_template
from flask_xmlrpcre.xmlrpcre import *

import datetime
from os import path

#SLQ access layer initialization
DATABASE_FILE = "check.sqlite"
db_exists = False
if path.exists(DATABASE_FILE):
    db_exists = True
    # print("\t database already exists")

engine = create_engine('sqlite:///%s'%(DATABASE_FILE), echo=False) #echo = True shows all SQL calls

Base = declarative_base()

class CheckIn(Base):        # change to usage
    __tablename__ = 'checkin'
    id = Column(Integer, primary_key=True)
    username = Column(String)
    location = Column(String)
    spec = Column(String)
    date = Column(Date)
    def __repr__(self):
        if self.spec == "Checked In":
            return "<CheckIn(id=%d username='%s', location='%s', date='%s')>" % (
                                    self.id, self.username, self.location, self.date)
        else:
            return "<CheckOut(id=%d username='%s', location='%s', date='%s')>" % (
                                    self.id, self.username, self.location, self.date)

def addCheckIn():
    username = request.form.get("username")
    location = request.form.get("Location")
    spec = "Checked In"; 
    checkin = CheckIn(username=username, location=location, spec=spec, date=datetime.date.today())
    session.add(checkin)
    session.commit()

def addCheckOut():
    username = request.form.get("username")
    location = request.form.get("Location")
    spec = "Checked Out"; 
    checkout = CheckIn(username=username, location=location, spec=spec, date=datetime.date.today()) # separate CheckOut class/table?
    session.add(checkout)
    session.commit()

def listChecks():
    username = request.form.get("username")
    return session.query(CheckIn).filter(CheckIn.username == username).all()

Base.metadata.create_all(engine) #Create tables for the data models

Session = sessionmaker(bind=engine)
session = Session()

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("checkIndex.html")

@app.route("/checkin", methods=["GET", "POST"])
def checkIn():
    if request.method == "GET":
        return render_template("checkInAdd.html")
    else:
        # Add check in to database
        addCheckIn()
        return "Check-in successful!"
    
@app.route("/checkout", methods=["GET", "POST"])
def checkOut():
    if request.method == "GET":
        return render_template("checkOutAdd.html")
    else:
        # Add check out to database
        addCheckOut()
        return "Check-out successful!"


@app.route("/listcheck", methods=["GET", "POST"])
def listcheck():
    if request.method == "GET":
        return render_template("checkList.html")    
    else:
        return render_template("checkList.html", checks=listChecks())
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)