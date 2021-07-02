from operator import and_, or_
import threading
import time

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask.globals import session
from flask_login import LoginManager, login_user, current_user, logout_user
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms, send
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import form
from werkzeug import CharsetAccept, debug
from models import UserGlobal, ChatRoom, BlockList, Message
from form import RegistrationForm, LoginForm, SearchForm
from datetime import datetime
import json


# Configure application
app = Flask(__name__)
app.secret_key = 'SECRET KEY'

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:HaiPhong3107@localhost:3306/distributed_project'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SQLALCHEMY_POOL_SIZE'] = 20
app.config['SQLALCHEMY_POOL_TIMEOUT'] = 300

db = SQLAlchemy(app)

# Initialize login manager
login = LoginManager(app)
login.init_app(app)


@login.user_loader
def load_user(id_user):
    return UserGlobal.query.get(int(id_user))


socketio_server = SocketIO(app, manage_session=False)

STATUSES = {}
NAMES = {}

is_connected = False

with app.app_context():
    all_users = UserGlobal.query.filter().all()
    users_loaded = True
    for user in all_users:
        STATUSES[user.globalId] = 'offline'
        NAMES[user.globalId] = user.name


def hashpassword(password):
    hash = 0
    if (len(password) == 0): 
        return hash
    for i in range(len(password)):
        chr   = ord(password[i])
        hash  = ((hash << 5) - hash) + chr
        hash |= 0; # Convert to 32bit integer
    return str(hash)

