from flask import Flask, render_template, request, jsonify
import sqlite3
import json
from datetime import datetime

app = Flask(__name__)
DB_PATH = 'database/quiz.db'

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS questions
                      (id INTEGER PRIMARY KEY,
                      content TEXT NOT NULL,
                      options TEXT NOT NULL,
                      correct TEXT NOT NULL,
                      type TEXT NOT NULL,
                      difficulty TEXT NOT NULL)''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS user_data
                      (id INTEGER PRIMARY KEY,
                      user_id TEXT NOT NULL,
                      question_id INTEGER,
                      answer TEXT,
                      timestamp TEXT,
                      FOREIGN KEY(question_id) REFERENCES questions(id))''')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/questions', methods=['POST'])
def add_question():
    data = request.get_json()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''INSERT INTO questions 
                      (content, options, correct, type, difficulty)
                      VALUES (?, ?, ?, ?, ?)''',
                    (data['content'], 
                     json.dumps(data['options']), 
                     data['correct'], 
                     data['type'], 
                     data['difficulty']))
        conn.commit()
    return jsonify({"status": "success"})

@app.route('/api/questions/random/<int:count>')
def get_random_questions(count=10):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute('''SELECT * FROM questions
                            ORDER BY RANDOM()
                            LIMIT ?''', (count,))
        questions = []
        for row in cursor.fetchall():
            questions.append({
                'id': row[0],
                'content': row[1],
                'options': json.loads(row[2]),
                'correct': row[3],
                'type': row[4],
                'difficulty': row[5]
            })
    return jsonify(questions)

@app.route('/api/answers', methods=['POST'])
def save_answer():
    data = request.get_json()
    timestamp = datetime.now().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''INSERT INTO user_data
                      (user_id, question_id, answer, timestamp)
                      VALUES (?, ?, ?, ?)''',
                    (data['user_id'], 
                     data['question_id'], 
                     json.dumps(data['answer']), 
                     timestamp))
        conn.commit()
    return jsonify({"status": "success"})

@app.route('/api/backup')
def backup_database():
    backup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    with sqlite3.connect(DB_PATH) as conn:
        with open(f'backup_{backup_time}.db', 'wb') as f:
            for line in conn.iterdump():
                f.write(f"{line}\n".encode())
    return jsonify({"status": "backup created"})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
