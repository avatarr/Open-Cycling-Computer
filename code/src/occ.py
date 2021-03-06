#!/usr/bin/python
# -*- coding: utf-8 -*-
## @package occ
#  OpenCyclingCompyter main file
#
#  http://opencyclingcomputer.eu/

from ble_scanner import ble_scanner
from layout import layout
from config import config
from operator import add
from pygame.locals import NOEVENT
from pygame.locals import USEREVENT
from rendering import rendering
from ride_parameters import ride_parameters
from sensors import sensors
from time import sleep
from time import strftime
import logging
import logging.handlers
import os
import platform
import pygame
import signal

## @var LOG_LEVEL
# Log level definitions
LOG_LEVEL = {"DEBUG": logging.DEBUG,
             "INFO": logging.INFO,
             "WARNING": logging.WARNING,
             "ERROR": logging.ERROR,
             "CRITICAL": logging.CRITICAL}

## @var LONG_CLICK
# Time of long click in ms All clicks over 800 ms are considered "long".
LONG_CLICK = 800

## @var SWIPE_LENGTH
# Lenght of swipe in pixels. All clicks with length ver 30 pixels are considered swipes.
SWIPE_LENGTH = 30

## @var EV_UPDATE_VALUES
# Custom pygame event used to trgger updating values in ride_parameters.
EV_UPDATE_VALUES = USEREVENT + 1

## @var EV_SAVE_CONFIG
# Custom pygame event used to trgger config file save.
EV_SAVE_CONFIG = USEREVENT + 2

## @var REFRESH_TIME
# Period of time in ms between EV_UPDATE_VALUES events.
REFRESH_TIME = 1000

## @var CONFIG_SAVE_TIME
# Period of time in ms between EV_SAVE_CONFIG events.
CONFIG_SAVE_TIME = 15000


