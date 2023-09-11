import socket
import time
import threading
import curses
import contextlib
import argparse

REFRESH_FREQUENCY = 2
COMMANDS = ["play", "pause", "next", "previous", "info", "switch"]
CLEAR_DELAY = 5

class MusicClient:
    def __init__(self, server_host, server_port):
        self.server_host = server_host
        self.server_port = server_port
        self.setup_display()

    def setup_display(self):
        self.stdscr = curses.initscr()
        self.lines, self.cols = self.stdscr.getmaxyx()
        self.cmd_window = curses.newwin(1, self.cols, self.lines - 1, 0)
        self.info_window = self.stdscr.subwin(self.lines - 1, self.cols, 0, 0)
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        self.stdscr.timeout(100)
        self.stdscr.keypad(True)

    def auto_request_song_info(self, s):
        while True:
            try:
                self.info_window.clear()
                self.info_window.addnstr(0, 0, "Song Info:", self.cols-1)
                s.send('info'.encode())
                data = s.recv(1024).decode()
                data = data[:self.cols-1]
                self.info_window.addnstr(1, 0, data, self.cols-1-1)
                self.info_window.refresh()
                time.sleep(REFRESH_FREQUENCY)
            except curses.error:
                pass

    def process_user_input(self, s):
        while True:
            try:
                self.cmd_window.clear()
                self.cmd_window.addnstr(0, 0, "Type command (play, pause, next, switch etc.) here:", self.cols-1)
                command = self.cmd_window.getstr().decode()
                if command.lower().split(' ')[0] in COMMANDS:
                    s.send(command.encode())
                    data = s.recv(1024).decode()
                    self.cmd_window.addnstr(1, 0, data[:self.cols-1], self.cols-1)
                else:
                    self.cmd_window.addnstr(1, 0, "Invalid command", self.cols-1)
                time.sleep(CLEAR_DELAY)
                self.cmd_window.clear()
            except curses.error:
                pass

    def main(self):
        with contextlib.closing(self.create_connection()) as s:
            threading.Thread(target=self.auto_request_song_info, args=(s,), daemon=True).start()
            self.process_user_input(s)
            
    def create_connection(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.server_host, int(self.server_port)))
            return s
        except Exception as e:
            print(f"Error: {e}")
            raise e

    def end_session(self):
        curses.nocbreak()
        self.stdscr.keypad(False)
        curses.echo()
        curses.endwin()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("address", type=str, help="Server address in the format 'host:port'")
    args = parser.parse_args()
    server_host, server_port = args.address.split(":")
    client = MusicClient(server_host, server_port)
    try:
        client.main()
    finally:
        client.end_session()
