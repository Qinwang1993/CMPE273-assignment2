from flask import Flask, request, redirect, url_for
from werkzeug.utils import secure_filename
import sqlite3
import json
import os


UPLOAD_FOLDER = '/Users/Ray/Desktop/SJSU/2020Spring/273/Lab2/uploads'
ALLOWED_EXTENSIONS = {'json'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate(obj):
    subject = obj["subject"]
    answers = obj["answers"]
    conn = sqlite3.connect("test.db")
    c = conn.cursor()
    query = "SELECT * FROM " + subject
    c.execute(query)
    values = c.fetchall()
    score = 0
    result = {}
    for row in values:
        question_id = row[0]
        submitted_answer = answers[str(question_id)]
        correct_answer = row[1]
        tmp = {}
        tmp["actual"] = submitted_answer
        tmp["expected"] = correct_answer
        result[row[0]] = tmp
        if submitted_answer == correct_answer:
            score = score + 1

    obj["result"] = result
    obj["score"] = score
    conn.commit()
    conn.close()
    return obj

def storeScantron(data, path):
    conn = sqlite3.connect("test.db")
    sql = "CREATE TABLE IF NOT EXISTS scantron (id INTEGER PRIMARY KEY AUTOINCREMENT, scantron_url VARCHAR(100), \
        name VARCHAR(50), subject VARCHAR(50), answers VARCHAR(10000))"
    c = conn.cursor()
    c.execute(sql)

    sql = "INSERT INTO scantron (scantron_url, name, subject, answers) VALUES (?, ?, ?, ?)"
    c.execute(sql, (path, data["name"], data["subject"], json.dumps(data["answers"])))

    query = "SELECT id FROM scantron WHERE name = ? AND subject = ? AND scantron_url = ?"
    c.execute(query, (data["name"], data["subject"], path, ))
    values = c.fetchall()
    data["scantron_id"] = values[0][0]
    data["scantron_url"] = path
    output = calculate(data)
    conn.commit()
    conn.close()
    del output["answers"]
    return output


@app.route('/')
def hello():
    return "Hello World"

# Create a test
@app.route('/api/tests', methods = ['POST'])
def addTest():
    content = request.get_json()
    subject = content["subject"]
    answers = content["answer_keys"]

    conn = sqlite3.connect("test.db")
    sql = "CREATE TABLE IF NOT EXISTS " + subject +  " (q_id INTEGER PRIMARY KEY, answer VARCHAR(1))"
    c = conn.cursor()
    c.execute(sql)

    for key in answers:
        value = answers[key]
        sql = "INSERT INTO " + subject + " (q_id, answer) VALUES (" + key + ", '" + value + "')"
        c.execute(sql)

    sql = "CREATE TABLE IF NOT EXISTS test_id (id INTEGER PRIMARY KEY AUTOINCREMENT, name VARCHAR(50))"
    c.execute(sql)

    sql = "INSERT INTO test_id (name) VALUES ('" + subject + "')"
    c.execute(sql)

    query = "SELECT * FROM test_id WHERE name = '" + subject + "'"
    c.execute(query)
    values = c.fetchall()
    output = {}
    output["test_id"] = values[0][0]
    output["subject"] = subject
    output["answers_keys"] = answers
    output["submissions"] = []
    conn.commit()
    conn.close()
    return output, 201

# Upload a scantron
@app.route('/api/tests/<test_id>/scantrons', methods = ['POST'])
def uploadScantron(test_id):
    if 'data' not in request.files:
        print ('No file part')
        return redirect(request.url)
    file = request.files['data']
    # if user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        print('No selected file')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        with open(os.path.join(app.config['UPLOAD_FOLDER'], filename)) as json_file:
            data = json.load(json_file)
            path = "http://localhost:5000/uploads/" + filename
            return storeScantron(data, path), 201
    return "error", 400


# Check all scantron submissions
@app.route('/api/tests/<test_id>', methods = ['GET'])
def checkAll(test_id):
    conn = sqlite3.connect("test.db")
    c = conn.cursor()
    query = "SELECT * FROM test_id WHERE id = " + test_id
    c.execute(query)
    values = c.fetchall()
    subject = values[0][1]
    output = {}
    output["test_id"] = test_id
    output["subject"] = subject

    answer_keys = {}
    query = "SELECT * FROM " + subject
    c.execute(query)
    values = c.fetchall()
    for row in values:
        answer_keys[row[0]] = row[1]
    output["answer_keys"] = answer_keys
    
    submissions = []
    query = "SELECT * FROM scantron WHERE subject = '" + subject + "'"
    c.execute(query)
    values = c.fetchall()
    for row in values:
        obj = {}
        obj["scantron_id"] = row[0]
        obj["scantron_url"] = row[1]
        obj["name"] = row[2]
        obj["subject"] = row[3]
        obj["answers"] = json.loads(row[4])
        s = calculate(obj)
        del s["answers"]
        submissions.append(s)

    output["submissions"] = submissions
    return output, 200