## Main OpenCyclingComputer class
# Based on RPI model A+ and PiTFT 2.8" 320x240
class open_cycling_computer(object):

    ## The constructor
    #  @param self The python object self
    #  @param simulate Decides if OCC runs in simulation mode or real device mode. Simulation mode is useful for test on non-raspberry pi hardware. Default value is False.
    #  @param width Width of screen or window. Default value is 240 pixels
    #  @param height Height of screen or window.  Default value is 320 pixels
    def __init__(self, simulate=False, width=240, height=320):
        ## @var simulate
        #  Stores simulate parameter from constructor call
        self.simulate = simulate
        ## @var l
        #  Handle to system logger
        self.l = logging.getLogger('system')
        pygame.init()
        # pygame.display.init()
        if not self.simulate:
            pygame.event.set_grab(True)
            pygame.mouse.set_visible(0)
        self.l.debug("[OCC] EV_UPDATE_VALUES to be generated every {} ms".format(REFRESH_TIME))
        pygame.time.set_timer(EV_UPDATE_VALUES, REFRESH_TIME)
        self.l.debug(
            "[OCC] EV_SAVE_CONFIG to be generated every {} s".format(CONFIG_SAVE_TIME / 1000))
        pygame.time.set_timer(EV_SAVE_CONFIG, CONFIG_SAVE_TIME)
        ## @var width
        #  Window/screen width
        self.width = width
        ## @var height
        #  Window/screen height
        self.height = height
        self.l.debug("[OCC] Screen size is {} x {}".format(self.width, self.height))
        ## @var screen
        #  Handle to pygame screen
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.l.debug("[OCC] Calling sensors")
        ## @var sensors
        #  Handle to sensors instance
        self.sensors = sensors(self)
        self.l.debug("[OCC] Calling ride_parameters")
        ## @var rp
        #  Handle to ride_parameters instance
        self.rp = ride_parameters(self, simulate)
        ## @var layout_path
        #  Path to layout file
        self.layout_path = ''
        self.l.debug("[OCC] Initialising config")
        ## @var config
        #  Handle to config instance
        self.config = config(self, "config/config.yaml", "config/config_base.yaml")
        self.l.debug("[OCC] Reading config")
        self.config.read_config()
        ## @var ble_scanner
        #  Handle to ble_scanner instance
        self.ble_scanner = ble_scanner(self)
        ## @var layout
        #  Handle to layout instance
        self.layout = layout(self, self.layout_path)
        self.l.debug("[OCC] Starting RP sensors")
        self.rp.start_sensors()
        self.l.debug("[OCC] Setting up rendering")
        ## @var rendering
        #  Handle to rendering instance
        self.rendering = rendering(self.layout)
        self.l.debug("[OCC] Starting rendering thread")
        self.rendering.start()
        ## @var released_t
        #  Time stamp of pygame.MOUSEBUTTONUP event (end of finger contact with touchscreen)
        self.released_t = 0
        ## @var rel_movement
        #  Vector since MOUSEBUTTONDOWN event. Used to derermine swipe motion.
        self.rel_movement = (0, 0)
        ## @var pressed_t
        #  Time stamp of pygame.MOUSEBUTTONDOWN event (start of finger contact with touchscreen)
        self.pressed_t = 0
        ## @var pressed_pos
        #  Position of pygame.MOUSEBUTTONDOWN event (start of finger contact with touchscreen)
        self.pressed_pos = (0, 0)
        ## @var released_pos
        #  Position of pygame.MOUSEBUTTONUP event (end of finger contact with touchscreen)
        self.released_pos = 0
        ## @var add_rel_motion
        #  Used to control if finger/mouse vectors should be tracked to determine total relative motion
        self.add_rel_motion = False
        ## @var running
        #  Variable controlling the main occ event loop. pygame.QUIT event triggers setting running to False
        self.running = True
        ## @var refresh
        #  Variable controlling if the screen need to be refreshed
        self.refresh = False

    ## Provides events from pygame system
    #  @param self The python object self
    def event_iterator(self):
        while True:
            yield pygame.event.wait()
            while True:
                event = pygame.event.poll()
                if event.type == NOEVENT:
                    break
                else:
                    yield event

    def force_refresh(self):
        self.refresh = True

    ## Switches logging level
    #  @param self The python object self
    #  @param log_level Log level to be set. Allowed levels are in \link LOG_LEVEL \endlink
    def switch_log_level(self, log_level):
        self.l.setLevel(LOG_LEVEL[log_level])
        self.l.log(100, "[OCC] Switching to log_level {}".format(log_level))

    ## Main click and swipe handler
    #  @param self The python object self
    #  @param time_now is event time passwd from the main event loop
    def screen_touched_handler(self, time_now):
        if (time_now - self.pressed_t) > LONG_CLICK:
            self.l.debug("[OCC] LONG CLICK : {} {} {}".format(
                time_now, self.pressed_t, self.pressed_pos))
            self.layout.check_click(self.pressed_pos, 'LONG')
            self.reset_motion()
        if self.released_t != 0:
            self.l.debug("[OCC] SHORT CLICK : {} {} {}".format(
                time_now, self.pressed_t, self.pressed_pos))
            self.layout.check_click(self.pressed_pos, 'SHORT')
            self.reset_motion()
        dx = self.rel_movement[0]
        dy = self.rel_movement[1]
        if (abs(dx)) > SWIPE_LENGTH:
            if dx > 0:
                self.l.debug("[OCC] SWIPE X RIGHT to LEFT : {} {} {} {} {} {}".
                             format(time_now, self.pressed_t, self.pressed_pos, self.released_pos, dx, dy))
                self.layout.check_click(self.pressed_pos, 'R_TO_L')
                self.reset_motion()
            else:
                self.l.debug("[OCC] SWIPE X LEFT to RIGHT : {} {} {} {} {} {}".
                             format(time_now, self.pressed_t, self.pressed_pos, self.released_pos, dx, dy))
                self.layout.check_click(self.pressed_pos, 'L_TO_R')
                self.reset_motion()
        elif (abs(dy)) > SWIPE_LENGTH:
            if dy < 0:
                self.l.debug("[OCC] SWIPE X BOTTOM to TOP : {} {} {} {} {} {}".
                             format(time_now, self.pressed_t, self.pressed_pos, self.released_pos, dx, dy))
                self.layout.check_click(self.pressed_pos, 'B_TO_T')
                self.reset_motion()
            else:
                self.l.debug("[OCC] SWIPE X TOP to BOTTOM : {} {} {} {} {} {}".
                             format(time_now, self.pressed_t, self.pressed_pos, self.released_pos, dx, dy))
                self.layout.check_click(self.pressed_pos, 'T_TO_B')
                self.reset_motion()

    ## Main event handler
    #  @param self The python object self
    #  @param event Pygame event
    #  @param time_now is event time passwd from the main event loop
    def event_handler(self, event, time_now):
        if event.type == pygame.QUIT:
            self.running = False
            self.l.debug("[OCC] QUIT {}".format(time_now))
        elif event.type == EV_UPDATE_VALUES:
            self.l.debug("[OCC] calling update_values {}".format(time_now))
            self.rp.update_values()
        elif event.type == EV_SAVE_CONFIG:
            self.l.debug("[OCC] calling write_config {}".format(time_now))
            self.config.write_config()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.pressed_t = time_now
            self.pressed_pos = pygame.mouse.get_pos()
            # Read rel to clean the value generated on click
            pressed_rel = pygame.mouse.get_rel()
            self.add_rel_motion = True
            self.layout.render_button = self.pressed_pos
            self.l.debug("[OCC] DOWN:{} {} {}".format(
                self.pressed_t, self.released_t, self.pressed_pos))
        elif event.type == pygame.MOUSEBUTTONUP:
            # That check prevents setting release_x after long click
            if (self.pressed_t != 0):
                self.released_t = time_now
                self.released_pos = pygame.mouse.get_pos()
            self.add_rel_motion = False
            self.layout.render_button = None
            self.l.debug("[OCC] UP: {} {} {}".format(
                self.pressed_t, self.released_t, self.pressed_pos))
        elif event.type == pygame.MOUSEMOTION:
            pressed_rel = pygame.mouse.get_rel()
            if self.add_rel_motion:
                self.rel_movement = tuple(map(add, self.rel_movement, pressed_rel))
            self.l.debug("[OCC] MOTION: {}".format(self.rel_movement))
        # self.l.debug("[OCC] ticking:time_now:{} pressed_t:{} pressed_pos:{} released_t:{} released_pos:{}". \
        # format(time_now, self.pressed_t, self.pressed_pos, self.released_t,
        # self.released_pos))
        if self.pressed_t != 0:
            self.refresh = True
            self.screen_touched_handler(time_now)

    ## Main event loop. Pools eventr from event_iterator, calls event_handler
    #  @param self The python object self
    def main_loop(self):
        self.l.debug("[OCC][F] main_loop")
        self.reset_motion()
        while self.running:
            for event in self.event_iterator():
                time_now = pygame.time.get_ticks()
                self.event_handler(event, time_now)
                if not self.running:
                    break
                if self.refresh:
                    self.refresh = False
                    self.rendering.force_refresh()

    ## Resets all parameters related to clicks/swipes
    #  @param self The python object self
    def reset_motion(self):
        self.l.debug("[OCC][F] reset_motion")
        self.pressed_t = 0
        self.released_t = 0
        self.pressed_pos = (0, 0)
        self.released_pos = (0, 0)
        self.rel_movement = (0, 0)
        self.layout.render_button = None
        self.add_rel_motion = False
        pygame.event.clear()

    ## Returns simulate variable
    #  @param self The python object self
    def get_simulate(self):
        return self.simulate

    ## Clean up function. Stops ride_parameters, writes config and layout, calls pygame quit and ends OCC. Should never be user it the real device once the code is rady. Used on development version.
    #  @param self The python object self
    def cleanup(self):
        self.l.debug("[OCC] Cleaning...")
        sleep(1)
        self.rp.stop()
        try:
            self.rendering.stop()
        except AttributeError:
            self.l.debug("[OCC] self.rendering.stop() produced AttributeError")
        try:
            self.config.write_config()
        except AttributeError:
            self.l.debug("[OCC] self.config.write_config() produced AttributeError")
        try:
            self.layout.write_layout()
        except AttributeError:
            self.l.debug("[OCC] self.layout.write_layout() produced AttributeError")
        pygame.quit()
        self.l.debug("[OCC] Log end")
        quit()


