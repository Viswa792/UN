from flask import Flask,render_template,url_for,redirect,session,request,flash,jsonify,make_response
from pymongo import MongoClient
import os
import datetime
from functools import wraps
from bson import ObjectId 
app=Flask(__name__)
app.secret_key = os.urandom(24)

client = MongoClient('mongodb://localhost:27017/')
db = client.UN
fm = db.foodmenu

def login_requires(f):
    @wraps(f)
    def wrap(*args,**kwargs):
        if 'logged_in' in session:
            return f(*args,**kwargs)
        else:
            return redirect(url_for("login"))
    return wrap
"""for reloading 
"""
@app.after_request
def add_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response
"""------"""
"""FOR NAME DYNAMIC LOADING"""
@app.route('/get_names', methods=['GET'])

def get_names():
    roomno = request.args.get('roomno')
    if roomno:
        result = db.people.find({'room_no': int(roomno)})
        names = [person['Name'] for person in result]
        return jsonify({'names': names})
    return jsonify({'names': []})

@app.route('/remove_member', methods=['POST'])
def remove_member():
    roomno = request.form['roomno']
    name = request.form['name']
    if roomno and name:
        db.people.delete_one({'room_no': int(roomno), 'Name': name})
        db.rooms.update_one({"RoomNo": int(roomno)}, {"$inc": {"Filled": -1}})
    return redirect(url_for('superadminlogin'))
""""""
@app.route('/')
@app.route('/about')
def about():
    session.clear()
    return render_template('about.html')
@app.route('/bookroom')
def bookroom():
    session.clear()
    return render_template('bookroom.html')
@app.route('/availablerooms')
def availablerooms():
    session.clear()
    rm = db.rooms
    data=rm.find({"$expr": {"$lt": ["$Filled", "$RoomType"]}})
    return render_template('availablerooms.html',entry=data)
@app.route('/foodmenu')
def foodmenu():
    session.clear()
    data = fm.find_one()
    return render_template('foodmenu.html',menu=data)
@app.route('/logincreate', methods=["GET", "POST"])
def logincreate():
    users = db.admin

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['1password']

        # Check if the username exists in the admin collection
        user = users.find_one({'username': username})
        if user:
            # Update the password for the user in the admin collection
            users.update_one({'username': username}, {'$set': {'password': password}})
            db.admin.update_one({ 'username': username },{'$set':  {"otp": 0 }})
            return redirect(url_for("login"))  # Redirect to login page after successful update
        else:
            # Handle case where user does not exist
            # You might want to handle this according to your application logic
            return "User not found"

    # If it's a GET request or if the form submission fails, redirect or render as needed
    return redirect(url_for("login"))
@app.route('/login', methods=["GET", "POST"])
def login():
    users = db.admin
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users.find_one({'username': username})

        if user: 
            try:
                if user['password'] == password:  # Assuming password stored in plain text
                    session['username'] = username
                    session['logged_in'] = True
                    session['type']=db.admin.find_one(
            { "username":username },  # Query criteria
            { "_id": 0, "type": 1 }  # Projection: include 'type', exclude '_id'
        )["type"]
                    return redirect(url_for('superadminlogin'))  # Redirect to super admin dashboard
                
                elif user['otp'] is not None and user['otp'] == password :
                    return render_template('logincreate.html',id=username)
                else:
                        return render_template('login.html', error=1)
            except:
                 return render_template('login.html', error=1)
        
        else:
                return render_template('login.html', error=1) 
            

    return render_template('login.html', error=0)
@app.route('/addadmin', methods=["GET", "POST"])
@login_requires
def addadmin():
    if request.method=="POST":
        name=request.form['adminname']
        email=request.form['adminemail']
        ph=request.form['adminph']
        type=request.form['admintype']
        password= str(os.urandom(10))
        otp=request.form['otp']
        db.admin.insert_one({ "Name": name[0].upper(),"username": email,"ph": ph,"password": password,"type": type,"otp":otp})
    return redirect(url_for("superadminlogin"))
