#!/usr/bin/python

import os
import pygame
from pygame.locals import *
from pygame.compat import unichr_, unicode_
import RPi.GPIO as GPIO
import sys
import locale



class open_cycle_computer():
	'Class for PiTFT 2.8" 320x240 cycle computer'
	def __init__(self, width = 240, height = 320):
		#TODO Move gpio handling to separate file 
		def speed_sensor_prox (channel):
			speed_prox_time_now = pygame.time.get_ticks()
			if (self.speed_prox_time != 0):
				self.speed_prox_time_delta = speed_prox_time_now - self.speed_prox_time 

			self.speed_prox_time = speed_prox_time_now
		
		# GPIO setup
		GPIO.setmode(GPIO.BCM)
		# 18 will be speed GPIO for now
		GPIO.setup(18, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)
		# bouncetimeis set to 
		# 120 km/h --> 33.333 m/s @ 20" wheel size (1.596 m) = 20.88 imp/s = 4.788 ms ~5 ms
		GPIO.add_event_detect(18, GPIO.RISING, callback=speed_sensor_prox, bouncetime=5)
		self.speed_prox_time = 0
		self.speed_prox_time_delta = 0

		os.environ["SDL_FBDEV"] = "/dev/fb1"
		pygame.init()
		pygame.mouse.set_visible(0)
		self.width = width
		self.height = height
		self.screen = pygame.display.set_mode((self.width, self.height), pygame.FULLSCREEN)
		self.clock = pygame.time.Clock()
		self.fg_colour = 255, 255, 255
		self.bg_image = pygame.image.load("images/occ_dark_green.png").convert()

	def main_loop(self):
		while 1:
			for event in pygame.event.get():
				if event.type in (QUIT, KEYDOWN, MOUSEBUTTONDOWN):
					sys.exit()
			t = 10
			#TODO Read values for rendering from a file here
			self.screen.blit(self.bg_image, [0, 0])
			#TODO Just show delta / 10 for now - not real speed
			self.render_top(self.speed_prox_time_delta / 10)
			self.render_mid(t)
			self.render_bl(t)
			self.render_br(t)
			self.draw_speed_unit()
			self.clock.tick(20)
			pygame.display.flip()

	def render_value(self, value, position, size):
		font = pygame.font.Font(None, 12 * size)
		ren = font.render(value, 1, self.fg_colour)
		x = ren.get_rect().centerx
		y = ren.get_rect().centery
		self.screen.blit(ren, (position[0] - x, position[1] - y))

	def render_top(self, value):
		self.render_value(str(value), (120 - 25, 75), 20)

	def render_mid(self, value):
		self.render_value(str(value), (120, 195), 12)

	def render_bl(self, value):
		self.render_value(str(value), (60, 280), 10)

	def render_br(self, value):
		self.render_value(str(value), (180, 280), 10)

	def draw_speed_unit(self):
		self.render_value("km/h", (210, 75), 3)

if __name__ == "__main__":
	main_window = open_cycle_computer()
	main_window.main_loop()
