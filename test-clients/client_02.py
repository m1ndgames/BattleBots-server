import socket
import json
import random

botname = 'testbot_2'
secret = 'W8oqPq6SSU++23e6JSLFCFb1Os0OdbmLuFnLFqH4O7E='  # this is the account 'password'
color = (random.randrange(0, 255), random.randrange(0, 255), random.randrange(0, 255))


def encode_data(in_data):
    json_data_string = json.dumps(in_data)
    encoded_data = str.encode(json_data_string)
    return encoded_data


def decode_data(out_data):
    decoded_data = out_data.decode('utf-8')
    data_objects = json.loads(decoded_data)
    return dict(data_objects)


client = socket.socket()
host = '127.0.0.1'
port = 1337

print('Waiting for connection response')
try:
    client.connect((host, port))
except socket.error as e:
    print(str(e))

while True:
    res = client.recv(2048)
    server_message = decode_data(res)
    if server_message:
        print(str(server_message))

        if server_message['type'] == 'init':
            data = {
                'type': 'init',
                'name': botname,
                'secret': secret,
                'color': color
            }
            client.send(encode_data(data))

        elif server_message['type'] == 'ack':
            game_map = server_message['map']
            min_players = server_message['min_players']
            max_players = server_message['max_players']
            max_rounds = server_message['max_rounds']

            data = {
                'type': 'ack',
                'name': botname,
                'secret': secret
            }
            client.send(encode_data(data))

        elif server_message['type'] == 'full':
            client.close()
            break

        elif server_message['type'] == 'start':
            data = {
                'type': 'ready',
                'name': botname,
                'secret': secret,
            }
            client.send(encode_data(data))

        elif server_message['type'] == 'game':
            pos_x = server_message['pos_x']
            pos_y = server_message['pos_y']
            speed = server_message['speed']
            power = server_message['power']
            pos_angle = server_message['pos_angle']
            radar_angle = server_message['radar_angle']
            data = {
                'type': 'game',
                'action': 'turn-left',
                'name': botname,
                'secret': secret
            }
            client.send(encode_data(data))
