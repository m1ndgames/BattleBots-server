import random
import socket
import json
import threading
from _thread import *
import time
import cv2
import numpy as np


class BattleBotsServer:
    def __init__(self, battlebots=None):
        self.battlebots = battlebots
        self.battlebots.objects = []
        self.battlebots.received_update = False
        self.battlebots.clients = []
        self.countdown_timer = None
        self.timer_thread = None
        self.timer_started = False
        self.battlebots.game_tick = 0
        self.round_actions = []

        self.game_start = False

    def timer(self):
        if not self.timer_started and not self.game_start:
            self.timer_started = True
            countdown = int(self.battlebots.config['game']['countdown'])
            while countdown > -1:
                time.sleep(1)
                countdown -= 1
                self.countdown_timer = countdown

    def encode_data(self, data):
        json_data_string = json.dumps(data)
        encoded_data = str.encode(json_data_string)
        return encoded_data

    def decode_data(self, data):
        decoded_data = data.decode('utf-8')
        data_objects = json.loads(decoded_data)
        return data_objects

    def get_impossible_positions(self):
        mapfile = 'images/maps/' + self.battlebots.map + '.png'
        image = cv2.imread(mapfile)
        coords = np.argwhere((image==[255,255,255]).all(axis=2))
        return coords

    def get_distance(self, x1, y1, x2, y2):
        result = ((((x2 - x1) ** 2) + ((y2 - y1) ** 2)) ** 0.5)
        return result

    def find_spawn_position(self):
        while True:
            random_position = [random.randrange(50, 950), random.randrange(50, 950)]
            random_pos_x_list = list(range(random_position[0] - 14, random_position[0] + 14))
            random_pos_y_list = list(range(random_position[1] - 14, random_position[1] + 14))

            random_positions = []

            for x in random_pos_x_list:
                for y in random_pos_y_list:
                    random_positions.append([x, y])

            for random_pos in random_positions:
                if random_pos not in self.battlebots.impossible_positions:
                    continue
                else:
                    break

            if self.battlebots.clients:
                for client in self.battlebots.clients:
                    distance_to_random = self.get_distance(random_position[0], random_position[1], client['pos_x'], client['pos_y'])
                    if distance_to_random > 250:
                        continue
                    else:
                        break

            if random_position:
                return random_position

    def get_tank_positions(self, player_data):
        pos_x = player_data['pos_x']
        pos_y = player_data['pos_y']

        pos_x_list = list(range(pos_x - 14, pos_x + 14))
        pos_y_list = list(range(pos_y - 14, pos_y + 14))

        tank_positions = []

        for x in pos_x_list:
            for y in pos_y_list:
                tank_positions.append([x, y])

        return tank_positions

    def turn(self, player, type, direction):
        if type == 'tank':
            angle = player['pos_angle']
        else:
            angle = player['radar_angle']

        if direction == 'left':
            if angle == 0:
                return 359
            else:
                new_angle = angle - 1
                return new_angle
        elif direction == 'right':
            if angle == 359:
                return 0
            else:
                new_angle = angle + 1
                return new_angle

    def check_valid_input(self, message):
        for client in self.battlebots.clients:
            if message['secret'] == client['secret']:
                if message['secret'] not in self.round_actions:
                    self.round_actions.append(message['secret'])

                if message['type'] == 'game' and message['action'] == 'accelerate':
                    client['speed'] += 1
                    return True
                elif message['type'] == 'game' and message['action'] == 'brake':
                    client['speed'] -= 1
                    return True
                elif message['type'] == 'game' and message['action'] == 'turn-left':
                    new_angle = self.turn(client, 'tank', 'left')
                    client['pos_angle'] = new_angle
                    return True
                elif message['type'] == 'game' and message['action'] == 'turn-right':
                    new_angle = self.turn(client, 'tank', 'right')
                    client['pos_angle'] = new_angle
                    return True
                elif message['type'] == 'game' and message['action'] == 'radar-left':
                    new_angle = self.turn(client, 'radar', 'left')
                    client['radar_angle'] = new_angle
                    return True
                elif message['type'] == 'game' and message['action'] == 'radar-right':
                    new_angle = self.turn(client, 'radar', 'right')
                    client['radar_angle'] = new_angle
                    return True
                else:
                    return False

    def multi_threaded_client(self, connection):
        # This data package is sent when a client connects
        data = {
            'type': 'init'
        }

        connection.send(self.encode_data(data))

        while True:
            # Send 'full' event type when max players have been connected
            if len(self.battlebots.clients) >= (int(self.battlebots.config['game']['max_players']) + 1):
                data = {
                    'type': 'full'
                }
                connection.send(self.encode_data(data))
                connection.close()
                return

            data = connection.recv(2048)
            if not data:
                break
            else:
                client_message = self.decode_data(data)
                if client_message:
                    # Send init event type to a new connection
                    if client_message['type'] == 'init':
                        name = client_message['name']
                        secret = client_message['secret']
                        color = client_message['color']
                        random_startangle = random.randrange(0, 359)

                        self.battlebots.clients.append(
                            {
                                'name': name,
                                'secret': secret,
                                'client': connection,
                                'color': color,
                                'pos_x': self.find_spawn_position()[0],
                                'pos_y': self.find_spawn_position()[1],
                                'pos_angle': random_startangle,
                                'radar_angle': random_startangle,
                                'speed': 0,
                                'power': 100,
                                'health': 100,
                                'ready': False
                            }
                        )

                        data = {
                            'type': 'ack',
                            'map': self.battlebots.config['game']['map'],
                            'min_players': self.battlebots.config['game']['min_players'],
                            'max_players': self.battlebots.config['game']['max_players'],
                            'max_rounds': self.battlebots.config['game']['max_rounds']
                        }
                        connection.send(self.encode_data(data))

                    elif client_message['type'] == 'ready':
                        for client in self.battlebots.clients:
                            if client['client'] == connection:
                                client['ready'] = True
                                data = {
                                    'type': 'game',
                                    'pos_x': client['pos_x'],
                                    'pos_y': client['pos_y'],
                                    'pos_angle': client['pos_angle'],
                                    'radar_angle': client['radar_angle'],
                                    'speed': client['speed'],
                                    'power': client['power'],
                                    'health': client['health'],
                                    'round': self.battlebots.game_tick
                                }
                                client['client'].send(self.encode_data(data))

                    elif client_message['type'] == 'game':
                        for client in self.battlebots.clients:
                            if client['client'] == connection:
                                if self.check_valid_input(client_message):
                                    data = {
                                        'type': 'game',
                                        'pos_x': client['pos_x'],
                                        'pos_y': client['pos_y'],
                                        'pos_angle': client['pos_angle'],
                                        'radar_angle': client['radar_angle'],
                                        'speed': client['speed'],
                                        'power': client['power'],
                                        'health': client['health'],
                                        'round': self.battlebots.game_tick
                                    }
                                    client['client'].send(self.encode_data(data))

    def server_processor(self):
        while not self.battlebots.stopthreads:
            # Check if all players provided an input this round
            if len(self.battlebots.clients) == len(self.round_actions):
                self.battlebots.received_update = True
                if self.game_start:
                    self.battlebots.game_tick += 1
                self.round_actions = []

            if self.battlebots.clients:
                # Send 'start' event type to all clients when we are ready to start
                if self.countdown_timer:
                    if self.countdown_timer <= 0 and not self.game_start:
                        self.game_start = True
                        data = {
                            'type': 'start',
                            'round': self.battlebots.game_tick
                        }
                        for client in self.battlebots.clients:
                            client['client'].send(self.encode_data(data))
                        self.countdown_timer = None
                        self.timer_thread = None
                        self.timer_started = False

                if len(self.battlebots.clients) == int(
                        self.battlebots.config['game']['max_players']) and not self.game_start:
                    if self.countdown_timer:
                        self.countdown_timer = None
                        self.timer_thread = None
                        self.timer_started = False

                    self.game_start = True
                    data = {
                        'type': 'start',
                        'round': self.battlebots.game_tick
                    }
                    for client in self.battlebots.clients:
                        client['client'].send(self.encode_data(data))

                # Start countdown if we are above min players and waiting for more
                if int(self.battlebots.config['game']['min_players']) <= len(self.battlebots.clients) <= int(
                        self.battlebots.config['game']['max_players']):
                    self.timer_thread = threading.Thread(target=self.timer, daemon=True, name='timer')
                    self.timer_thread.start()

    def run(self):
        # Create list of wall coordinates
        self.battlebots.impossible_positions = self.get_impossible_positions()

        ServerSideSocket = socket.socket()

        try:
            ServerSideSocket.bind(
                (str(self.battlebots.config['server']['ip']), int(self.battlebots.config['server']['port'])))
        except socket.error as e:
            print(str(e))

        print('Socket is listening..')
        ServerSideSocket.listen(5)

        # Create new Client threads
        while not self.battlebots.stopthreads:
            Client, address = ServerSideSocket.accept()
            print('Connected to: ' + address[0] + ':' + str(address[1]))
            start_new_thread(self.multi_threaded_client, (Client,))
