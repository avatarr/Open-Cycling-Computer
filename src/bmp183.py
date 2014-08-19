import RPi.GPIO as GPIO
import sys
import time
import numpy

class bmp183():
	'Class for BMP183 pressure and temperature sensor'
	BMP183_REG = {
		'CAL_AC1' : 0xAA, 
		'CAL_AC2' : 0xAC,
		'CAL_AC3' : 0xAE,
		'CAL_AC4' : 0xB0,
		'CAL_AC5' : 0xB2,
		'CAL_AC6' : 0xB4,
		'CAL_B1': 0xB6,
		'CAL_B2': 0xB8, 
		'CAL_MB': 0xBA,
		'CAL_MC': 0xBC,
		'CAL_MD': 0xBE,
		#@ Chip ID. Value fixed to 0x55. Usefull to check if communication works
		'ID' : 0xD0,

		#@ VER FIXME Undocumented
		'VER' : 0xD1,

		#@ SOFT_RESET
		# Write only. If set to 0xB6, will perform the same sequence as power on reset.
		'SOFT_RESET' : 0xE0,

		#@ CTRL_MEAS
		# Controls the pressure measurement
		'CTRL_MEAS' : 0xF4,

		#@ DATA
		'DATA' : 0xF6,
	};

	BMP183_CMD = {
		'READWRITE' : 0x80,

		# Read TEMPERATURE, Wait time 4.5 ms
		'TEMP'  : 0x2E,

		# Read PRESSURE
		'PRESS' : 0x34, #001
		
		'OVERSAMPLE_0' : 0x00, # ultra low power, no oversampling, wait time 4.5 ms
		'OVERSAMPLE_1' : 0x40, # standard, 2 internal samples, wait time 7.5 ms
		'OVERSAMPLE_2' : 0x80, # high resolution, 4 internal samples, wait time 13.5 ms
		'OVERSAMPLE_3' : 0xC0, # ultra high resolution, 8 internal samples, Wait time 25.5 ms
		# Usage: (PRESS || OVERSAMPLE_2)

		#FIXME How ADVANCED RESOLUTION mode works? Page 13 of data sheet,  wait time 76.5 ms
	}

	def __init__(self):
		self.SCLK = 8  # GPIO for Clock
		self.MISO = 10  # GPIO for MISO
		self.MOSI = 12  # GPIO for MOSI
		self.CE   = 16  # GPIO for Chip Enable

		self.delay = 1/1000.0

		#start

		# GPIO initialisation
		GPIO.setmode(GPIO.BOARD)
		GPIO.setup(self.SCLK, GPIO.OUT, initial=GPIO.HIGH)
		GPIO.setup(self.CE, GPIO.OUT, initial=GPIO.HIGH)
		GPIO.setup(self.MOSI, GPIO.OUT)
		GPIO.setup(self.MISO, GPIO.IN)

		#Check comunication / read ID
		ret = self.read_byte(self.BMP183_REG['ID'])
		if ret != 0x55:
			print ("BMP183 returned ", ret, " instead of 0x55")
		#Read calibration data
		AC1 = numpy.int16(self.read_word(self.BMP183_REG['CAL_AC1']))
		AC2 = numpy.int16(self.read_word(self.BMP183_REG['CAL_AC2']))
		AC3 = numpy.int16(self.read_word(self.BMP183_REG['CAL_AC3']))
		AC4 = numpy.uint16(self.read_word(self.BMP183_REG['CAL_AC4']))
		AC5 = numpy.uint16(self.read_word(self.BMP183_REG['CAL_AC5']))
		AC6 = numpy.uint16(self.read_word(self.BMP183_REG['CAL_AC6']))
		B1 = numpy.int16(self.read_word(self.BMP183_REG['CAL_B1']))
		B2 = numpy.int16(self.read_word(self.BMP183_REG['CAL_B2']))
		MB = numpy.int16(self.read_word(self.BMP183_REG['CAL_MB']))
		MC = numpy.int16(self.read_word(self.BMP183_REG['CAL_MC']))
		MD = numpy.int16(self.read_word(self.BMP183_REG['CAL_MD']))
		print "AC1", AC1
		print "AC2", AC2
		print "AC3", AC3
		print "AC4", AC4
		print "AC5", AC5
		print "AC6", AC6
		print "B1", B1
		print "B2", B2
		print "MB", MB
		print "MC", MC
		print "MD", MD

		#start TEMP measurement
		#self.write_byte(self.BMP183_REG['CTRL_MEAS'], self.BMP183_CMD['TEMP'], 8)
		#time.sleep(0.05)
		#wait 4.5

		#read uncmpensated temperature u_temp

		#start pressure measurement

		#wait (depend on mode)

		#read uncmpensated pressure u_press

		#calculate real temperature r_temp

		#calculate real pressure r_press

		#end

		GPIO.cleanup(self.SCLK)
		GPIO.cleanup(self.CE)
		GPIO.cleanup(self.MOSI)
		GPIO.cleanup(self.MISO)

	def read_byte(self, addr):
		print 'read_byte'
		ret_value = self.spi_transfer(addr, 0, 1, 8)	
		return ret_value

	def read_word(self, addr):
		print 'read_word'
		ret_value = self.spi_transfer(addr, 0, 1, 16)	
		return ret_value

	def write_byte(self, addr, value, length):
		print 'write_byte'
		self.spi_transfer(addr, value, 0, length)	
		
	def spi_transfer(self, addr, value, rw, length):
		print 'spi_transfer'
		ret_value = 0
		if (rw == 0):
			spi_addr = addr & (~self.BMP183_CMD['READWRITE'])
			print "addr: ", hex(addr), " spi_addr: ", hex(spi_addr), " value: ", hex(value), "length:", length
		else:
			spi_addr = addr | self.BMP183_CMD['READWRITE']
			print "addr: ", hex(addr), " spi_addr: ", hex(spi_addr), "length:", length


		GPIO.output(self.CE, 0)
		time.sleep(self.delay)
		#Send address
		sys.stdout.write('Sending addr: ')
		for i in range(8):
			bit = spi_addr & (0x01 << (7 - i))
			if (bit):
				sys.stdout.write("1")
				GPIO.output(self.MOSI, 1)
			else:
				sys.stdout.write("0")
				GPIO.output(self.MOSI, 0)
			GPIO.output(self.SCLK, 0)
			time.sleep(self.delay)
			GPIO.output(self.SCLK, 1)
			time.sleep(self.delay)
		print(' ')

		if (rw == 1):
			#Read data
			sys.stdout.write('Received: ')
			for i in range(length):
				GPIO.output(self.SCLK, 0)
				time.sleep(self.delay)
				bit = GPIO.input(self.MISO)
				if (bit):
					sys.stdout.write("1")
				else:
					sys.stdout.write("0")
				GPIO.output(self.SCLK, 1)
				ret_value = (ret_value << 1) | bit
				time.sleep(self.delay)
			print(' ')
			print 'ret_value: ', hex(ret_value)

		if (rw == 0):
			print('Writing:')
			print(hex(value))
			for i in range(length):
				bit = value & (0x01 << (length - 1 - i))
				if (bit):
					sys.stdout.write("1")
					GPIO.output(self.MOSI, 1)
				else:
					sys.stdout.write("0")
					GPIO.output(self.MOSI, 0)
				GPIO.output(self.SCLK, 0)
				time.sleep(self.delay)
				GPIO.output(self.SCLK, 1)
				time.sleep(self.delay)
			print(' ')
		GPIO.output(self.CE, 1)
		return ret_value

if __name__ == "__main__":
	bmp = bmp183()
	quit()