@app.route('/', methods=['GET', 'POST'])
def index():
    try:
        registration_form = RegistrationForm()
        if registration_form.validate_on_submit():
            username = registration_form.username.data
            password = registration_form.password.data
            hashed_password = hashpassword(password)

            new_user = UserGlobal(userId=1, name=username, serverId=1, hashpass=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Successfully! Please go back to login.', 'success')
            return redirect(url_for('login'))

        return render_template('register.html', form=registration_form)
    except Exception as e:
        return '<h1>' + str(e) + '</h1>'


@app.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm()

    if login_form.validate_on_submit():
        user_object = UserGlobal.query.filter_by(name=login_form.username.data).first()
        login_user(user_object)
        STATUSES[user_object.globalId] = 'online'
        session['username'] = user_object.name
        session['id'] = user_object.globalId

        socketio_server.emit('status_change', {'id': user_object.globalId, 'username': user_object.name, 'status': 'online'}, broadcast=True)
        socketio_server.emit('status_change_response', {'id': user_object.globalId, 'username': user_object.name, 'status': 'online'})
        return redirect(url_for('exchange_message'))

    return render_template('login.html', form=login_form)


@app.route('/logout', methods=['GET'])
def logout():
    temp_id = session['id']
    temp_name = session['username']
    socketio_server.emit('status_change', {'id': temp_id, 'username': temp_name, 'status': 'offline'}, broadcast=True)
    socketio_server.emit('status_change_response', {'id': temp_id, 'username': temp_name, 'status': 'offline'})
    STATUSES[temp_id] = 'offline'
    logout_user()
    flash('Logout Successfully!', 'success')
    
    return redirect(url_for('login'))


@app.route('/exchange_message', methods=['GET', 'POST'])
def exchange_message():
    ROOMS = []
    ROOM_IDS = {}
    BLOCK_STATUSES = {}
    BLOCK_USERS = []
    search_form = SearchForm()

    
    all_users = UserGlobal.query.filter().all()

    blocking_user = BlockList.query.filter(BlockList.user == session['id']).all()
    
    for user in blocking_user:
        user_object = UserGlobal.query.filter(UserGlobal.globalId == user.blockedUser).first()
        BLOCK_USERS.append(user_object)
    
    
    for user in all_users:
        # user_object = UserGlobal.query.filter(UserGlobal.globalId == user.userGlobal2).first()
        if user.globalId != session['id']:

            ROOMS.append(user)

            test = ChatRoom.query.filter(or_(
                and_(ChatRoom.userGlobal1 == session['id'], ChatRoom.userGlobal2 == user.globalId),
                and_(ChatRoom.userGlobal1 == user.globalId, ChatRoom.userGlobal2 == session['id'])
            )).first()
            
            if test is None:
                new_rom = ChatRoom(session['id'], user.globalId)
                db.session.add(new_rom)
                db.session.commit()
                ROOM_IDS[user.globalId] = new_rom.id
            else:
                ROOM_IDS[user.globalId] = test.id

            if user.globalId not in STATUSES:
                STATUSES[user.globalId] = 'offline'                
        else:
            STATUSES[user.globalId] = 'online'

        if user in BLOCK_USERS:
            BLOCK_STATUSES[user.globalId] = 'Un-Block'
        else:
            BLOCK_STATUSES[user.globalId] = 'Block'
    
    print(session['username'], STATUSES)
    return render_template('exchange_message.html', form = search_form, 
                            username=session['username'], id=session['id'], room_ids=ROOM_IDS,
                            rooms=ROOMS, block_statuses=BLOCK_STATUSES, statuses=STATUSES)


@app.route('/block_user', methods = ['POST'])
def block_user():
    friend_id = request.form.get("id")
    friend_id = int(friend_id.replace('block_user_', ''))
    action = request.form.get("action")
    print(friend_id, action)
    if action == 'Block':
        new_block = BlockList(session['id'], friend_id, datetime.now())
        db.session.add(new_block)
        db.session.commit()
        result = {"msg": "Block user successfully!"}
    else:
        block = BlockList.query.filter(and_(BlockList.user == session['id'], 
        BlockList.blockedUser == friend_id)).first()
        print(block)
        current_session = db.session.object_session(block)
        current_session.delete(block)
        current_session.commit()
        # db.session.delete(block)
        # db.session.commit()
        result = {"msg": "Unblock user successfully!"}
    return jsonify(result)


@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('404.html'), 404


@socketio_server.on('block_sending')
def block_sending(data):
    print(data)
    emit('disable_button', {'userid': data['userid'], 'blocked_id': data['blocked_id'], 'action': data['action']}, broadcast=True)


@socketio_server.on('incoming-msg')
def on_message(data):
    print('incoming-msg', data)
    msg = data['msg']
    username = data['username']
    room = data['room']
    room_id = int(room.replace('choose_room_', ''))
    timestamp = datetime.now()
    # print(msg, username, room, timestamp)

    check_roomchat = ChatRoom.query.filter(ChatRoom.id == room_id).first()
    
    if check_roomchat.userGlobal1 == session['id']:
        friend_id = check_roomchat.userGlobal2
    else:
        friend_id = check_roomchat.userGlobal1
    
    # print('friend id: ', friend_id, 'blocked id: ', current_user.globalId)
    check_block = BlockList.query.filter(and_(
        BlockList.blockedUser == session['id'],
        BlockList.user == friend_id
    )).first()
    
    if check_block is None:
        new_msg = Message(roomId=room_id, userGlobal=session['id'], content=msg, timeStamp=timestamp)
        db.session.add(new_msg)
        db.session.commit()
        send({'msg': msg, 'username': username, 'time_stamp': str(timestamp)}, room=room)
        socketio_server.emit('incoming-msg_response', {'msg': msg, 'username': username, 'time_stamp': str(timestamp), 'room': room})
        # send({'msg': msg, 'username': username, 'time_stamp': str(timestamp)}, room=room)
    else:
        send({'msg': 'Cannot send message because you were blocked by your friend.'})
        socketio_server.emit('incoming-msg_response', {'msg': 'Cannot send message because you were blocked by your friend.'})


@socketio_server.on('join')
def join(data):
    username = data['username']
    room = data['room']
    roomName = data['roomName']
    join_room(room)
    room_id = int(room.replace('choose_room_', ''))
    query_result = Message.query.filter(Message.roomId == room_id)
    all_messages = [i.serialize for i in query_result.all()]
    # print(all_messages)
    print('join room: ', room, 'username: ', username, 'room_id: ', room_id)
    
    emit('load_old_messages', {'msg': username + ' has joined the room with ' + roomName + '.',
        'sender': username,
        'receiver': roomName,
        'all_messages': all_messages}, room=room)


@socketio_server.on('leave')
def leave(data):
    username = data['username']
    room = data['room']
    roomName = data['roomName']
    leave_room(room)
    print('leave room: ', room, 'username: ', username)
    send({'msg': username + ' has left the room with ' + roomName + '.'}, room=room)

@socketio_server.on('first_connection')
def on_first_connection(data):
    global STATUSES
    print('first', data)
    # print('bcallback', STATUSES)
    for key in data['status']:
        if STATUSES[int(key)] != data['status'][key]:
            STATUSES[int(key)] = 'online'
            emit('status_change', {'id': int(key), 'username': data['name'][key], 'status': 'online'}, broadcast=True)
        else:
            STATUSES[int(key)] = data['status'][key]
    
    # print('acallback', STATUSES)
    return STATUSES, NAMES

# Handle status change notification from the other server
@socketio_server.on('status_change_friend_server')
def on_status_change_friend_server(data):
    print(data)
    STATUSES[data['id']] = data['status']
    emit('status_change', {'id': data['id'], 'username': data['username'], 'status': data['status']}, broadcast=True)


# Handle new user notification from the other server
@socketio_server.on('new_user_friend_server')
def on_new_user_friend_server(data):
    print(data)
    emit('new_user', 
        {'id': data['id'], 'username': data['username'], 'password': data['password'], 'status': data['status']},
        broadcast=True)

# Handle new user notification from the other server
@socketio_server.on('disable_button_friend_server')
def on_disable_button_friend_server(data):
    print(data)
    emit('disable_button', {'userid': data['userid'], 'blocked_id': data['blocked_id'], 'action': data['action']}, broadcast=True)

@socketio_server.on('incoming-msg_friend_server')
def on_incoming_msg_friend_server(data):
    print('incoming-msg_friend_server', data)
    if len(data) == 1:
        send({'msg': data['msg']})
    else:
        send({'msg': data['msg'], 'username': data['username'], 'time_stamp': data['time_stamp']}, room=data['room'])


if __name__ == "__main__":
    app.run(host="localhost", port=8000, debug=True)

    
    
