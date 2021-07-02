document.addEventListener('DOMContentLoaded', () => {
    
    // Connect to websocket
    var socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);
    // Retrieve username
    const username = document.querySelector('#get-username').innerHTML;
    const id = document.querySelector('#get-iduser').innerHTML;

    // // Set default room
    let room = document.querySelectorAll('.select-room')[0].id;
    let roomName = document.querySelectorAll('.select-room')[0].innerHTML;
    console.log(roomName);
    joinRoom(room, roomName);

    let oldName = document.querySelectorAll('.select-room')[0].innerHTML;
    let block_statuses = document.querySelectorAll('.block-btn');

    // block user
    document.querySelectorAll('.block-btn').forEach(button => {
        button.onclick = () => {
            let blocked_user_id = button.id;
            let btn_value = button.value;
            // console.log(btn_value);
            $.ajax({
                method: 'post',
                url: '/block_user',
                data: {'id': blocked_user_id, 'action': btn_value},
                success: function(res) {
                    printSysMsg(res['msg']);
                    if (btn_value === 'Block') {
                        button.value = 'Un-Block';
                    }
                    else {
                        button.value = 'Block';
                    }
                    socket.emit('block_sending', {'userid': id, 'blocked_id': blocked_user_id, 'action': btn_value});
                }
            });
        }
    });

    // Send messages
    document.querySelector('#send_message').onclick = () => {
        socket.emit('incoming-msg', {'msg': document.querySelector('#user_message').value,
            'username': username, 'room': room});
        // console.log({'msg': document.querySelector('#user_message').value,
        // 'username': username, 'room': room});
        document.querySelector('#user_message').value = '';
    };

    socket.on('status_change', data => {
        // console.log(data);
        let new_id = data['id'];
        let new_name = data['username'];
        let new_status = data['status'];

        if (new_name !== username) {
            document.querySelector('#status_' + new_id).innerHTML = new_status;
        }
        // document.querySelector('#status_' + data['id']).innerHTML = data['status'];
    });

    // socket.on('new_user', data => {
    //     console.log(data);
    //     const p_room = document.createElement("p");
    //     const p_status = document.createElement("p");
    //     const input_block = document.createElement("input");

    //     p_room.id = "choose_room_" + ;
    //     p_room.setAttribute("class", "select-room cursor-pointer inline-object");
    //     p_room.innerText = data['username'];

    //     p_status.id = "status_" + ;
    //     p_status.setAttribute("class", "select-room cursor-pointer inline-object");
    //     p_status.innerText = data['username'];

    //     input_block.id = "block_user_" + ;
    //     input_block.setAttribute("class", "block-btn inline-object");
    //     input_block.type = "button";
    //     input_block.value = 'Block';

    // });

    // Display history of a conversation
    socket.on('load_old_messages', data => {
        console.log(data);
        
        printSysMsg(data.msg);

        for (let i = 0; i < data.all_messages.length; i++) {

            const p = document.createElement('p');
            const span_username = document.createElement('span');
            const span_timestamp = document.createElement('span');
            const br = document.createElement('br');

            if (data.all_messages[i]['userGlobal'] == id) {
                p.setAttribute("class", "my-msg");

                // Username
                span_username.setAttribute("class", "my-username");
                span_username.innerText = username;

            }
            else {
                p.setAttribute("class", "others-msg");

                // Username
                span_username.setAttribute("class", "other-username");
                if (data.sender != username) {
                    span_username.innerText = data.sender;
                }
                else {
                    span_username.innerText = data.receiver;
                }
                // span_username.innerText = "friend";

            }
            span_timestamp.setAttribute("class", "timestamp");
            span_timestamp.innerText = data.all_messages[i]['timeStamp'];

            // HTML to append
            p.innerHTML += span_username.outerHTML + br.outerHTML + data.all_messages[i]['content'] + br.outerHTML + span_timestamp.outerHTML;

            //Append
            document.querySelector('#display-message-section').append(p);
        }

        scrollDownChatWindow();
    });

    // Display all incoming messages
    socket.on('message', data => {
        
        if (data.msg) {
            const p = document.createElement('p');
            const span_username = document.createElement('span');
            const span_timestamp = document.createElement('span');
            const br = document.createElement('br');
            
            if (data.username == username) {
                p.setAttribute("class", "my-msg");

                // Username
                span_username.setAttribute("class", "my-username");
                span_username.innerText = data.username;

                // Timestamp
                span_timestamp.setAttribute("class", "timestamp");
                span_timestamp.innerText = data.time_stamp;

                // HTML to append
                p.innerHTML += span_username.outerHTML + br.outerHTML + data.msg + br.outerHTML + span_timestamp.outerHTML

                //Append
                document.querySelector('#display-message-section').append(p);
            }
            // Display other users' messages
            else if (typeof data.username !== 'undefined') {
                // console.log('msg of other user');
                p.setAttribute("class", "others-msg");

                // Username
                span_username.setAttribute("class", "other-username");
                span_username.innerText = data.username;

                // Timestamp
                span_timestamp.setAttribute("class", "timestamp");
                span_timestamp.innerText = data.time_stamp;

                // HTML to append
                p.innerHTML += span_username.outerHTML + br.outerHTML + data.msg + br.outerHTML + span_timestamp.outerHTML;

                //Append
                document.querySelector('#display-message-section').append(p);
            }
            // Display system message
            else {
                printSysMsg(data.msg);
                // console.log('aaaa');
            }

        }
        scrollDownChatWindow();
    });

    // Select a room
    document.querySelectorAll('.select-room').forEach((p, index, value) => {
        p.onclick = () => {
            let newRoom = p.id;
            let roomName = p.innerHTML;
            // Check if user already in the room
            if (newRoom === room) {
                msg = `You are already in the room with ${roomName}.`;
                printSysMsg(msg);
            } else {
                leaveRoom(room, oldName);
                joinRoom(newRoom, roomName);
                room = newRoom;
            }
        };
    });

    window.addEventListener('beforeunload', function(e) {
        socket.emit('offline', {'id':id, 'username': username});
    });

    // Logout from chat
    // document.querySelector("#logout-btn").onclick = () => {
    //     // socket.emit('offline', {'id':id, 'username': username});
    //     leaveRoom(room);
    // };

    // Trigger 'leave' event if user was previously on a room
    function leaveRoom(room, roomName) {
        socket.emit('leave', {'username': username, 'room': room, 'roomName': roomName});

        document.querySelectorAll('.select-room').forEach(p => {
            p.style.color = "black";
        });
    }

    // Trigger 'join' event
    function joinRoom(room, roomName) {

        // Join room
        socket.emit('join', {'username': username, 'room': room, 'roomName': roomName});

        // Highlight selected room
        document.querySelector('#' + CSS.escape(room)).style.color = "#ffc107";
        document.querySelector('#' + CSS.escape(room)).style.backgroundColor = "white";

        // Clear message area
        document.querySelector('#display-message-section').innerHTML = '';

        // Autofocus on text box
        document.querySelector("#user_message").focus();
    }

    // Scroll chat window down
    function scrollDownChatWindow() {
        const chatWindow = document.querySelector("#display-message-section");
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    // Print system messages
    function printSysMsg(msg) {
        const p = document.createElement('p');
        p.setAttribute("class", "system-msg");
        p.innerHTML = msg;
        document.querySelector('#display-message-section').append(p);
        scrollDownChatWindow()

        // Autofocus on text box
        document.querySelector("#user_message").focus();
    }
});