@app.route('/deleteadmin', methods=["GET", "POST"])
@login_requires
def deleteadmin():
    if request.method == "POST":
        name = request.form['adminuser']
        result = db.admin.delete_one({"username": name})
        if result.deleted_count > 0:
            flash(f"Admin {name} successfully deleted", "success")
        else:
            flash(f"Admin {name} not found", "error")
    return redirect(url_for("superadminlogin")) 
@app.route('/superadminlogin')
@login_requires
def superadminlogin():
    adminss=db.admin.find()
    #########
    name=db.rooms.find()
    admin_rooms=[]
    for i in name:
        admin_rooms.append(i['RoomNo'])
    #####
    rentcollection={}
    expensecollection={}
    for i in db.admin.find():
        pipeline = [
    { '$match': { 'By': i['Name'] } },  # Filter documents where By field is equal to "C"
    { '$group': {
        '_id': None,  # Group all documents together (since we want the total sum)
        'total': { '$sum': '$Rent' }  # Calculate the sum of Rent field
    }}
]
        rentcollection = {}
    expensecollection = {}

    # Iterate over admin collection
    for admin in db.admin.find():
        # Define aggregation pipelines for rent and expense collections
        rent_pipeline = [
            { '$match': { 'By': admin['Name'] ,'Status':'paid'} },  # Filter documents where By field matches admin's Name
            { '$group': {
                '_id': None,  # Group all documents together (since we want the total sum)
                'total': { '$sum': '$Rent' }  # Calculate the sum of Rent field
            }}
        ]

        expense_pipeline = [
            { '$match': { 'By': admin['Name'] } },  # Filter documents where By field matches admin's Name
            { '$group': {
                '_id': None,  # Group all documents together (since we want the total sum)
                'total': { '$sum': '$Amount' }  # Calculate the sum of Amount field
            }}
        ]

        # Perform aggregations
        rent_aggregation = list(db.rent.aggregate(rent_pipeline))
        expense_aggregation = list(db.expense.aggregate(expense_pipeline))

        # Store results in dictionaries
        rentcollection[admin['Name']] = rent_aggregation[0]['total'] if rent_aggregation else 0
        expensecollection[admin['Name']] = expense_aggregation[0]['total'] if expense_aggregation else 0

    current_year = datetime.datetime.now().year
    current_month = datetime.datetime.now().strftime('%Y-%m')
    return render_template("super_dashboard.html",sessions=session,admin=adminss,current_month=current_month,rentcollection=rentcollection,expensecollection=expensecollection,names=admin_rooms)
@app.route('/logout')
@login_requires
def logout():
    session.clear()
    # Redirect to login page
    return redirect(url_for('about'))
@app.route('/adminfoodmenu')
@login_requires
def adminfoodmenu():
    if session:
        menu=fm.find_one()
        return render_template('adminfoodmenu.html',menu=menu)
    else:
        return redirect(url_for("superadminlogin")) 

@app.route('/update_menu', methods=['POST'])
@login_requires
def update_menu():
    edited_menu = {
        'Breakfast': request.form['Breakfast'],
        'morningsnack': request.form['morningsnack'],
        'lunch': request.form['lunch'],
        'eveningsnack': request.form['eveningsnack'],
        'dinner': request.form['dinner']
    }
    # Update the menu in MongoDB
    fm.update_one({}, {'$set': edited_menu}, upsert=True)
    return redirect(url_for('adminfoodmenu', message='Menu updated successfully'))

@app.route('/adminroomdetails')
@login_requires
def adminroomdetails():
    rm = db.rooms
    data=rm.find()
    return render_template('adminroomdetails.html',rooms=data)
@app.route('/edit_room', methods=['POST'])
@login_requires
def edit_room():
    
    room_no = request.form['room_no']
    sharing = request.form['sharing']    
    # Update room details in MongoDB based on room_no
    result = db.rooms.update_one({'RoomNo': int(room_no)}, {'$set': {'RoomType': int(sharing)}})
    return redirect(url_for('adminroomdetails'))
