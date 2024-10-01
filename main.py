
# External module imports
import time
import serial
from datetime import date
import mysql.connector
# Database setup:
db = mysql.connector.connect(
    host="localhost",
    user="thvottur",
    passwd="einar228",
    database="thvottadb"
)
myCursor = db.cursor()

# Serial setup:
ser = serial.Serial(
port='/dev/ttyACM0',
baudrate = 9600,
parity=serial.PARITY_NONE,
stopbits=serial.STOPBITS_ONE,
bytesize=serial.EIGHTBITS,
timeout=1
)

# Global starting values

def putIntoTable(table, data):
    insert = f"INSERT INTO {table} (QRcode) VALUES (%s)"
    myCursor.execute(insert, (data, ))
    db.commit()
def searchTable(table, data):
    selectCreated = f"SELECT QRcode FROM {table} WHERE QRcode = %s"
    myCursor.execute(selectCreated, (data, ))
    return myCursor.fetchone()
def delFromValidCodes(data):
    delete = "DELETE FROM validCodes WHERE QRcode = %s"
    myCursor.execute(delete, (data, ))
    db.commit()

while True:
    serData = str(ser.readline().decode("utf-8"))
    print(serData)
    # Checks if serial data is the same as the code of the day
    if searchTable("validCodes", serData):

    elif not searchTable("validCodes", serData) and serData != "":
        
