from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from flask import Flask, request, render_template, redirect, url_for
from flask_xmlrpcre.xmlrpcre import XMLRPCHandler
from os import path
import datetime
from flask import jsonify
from sqlalchemy import ForeignKey
DATABASE_FILE = "db/messagesdb.sqlite"

MAIN_APP_SECRET = "eletrodomesticos_e_computadores_2024"

db_exists = path.exists(DATABASE_FILE)

engine = create_engine(f"sqlite:///{DATABASE_FILE}", echo=False)
Base = declarative_base()

class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    def __repr__(self):
        return f"<User(id={self.id} username='{self.username}')>"

class Message(Base):
    __tablename__ = 'message'
    id = Column(Integer, primary_key=True)
    sender_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    receiver_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Add relationships
    sender_user = relationship("User", foreign_keys=[sender_id], backref="sent_messages")
    receiver_user = relationship("User", foreign_keys=[receiver_id], backref="received_messages")
    
    def __repr__(self):
        return f"<Message(id={self.id} sender_id={self.sender_id} receiver_id={self.receiver_id} content='{self.content}')>"


class Friendship(Base):
    __tablename__ = 'friendship'
    id = Column(Integer, primary_key=True)
    user1_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    user2_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    
    # Optional: Add relationships if you want to access User objects directly
    user1 = relationship("User", foreign_keys=[user1_id])
    user2 = relationship("User", foreign_keys=[user2_id])
    
    def __repr__(self):
        return f"<Friendship(id={self.id} user1_id={self.user1_id} user2_id={self.user2_id})>"


Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

def getUserByUsername(username):
    return session.query(User).filter(User.username == username).first()

# Data access helpers
def listMessages():
    username = request.form.get("username")
    return session.query(Message).filter(Message.sender == username).order_by(Message.id.desc()).all()

def getMessage(messageID):
    return session.query(Message).filter(Message.id == messageID).first()

def addMessage(sender, receiver, content):
    senderID = getUserByUsername(sender).id
    receiverID = getUserByUsername(receiver).id
    if not senderID:
        return None
    if not receiverID:
        return None
    
    m = Message(sender_id=senderID, receiver_id=receiverID, content=content)
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

@app.route('/inbox', methods=["GET", "POST"])
def inbox():
    if request.method == "POST":
        messages = listMessages()
        return render_template("messageAppInbox.html", messages=messages)
    else:
        all_messages = session.query(Message).all()
        return render_template("messageAppInbox.html", messages=all_messages)

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

#proj2 functions

def get_friends_by_id(user_id):
    friendships = session.query(Friendship).filter(
        (Friendship.user1_id == user_id) | (Friendship.user2_id == user_id)
    ).all()
    friends = []
    for friendship in friendships:
        if friendship.user1 == user_id:
            friends.append(friendship.user2)
        else:
            friends.append(friendship.user1)
    return friends

def get_friends_by_username(username):
    user = session.query(User).filter(User.username == username).first()
    if not user:
        return []
    return get_friends_by_id(user.id)
    
def getMessagesBySender(nick):
    sender_id = getUserByUsername(nick).id
    return session.query(Message).filter(Message.sender_id == sender_id).all()

def getMessagesByReceiver(nick):
    receiver_id = getUserByUsername(nick).id
    return session.query(Message).filter(Message.receiver_id == receiver_id).all()

#REST API endpoints 

@app.route('/api/User/<string:username>', methods=['GET'])
def api_is_user(username):
    user = getUserByUsername(username)
    if user:
        return  200
    else:
        return  404  



@app.route('/api/add_user', methods=['POST'])
def api_add_user():
    data = request.get_json()
    username = data.get("username")
    pwd = data.get("pwd")
    
    if pwd != MAIN_APP_SECRET:
        return "Unauthorized", 401
    
    if not username:
        return "Username is required", 400
    
    if getUserByUsername(username):
        return "User already exists", 400
    
    new_user = User(username=username)
    session.add(new_user)
    session.commit()
    
    return "User added successfully", 200

@app.route('/api/add_friend', methods=['POST'])
def api_add_friend():
    data = request.get_json()
    username = data.get("username")
    friend_username = data.get("friend_username")
    pwd = data.get("pwd")
    
    if pwd != MAIN_APP_SECRET:
        return "Unauthorized", 401
    
    user = getUserByUsername(username)
    friend = getUserByUsername(friend_username)
    
    if not user or not friend:
        return "User or friend not found", 404
    
    # Check if friendship already exists
    existing_friendship = session.query(Friendship).filter(
        ((Friendship.user1_id == user.id) & (Friendship.user2_id == friend.id)) |
        ((Friendship.user1_id == friend.id) & (Friendship.user2_id == user.id))
    ).first()
    
    if existing_friendship:
        return "Friendship already exists", 400
    
    new_friendship = Friendship(user1_id=user.id, user2_id=friend.id)
    session.add(new_friendship)
    session.commit()
    
    return "Friend added successfully", 200

@app.route('/api/user/<string:username>', methods=['DELETE'])
def api_delete_user(username):
    user = getUserByUsername(username)
    if not user:
        return "User not found", 404
    session.delete(user)
    session.commit()
    return "User deleted successfully", 200

@app.route('/api/users/<string:username>/friends', methods=['GET'])
def api_get_friends(username):
    user = getUserByUsername(username)
    if not user:
        return "User not found", 404
    friendsID = get_friends_by_username(username)
    friendsUsername=[]
    for friendIS in friendsID:
        friend = session.query(User).filter(User.id == friendIS).first()
        friendsUsername.append(friend.username)
    return jsonify(friendsUsername)
    
    

@app.route('/api/<string:username>/inbox', methods=['GET'])
def api_inbox(username):
    messages = getMessagesByReceiver(username)
    result = [
        dict(id=m.id, sender=m.sender, receiver=m.receiver, content=m.content, created_at=str(m.created_at))
        for m in messages
    ]
    return jsonify(result)

@app.route('/api/<string:username>/sent ', methods=['GET'])
def api_sent(username):
    messages = getMessagesBySender(username)
    result = [
        dict(id=m.id, sender=m.sender, receiver=m.receiver, content=m.content, created_at=str(m.created_at))
        for m in messages
    ]
    return jsonify(result)

def deleteUser(id):
    user = User.query.get(id)
    if user:
        session.delete(user)
        session.commit()
    return


def removeBots():
    users = session.query(User).filter(User.username.startswith("bot")).all()
    for user in users:

        session.delete(user)
    session.commit()
    return

if __name__ == "__main__":

    if not session.query(User).count() or not db_exists:
        u1 = User(username="admin")
        u2 = User(username="alice")
        u3 = User(username="bob")
        u4 = User(username="system")
        session.add_all([u1, u2, u3, u4])
        session.commit()
        
    if not db_exists:
        addMessage("system", "admin", "Welcome to the message service")
        addMessage("alice", "bob", "Hi Bob!")
        addMessage("bob", "alice", "Hello Alice!")
        
    if session.query(Friendship).count() == 0:
        f1 = Friendship(user1_id=1, user2_id=2)
        f2 = Friendship(user1_id=2, user2_id=3)

        session.add_all([f1, f2])
        session.commit()

    print(get_friends_by_id(2))  # Example usage

    print(f"messages from alice: {getMessagesBySender('alice')}")
    print(f"messages to alice: {getMessagesByReceiver('alice')}")
    print(f"alice's friends: {get_friends_by_username('alice')}")
    app.run(port=5010, debug=True)
