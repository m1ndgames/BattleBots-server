import configparser
import ctypes
from threading import Thread
import PySimpleGUI as Gui
from imagehandler import ImageHandler
from server import BattleBotsServer


class BattleBots:
    def __init__(self):
        super().__init__()
        # Init variables
        self.version = '0.1a'
        self.config = configparser.ConfigParser()
        self.imagehandler = ImageHandler(self)
        self.server = BattleBotsServer(self)
        self.setup_done = False
        self.stopthreads = False
        self.game = None
        self.mapfile = None

    def setup(self):
        ctypes.windll.user32.SetProcessDPIAware()

        self.config.read('config.ini')
        self.map = self.config['game']['map']

        # Start server_thread
        server_thread = Thread(target=self.server.run)
        server_thread.setDaemon(True)
        server_thread.start()

        # Start mapgen_thread
        mapgen_thread = Thread(target=self.imagehandler.run)
        mapgen_thread.setDaemon(True)
        mapgen_thread.start()

        # Start server_processor thread
        processor_thread = Thread(target=self.server.server_processor)
        processor_thread.setDaemon(True)
        processor_thread.start()

        self.setup_done = True

    def run(self):
        # Run setup routine
        if not self.setup_done:
            self.setup()

        # Set theme
        Gui.theme('DarkAmber')

        # Create the layout
        layout = [
            [Gui.Image(data=self.imagedata, key='map')]
        ]

        # Create the window
        window = Gui.Window(title='BattleBotsServer ' + self.version, no_titlebar=False, layout=layout, finalize=True, keep_on_top=True, grab_anywhere=True, return_keyboard_events=True)

        # Run GUI
        while True:
            event, values = window.read(timeout=100)
            if event == Gui.WIN_CLOSED:
                break

            window.Element('map').Update(data=self.imagedata)
            window.refresh()

        self.stopthreads = True
        window.close()
