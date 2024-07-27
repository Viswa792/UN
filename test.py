from pymongo import MongoClient
from flask import Flask,render_template,url_for,redirect,session

client = MongoClient('mongodb://localhost:27017/')
db = client.UN
rm = db.people
db.people.find_one({'room_no': 1})
@app.route('/get_names', methods=['GET'])
def get_names():
    roomno = request.args.get('roomno')
    # Fetch names from database based on roomno
    # Example data
    names_by_room = db.people.find_one({'room_no': 1})
    names = names_by_room.get(roomno, [])
    return jsonify({'names': names})