from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import json

db = SQLAlchemy()


class UserGlobal(UserMixin, db.Model):

    __tablename__ = 'userglobal'
    globalId = db.Column(db.Integer, primary_key=True, nullable=False)
    userId = db.Column(db.Integer, nullable=True)
    name = db.Column(db.String(20), nullable=True)
    serverId = db.Column(db.Integer, nullable=True)
    hashpass = db.Column(db.String(32), nullable=True)

    def __init__(self, userId, name, serverId, hashpass):
        self.userId = userId
        self.name = name
        self.serverId = serverId
        self.hashpass = hashpass
    
    def get_id(self):
        return self.globalId

class ChatRoom(db.Model):

    __tablename__ = 'chatroom'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    userGlobal1 = db.Column(db.Integer, nullable=True)
    userGlobal2 = db.Column(db.Integer, nullable=True)

    def __init__(self, user1_id, user2_id):
        self.userGlobal1 = user1_id
        self.userGlobal2 = user2_id

class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    content = db.Column(db.String(1024), nullable=True)
    timeStamp = db.Column(db.DateTime, nullable=True)
    roomId = db.Column(db.Integer, nullable=True)
    userGlobal = db.Column(db.Integer, nullable=True)

    def __init__(self, content, timeStamp, roomId, userGlobal):
        self.content = content
        self.timeStamp = timeStamp
        self.roomId = roomId
        self.userGlobal = userGlobal

    @property
    def serialize(self):
        return {
            'id': self.id,
            'roomId': self.roomId,
            'userGlobal': self.userGlobal,
            'content': self.content,
            'timeStamp': str(self.timeStamp)
        }

class BlockList(db.Model):
    __tablename__ = 'blocklist'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    user = db.Column(db.Integer, nullable=True)
    blockedUser = db.Column(db.Integer, nullable=True)
    timeStart = db.Column(db.DateTime, nullable=True)

    def __init__(self, user, blockedUser, timeStart):
        self.user = user
        self.blockedUser = blockedUser
        self.timeStart = timeStart