## Quit handler, triggers cleanup function after SIGTERM or SIGINT
#  @param signal TBC
#  @param frame TBC
def quit_handler(signal, frame):
    main_window.cleanup()


if __name__ == "__main__":
    ## @var suffix
    # Log suffix
    suffix = strftime("%d-%H:%M:%S")
    ## @var sys_log_filename
    # Log filename
    sys_log_filename = "log/debug." + suffix + ".log"
    logging.getLogger('system').setLevel(logging.DEBUG)
    ## @var sys_log_handler
    # Log handler
    sys_log_handler = logging.handlers.RotatingFileHandler(sys_log_filename)
    ## @var sys_log_format
    # Log format string
    sys_log_format = '[%(levelname)-5s] %(message)s'
    sys_log_handler.setFormatter(logging.Formatter(sys_log_format))
    logging.getLogger('system').addHandler(sys_log_handler)
    ## @var sys_logger
    # System logger handle
    sys_logger = logging.getLogger('system')
    signal.signal(signal.SIGTERM, quit_handler)
    signal.signal(signal.SIGINT, quit_handler)
    sys_logger.debug("[OCC] Log start")
    # This is a simple check if we're running on Raspberry PI.
    # Switch to simulation mode if we're not
    if (platform.machine() == "armv6l"):
        os.putenv('SDL_MOUSEDEV', '/dev/input/touchscreen')
        os.environ["SDL_FBDEV"] = "/dev/fb1"
        os.putenv('SDL_VIDEODRIVER', 'fbcon')
        os.putenv('SDL_MOUSEDRV', 'TSLIB')
        ## @var simulate
        #  Stores simulate parameter. It's True on non armv6l platform
        simulate = False
    else:
        simulate = True
        sys_logger.warning(
            "Warning! platform.machine() is NOT armv6l. I'll run in simulation mode. No real data will be shown.")
    ## @var main_window
    # OCC main window. It's instance of open_cycling_computer class
    main_window = open_cycling_computer(simulate)
    sys_logger.debug("[OCC] simulate = {}".format(simulate))
    main_window.main_loop()
    main_window.cleanup()
