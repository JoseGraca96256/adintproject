from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from flask import Flask, request, render_template, redirect, url_for
from flask_xmlrpcre.xmlrpcre import XMLRPCHandler
from os import path
import datetime

DATABASE_FILE = "messagesdb.sqlite"
db_exists = path.exists(DATABASE_FILE)

engine = create_engine(f"sqlite:///{DATABASE_FILE}", echo=False)
Base = declarative_base()

class Message(Base):
    __tablename__ = 'message'
    id = Column(Integer, primary_key=True)
    sender = Column(String, nullable=False)
    receiver = Column(String, nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    def __repr__(self):
        return f"<Message(id={self.id} sender='{self.sender}' receiver='{self.receiver}' content='{self.content}')>"

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

# Data access helpers
def listMessages():
    return session.query(Message).order_by(Message.id.desc()).all()

def getMessage(messageID):
    return session.query(Message).filter(Message.id == messageID).first()

def addMessage(sender, receiver, content):
    m = Message(sender=sender, receiver=receiver, content=content)
    session.add(m)
    session.commit()
    return m.id

def getMessagesBySender(sender):
    return session.query(Message).filter(Message.sender == sender).all()

def getMessagesByReceiver(receiver):
    return session.query(Message).filter(Message.receiver == receiver).all()

def removeMessage(messageID):
    m = getMessage(messageID)
    if m:
        session.delete(m)
        session.commit()
        return True
    return False

app = Flask(__name__)

@app.route('/')
def index():
    messages = listMessages()
    # Expect a template 'messageIndex.html' similar to foodAppIndex.html
    # Template context: messages
    return render_template("messageAppIndex.html", messages=messages)

@app.route('/message/<int:msgId>')
def message_detail(msgId):
    m = getMessage(msgId)
    if not m:
        return "Message not found", 404
    # Expect template 'messageDetails.html' with message
    return render_template("messageDetails.html", message=m)

@app.route('/send', methods=['POST'])
def add_message():
    sender = request.form.get('sender')
    receiver = request.form.get('receiver')
    content = request.form.get('content')
    if not (sender and receiver and content):
        return "Missing fields", 400
    addMessage(sender, receiver, content)
    return redirect(url_for('send_message_form'))

@app.route('/inbox')
def inbox():
    messages = listMessages()
    return render_template("messageAppInbox.html", messages=messages)

@app.route('/sendMessage')
def send_message_form():
    return render_template("messageAppSend.html")


# XML-RPC setup
handler = XMLRPCHandler('api')
handler.connect(app, '/api')

@handler.register
def add_message(sender, receiver, content):
    return addMessage(sender, receiver, content)

@handler.register
def get_message(message_id):
    m = getMessage(message_id)
    if m:
        return dict(id=m.id, sender=m.sender, receiver=m.receiver, content=m.content, created_at=str(m.created_at))
    return "Message not found"

@handler.register
def list_all_messages():
    return [
        dict(id=m.id, sender=m.sender, receiver=m.receiver, content=m.content, created_at=str(m.created_at))
        for m in listMessages()
    ]

@handler.register
def remove_message(message_id):
    return "Removed" if removeMessage(message_id) else "Message not found"

@handler.register
def list_messages_by_sender(sender):
    return [m.id for m in getMessagesBySender(sender)]

@handler.register
def list_messages_by_receiver(receiver):
    return [m.id for m in getMessagesByReceiver(receiver)]

if __name__ == "__main__":
    if not db_exists:
        addMessage("system", "admin", "Welcome to the message service")
        addMessage("alice", "bob", "Hi Bob!")
        addMessage("bob", "alice", "Hello Alice!")
    app.run(port=5010, debug=True)