@app.route('/delete_room', methods=['POST'])
@login_requires
def delete_room():
    if request.method == 'POST':
        room_no = request.form['room_no']
        # Assuming 'db' is your database connection
        db.rooms.delete_one({"RoomNo": int(room_no)})
        return redirect(url_for('adminroomdetails'))
@app.route('/add_room', methods=['POST'])
@login_requires
def add_room():
    # Add new room to MongoDB based on form data
    room_no = request.form['room_no']
    sharing = request.form['sharing']
    existing_room = db.rooms.find_one({'RoomNo': int(room_no)})
    if existing_room:
        return redirect(url_for('adminroomdetails'))
    db.rooms.insert_one({'RoomNo': int(room_no), 'RoomType': int(sharing),'Filled':0})
    return redirect(url_for('adminroomdetails'))

"""GOING TO WORK ON ADMIN RENT

"""
@app.route("/adminrent")
@login_requires
def adminrent():
    name=db.admin.find()
    admin_names=[]
    for i in name:
        admin_names.append(i['Name'])
    paidlist=db.rent.find({'Status':'paid'})
    notpaidlist=db.rent.find({'Status':'notpaid'})
    return render_template("adminrent.html",paidlist=paidlist,notpaidlist=notpaidlist,names=admin_names)
@app.route("/rentchange", methods=['POST'])
@login_requires
def rentchange():
     if request.method == 'POST':
        action = request.form['action']
        room_no = request.form['room_no']
        name=request.form['name']
        if action == 'paid':
            # Update MongoDB record to mark the room as paid
            by_input = request.form.get("cd")
            by = by_input.upper() if by_input else 'Unknown'  # Handle byInput if it's not provided
            db.rent.update_one({'RoomNo': int(room_no), 'Name': name}, {'$set': {'Status': 'paid', 'By': by}})
            flash(f'Room {room_no} for {name} is updated to Paid', 'success')
            flash('Room status updated to Paid', 'success')  # Optional: Flash message for update
        else:
            db.rent.update_one({'RoomNo': int(room_no), 'Name': name}, {'$set': {'Status': 'notpaid'}})
            flash('Room status updated to Paid', 'success')  # Optional: Flash message for update
     return redirect(url_for('adminrent'))
"""
GOING TO WORK ON ADMIN EXPENSE


"""
@app.route("/adminexpense",endpoint="admin_expense")
@login_requires
def admin_expense():
    name=db.admin.find()
    admin_names=[]
    for i in name:
        admin_names.append(i['Name'])
    datas=db.expense.find()
    return render_template("adminexpense.html",datas=datas,names=admin_names)
@app.route("/update_expense", methods=['POST'])
@login_requires
def expense():
    if request.method == 'POST':
       date=request.form['date']
       item=request.form['item']
       amount=request.form['amount']
       paidby=request.form['selected_name']
       paidby=paidby[0].upper()
       comments=request.form['comments']
       db.expense.insert_one({"Date":date,"Item":item,"Amount":int(amount),"By":paidby,"Comments":comments})
    return redirect(url_for("admin_expense"))
"""
GOING TO WORK ON CUSTOMER DETAIL

"""
@app.route("/addinfo", methods=['POST'])
@login_requires
def addinfo():
    if request.method == 'POST':
        try:
            roomno = int(request.form['roomno'])
            name = request.form['name']
            rentamount = int(request.form['rentamount'])
            doj = request.form['doj']

            # Insert into 'people' collection
            db.people.insert_one({"room_no": roomno, "Name": name, "Rent": rentamount, "Date": doj})

            # Insert into 'rent' collection
            db.rent.insert_one({"RoomNo": roomno, "Name": name, "Rent": rentamount, "Status": "notpaid", "By": ""})
            db.rooms.update_one({"RoomNo": roomno}, {"$inc": {"Filled": 1}})
            return redirect(url_for("superadminlogin"))  # Redirect to success page or another route
        except Exception as e:
            return jsonify({"error": str(e)})  # Handle errors gracefully
    else:
        return jsonify({"error": "Method not allowed"}), 405
if __name__=="__main__":
    app.run(debug=True)