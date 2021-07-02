from logging import Logger
from operator import and_, or_
from os import path
import threading
import time

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
# from flask.globals import session
from flask_login import LoginManager, login_user, current_user, logout_user
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms, send
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import form
from werkzeug import CharsetAccept, debug
from models import UserGlobal, ChatRoom, BlockList, Message
from form import RegistrationForm, LoginForm, SearchForm
from datetime import datetime
import json
# import socketIO_client
import socketio


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

users_loaded = False
is_connected = False
STATUSES = {}
NAMES = {}

socketio_server = SocketIO(app, manage_session=True)

socketio_client = socketio.Client()

friend_url = 'http://localhost:8000'

with app.app_context():
    all_users = UserGlobal.query.filter().all()
    users_loaded = True
    # print('here')
    for user in all_users:
        STATUSES[user.globalId] = 'offline'
        NAMES[user.globalId] = user.name

@socketio_client.on('require_handshake')
def on_require_handshake(data):
    print(data)
    global is_connected
    global STATUSES
    is_connected = establish_connection(friend_url)
    for key in data['data']:
        STATUSES[int(key)] = data['data'][key]

def callback_connect(*args):
    global STATUSES
    for key in args[0]:
        if STATUSES[int(key)] != args[0][key]:
            STATUSES[int(key)] = 'online'
            socketio_server.emit('status_change', {'id': int(key), 'username': args[1][key], 'status': 'online'},broadcast=True)
        else:
            STATUSES[int(key)] = args[0][key]
    

@socketio_client.event
def connect():
    global is_connected
    print("Connected")
    is_connected = True
    # socketio_client.emit('first_connection', {'msg': 'handshake', 'data': 'start'})
    socketio_client.emit('first_connection', {'msg': 'global', 'status': STATUSES, 'name': NAMES}, callback=callback_connect)


@socketio_client.event
def connect_error(data):
    global is_connected
    is_connected = False
    print("The connection failed!")

@socketio_client.event
def disconnect():
    global is_connected
    is_connected = False
    print("I'm disconnected!")

# Handle new user notification from the friend server
@socketio_client.on('new_user_response')
def on_new_user_response(data):
    socketio_server.emit('new_user', 
                        {'id': data['id'], 'username': data['username'],
                        'password': data['password'], 'status': data['status']},
                        broadcast=True)

# Handle status change notification from the friend server
@socketio_client.on('status_change_response')
def on_user_online_response(data):
    STATUSES[data['id']] = data['status']
    socketio_server.emit('status_change', {'id': data['id'], 'username': data['username'], 'status': data['status']},broadcast=True)

@socketio_client.on('block_user_response')
def on_block_user_response(data):
    pass


@socketio_client.on('incoming-msg_response')
def on_incoming_msg_response(data):
    print('incoming-msg_response', data)
    if len(data) == 1:
        socketio_server.send({'msg': data['msg']})
    else:
        socketio_server.send({'msg': data['msg'], 'username': data['username'], 'time_stamp': data['time_stamp']}, room=data['room'])

# @socketio_client.event
# def message(data):
#     print('message', data)
#     socketio_server.send({'msg': data['msg'], 'username': data['username'], 'time_stamp': data['time_stamp']}, room=data['room'])


# Connect to the friend server
def establish_connection(url):
    try:
        socketio_client.connect(url)
    except Exception as e:
        print("\nEstablish connection fail. The friend server is still off.\n")
    
    return socketio_client.connected

is_connected = establish_connection(friend_url)
if is_connected:
    print('\nEstablish connection successfully!\n')
else:
    print('\nWating for friend user to turn on.\n')

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

            # for user in all_users:
            #     new_rom = ChatRoom(user.globalId, new_user.globalId)
            #     db.session.add(new_rom)
            #     db.session.commit()
            
            all_users.append(new_user)
            STATUSES[new_user.globalId] = 'offline'

            socketio_server.emit('new_user',
                                {'id': new_user.globalId, 'username': new_user.name,
                                'password': new_user.hashpass, 'status': 'offline'},
                                broadcast=True)
            
            if is_connected:
                socketio_client.emit('new_user_friend_server', 
                                    {'id': new_user.globalId, 'username': new_user.name, 
                                    'password': new_user.hashpass, 'status': 'offline'})
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

        socketio_server.emit('status_change', 
                            {'id': user_object.globalId, 'username': user_object.name, 'status': 'online'},
                            broadcast=True)
        if is_connected:
            socketio_client.emit('status_change_friend_server', 
                                {'id': user_object.globalId, 'username': user_object.name, 'status': 'online'})
        else:
            if establish_connection(friend_url):
                socketio_client.emit('status_change_friend_server', 
                                {'id': user_object.globalId, 'username': user_object.name, 'status': 'online'})
            else:
                print('Still no connection. Waiting...')
        return redirect(url_for('exchange_message'))

    return render_template('login.html', form=login_form)


