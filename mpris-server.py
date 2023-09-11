import threading
import time
import curses
import os
import dbus, argparse, json, socket
from threading import Thread


SERVICE_PREFIX = 'org.mpris.MediaPlayer2.'
DBUS_INTERFACE = 'org.freedesktop.DBus.Properties'
OBJECT_PATH = "/org/mpris/MediaPlayer2"
PLAYER_INTERFACE = 'org.mpris.MediaPlayer2.Player'

PLAYER_PREF_PATH = "player_pref.json"
SERVER_HOST = ""
SERVER_PORT = 8888

class MediaInfoThread(threading.Thread):
    def __init__(self, controller):
        threading.Thread.__init__(self)
        self.controller = controller
        self.running = False
        
    def run(self):
            self.running = True
            while self.running:
                metadata = self.controller.fetch_player_metadata(self.controller.preferred_player())
                if metadata:
                    artist = metadata.get('xesam:artist', [])
                    data = f"Song: {metadata.get('xesam:title', '')}\nArtist: {''.join(map(str,artist))}\nAlbum: {metadata.get('xesam:album', '')}"
                    print_info(data)
                time.sleep(2)

    def stop(self):
        self.running = False        

def print_info(data):
    stdscr = curses.initscr()
    stdscr.clear()
    stdscr.addstr(0, 0, data)
    stdscr.refresh()

class MediaPlayer:
    def __init__(self, bus):
        self.bus = bus

    def fetch_player_metadata(self, service_name):
        player_object = self.bus.get_object(service_name, OBJECT_PATH)
        player_interface = dbus.Interface(player_object, dbus_interface=DBUS_INTERFACE)
        return player_interface.Get('org.mpris.MediaPlayer2.Player', 'Metadata')

    @classmethod
    def print_metadata(cls, metadata, info_mode):
        if info_mode:
            artist = metadata.get('xesam:artist', [])
            print(f"Song: {metadata.get('xesam:title', '')}")
            print(f"Artist: {''.join(map(str,artist))}")
            print(f"Album: {metadata.get('xesam:album', '')}")
        print()

    @staticmethod
    def is_valid_service(service):
        return service.startswith(SERVICE_PREFIX)

    def process_services(self, services, info_mode):
        for service in services:
            if self.is_valid_service(service):
                metadata = self.fetch_player_metadata(service)
                if metadata:
                    self.print_metadata(metadata, info_mode)

    def preferred_player(self):
        return self.load_preference() if os.path.exists(PLAYER_PREF_PATH) else None

    def retrieve_services(self):
        return [service for service in self.bus.list_names() if self.is_valid_service(service)]

    def user_select_player(self, available_services):
        print("Available players:")
        for i, service in enumerate(available_services, start=1):
            print(f"{i}. {service[len(SERVICE_PREFIX):]}")
        user_choice = int(input("Select your preferred player by entering its corresponding number: ")) - 1
        self.save_preference(available_services[user_choice])
        self.process_services([available_services[user_choice]], args.info)

    def load_preference(self):
        with open(PLAYER_PREF_PATH, "r") as file:
            pref_service = json.load(file)
        return pref_service

    def save_preference(self, service):
        with open(PLAYER_PREF_PATH, "w") as file:
            json.dump(service, file)

    def run_tcp_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((SERVER_HOST, SERVER_PORT))
        server.listen(1)
        print(f"[*] Listening as {SERVER_HOST}:{SERVER_PORT}")

        while True:
            client_socket, client_address = server.accept()
            print(f"[+] {client_address} connected.")
            handle_thread = Thread(target=self.handle_client, args=(client_socket,))
            handle_thread.start()

    def control_player(self, service_name, command):
        player_object = self.bus.get_object(service_name, OBJECT_PATH)
        player_interface = dbus.Interface(player_object, dbus_interface=PLAYER_INTERFACE)
        if command.lower() in ["play", "pause", "next", "previous"]:
            getattr(player_interface, command.capitalize())()
        else:
            print(f"Invalid command: {command}")

    def handle_client(self, client_socket):
        preferred_service = self.preferred_player()
        if preferred_service and preferred_service in self.bus.list_names():
            info_thread = MediaInfoThread(self)
            info_thread.start()
            while True:
                msg = client_socket.recv(1024).decode().strip()
                if msg.lower() in ["play", "pause", "next", "previous"]:
                    self.control_player(preferred_service, msg)
                    metadata = self.fetch_player_metadata(preferred_service)
                    if metadata:
                        artist = metadata.get('xesam:artist', [])
                        data = f"Song: {metadata.get('xesam:title', '')}\nArtist: {''.join(map(str,artist))}\nAlbum: {metadata.get('xesam:album', '')}"
                        client_socket.send(data.encode())
                    else:
                        client_socket.send("No song info available.".encode())
                elif msg.lower() == "info":
                    metadata = self.fetch_player_metadata(preferred_service)
                    if metadata:
                        artist = metadata.get('xesam:artist', [])
                        data = f"Song: {metadata.get('xesam:title', '')}\nArtist: {''.join(map(str,artist))}\nAlbum: {metadata.get('xesam:album', '')}"
                        client_socket.send(data.encode())
                    else:
                        client_socket.send("No song info available.".encode())
                elif msg.lower().startswith('switch '): 
                    new_service = SERVICE_PREFIX + msg.lower().split(' ', 1)[1]
                    if new_service in self.bus.list_names():
                        preferred_service = new_service
                        client_socket.send(f"Switched to {new_service}.".encode())
                    else:
                        client_socket.send(f"No such service {new_service}.".encode())
                else:
                    if msg.lower() == 'quit':
                        info_thread.stop()
                        info_thread.join()
                        break
                    client_socket.send("Invalid command. Commands can be: play, pause, next, previous, info.".encode())
            client_socket.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-info", action="store_true", help="output limited to the song name, the artist, and the album")
    parser.add_argument("-tcp", action="store_true", help="operate as a TCP server to send song info to client")
    parser.add_argument("-control", choices=["play", "pause", "next", "previous"], help="control media playback")
    parser.add_argument("-reselect", action="store_true", help="re-select preferred media player")
    args = parser.parse_args()

    bus = dbus.SessionBus()
    player = MediaPlayer(bus)

    if args.tcp:
        player.run_tcp_server()

    elif args.control:
        preferred_service = player.preferred_player()
        if preferred_service and preferred_service in bus.list_names():
            try:
                player.control_player(preferred_service, args.control)
            except Exception as e:
                print(f"Error in controlling player: {e}")

    elif args.reselect:
            try:
                available_services = player.retrieve_services()
                player.user_select_player(available_services)
            except Exception as e:
                print(f"Error while attempting to reselect player: {e}")

    else:    
        preferred_service = player.preferred_player()

        if preferred_service and preferred_service in bus.list_names():
            try:
                player.process_services([preferred_service], args.info)
            except Exception as e:
                print(f"Error in processing service: {e}")
        else:
            try:
                available_services = player.retrieve_services()
                player.user_select_player(available_services)
            except Exception as e:
                print(f"Error in processing services: {e}")
