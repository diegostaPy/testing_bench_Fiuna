from smbus2 import SMBus

# Open i2c bus 1 and read one byte from address 80, offset 0
bus = SMBus(1)
read = bus.read_byte_data(0x01,0xB2)
temp=read<<8
read = bus.read_byte_data(0x01,0xB2)
temp=temp+read
print(temp/100)
read = bus.read_byte_data(0x01,0xB3)
hum=read<<8
read = bus.read_byte_data(0x01,0xB3)
hum=hum+read

print(hum/100)
bus.close()