@app.route('/logout', methods=['GET'])
def logout():
    temp_id = session['id']
    temp_name = session['username']

    socketio_server.emit('status_change', {'id': temp_id, 'username': temp_name, 'status': 'offline'}, broadcast=True)
    
    if is_connected:
        socketio_client.emit('status_change_friend_server', 
                            {'id': temp_id, 'username': temp_name, 'status': 'offline'})
    else:
        if establish_connection(friend_url):
            socketio_client.emit('status_change_friend_server', 
                                {'id': temp_id, 'username': temp_name, 'status': 'offline'})
        else:
            print('Still no connection. Waiting...')

    STATUSES[temp_id] = 'offline'
    logout_user()
    flash('Logout Successfully!', 'success')
    
    return redirect(url_for('login'))


@app.route('/exchange_message', methods=['GET', 'POST'])
def exchange_message():

    # session['ROOMS'] = []
    # session['ROOM_IDS'] = {}
    # session['BLOCK_STATUSES'] = {}
    # session['BLOCK_USERS'] = []

    # ROOMS = session['ROOMS']
    # ROOM_IDS = session['ROOM_IDS']
    # BLOCK_STATUSES = session['BLOCK_STATUSES']
    # BLOCK_USERS = session['BLOCK_USERS']

    ROOMS = []
    ROOM_IDS = {}
    BLOCK_STATUSES = {}
    BLOCK_USERS = []

    search_form = SearchForm()
    
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

    # print(session['username'], STATUSES)
    # session['ROOMS'] = ROOMS
    # session['ROOM_IDS'] = ROOM_IDS
    # session['BLOCK_STATUSES'] = BLOCK_STATUSES
    # session['BLOCK_USERS'] = BLOCK_USERS

    
    # return render_template('exchange_message.html', form = search_form, 
    #                         username=session['username'], id=session['id'], room_ids=session['ROOM_IDS'],
    #                         rooms=session['ROOMS'], block_statuses=session['BLOCK_STATUSES'], statuses=STATUSES)
    
    return render_template('exchange_message.html', form = search_form, 
                            username=session['username'], id=session['id'], room_ids=ROOM_IDS,
                            rooms=ROOMS, block_statuses=BLOCK_STATUSES, statuses=STATUSES)


@app.route('/block_user', methods = ['POST'])
def block_user():
    friend_id = request.form.get("id")
    friend_id = int(friend_id.replace('block_user_', ''))
    action = request.form.get("action")
    print('block_user: ', friend_id, action)
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
    # print(data)
    emit('disable_button', {'userid': data['userid'], 'blocked_id': data['blocked_id'], 'action': data['action']}, broadcast=True)
    
    if is_connected:
        socketio_client.emit('disable_button_friend_server',
                            {'userid': data['userid'], 'blocked_id': data['blocked_id'], 'action': data['action']})
    else:
        pass


@socketio_server.on('incoming-msg')
def on_message(data):
    msg = data['msg']
    username = data['username']
    room = data['room']
    room_id = int(room.replace('choose_room_', ''))
    timestamp = datetime.now()
    print('incoming-msg: ', msg, username, room, timestamp)

    check_roomchat = ChatRoom.query.filter(ChatRoom.id == room_id).first()
    
    if check_roomchat.userGlobal1 == session['id']:
        friend_id = check_roomchat.userGlobal2
    else:
        friend_id = check_roomchat.userGlobal1
    
    check_block = BlockList.query.filter(and_(
        BlockList.blockedUser == session['id'],
        BlockList.user == friend_id
    )).first()
    
    if check_block is None:
        new_msg = Message(roomId=room_id, userGlobal=session['id'], content=msg, timeStamp=timestamp)
        db.session.add(new_msg)
        db.session.commit()
        send({'msg': msg, 'username': username, 'time_stamp': str(timestamp)}, room=room)
        if is_connected:
            socketio_client.emit('incoming-msg_friend_server', 
                                {'msg': msg, 'username': username, 'time_stamp': str(timestamp), 'room': room})
        # socketio_client.emit('incoming-msg', {'msg': msg, 'username': username, 'time_stamp': str(timestamp)}, room=room)
        # send({'msg': msg, 'username': username, 'time_stamp': str(timestamp)}, room=room)
    else:
        send({'msg': 'Cannot send message because you were blocked by your friend.'})
        if is_connected:
            socketio_client.emit('incoming-msg_friend_server',
                                {'msg': 'Cannot send message because you were blocked by your friend.'})
        # socketio_client.emit('incoming-msg', {'msg': 'Cannot send message because you were blocked by your friend.'})


@socketio_server.on('join')
def join(data):
    print(data)
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


if __name__ == "__main__":
    app.run(host="localhost", port=5000, debug=True)

    
    
