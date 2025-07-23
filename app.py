from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import json
from datetime import datetime
import os
import logging

app = Flask(__name__, static_folder='static')
DB_PATH = 'database/quiz.db'
BACKUP_DIR = 'backups'

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    try:
        db_dir = os.path.dirname(DB_PATH)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        
        with sqlite3.connect(DB_PATH) as conn:
            # 创建章节表
            conn.execute('''CREATE TABLE IF NOT EXISTS chapters
                        (id INTEGER PRIMARY KEY,
                        title TEXT NOT NULL UNIQUE,
                        description TEXT,
                        created_at TEXT)''')
            
            # 创建问题表（增加chapter_id字段）
            conn.execute('''CREATE TABLE IF NOT EXISTS questions
                        (id INTEGER PRIMARY KEY,
                        chapter_id INTEGER,
                        content TEXT NOT NULL,
                        options TEXT NOT NULL,
                        correct TEXT NOT NULL,
                        explanation TEXT,
                        type TEXT NOT NULL,
                        difficulty TEXT NOT NULL,
                        FOREIGN KEY(chapter_id) REFERENCES chapters(id))''')
            # 检查questions表是否有chapter_id列
            cursor = conn.execute("PRAGMA table_info(questions)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'chapter_id' not in columns:
                logger.info("添加缺失的chapter_id列到questions表")
                conn.execute("ALTER TABLE questions ADD COLUMN chapter_id INTEGER")
                conn.commit()
            # 创建用户数据表
            conn.execute('''CREATE TABLE IF NOT EXISTS user_data
                        (id INTEGER PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        question_id INTEGER,
                        answer TEXT,
                        is_correct INTEGER,
                        timestamp TEXT,
                        FOREIGN KEY(question_id) REFERENCES questions(id))''')
            
            # 检查是否有章节
            cursor = conn.execute("SELECT COUNT(*) FROM chapters")
            chapter_count = cursor.fetchone()[0]
            
            if chapter_count == 0:
                logger.info("添加示例章节到数据库")
                sample_chapters = [
                    ("第1章: Python基础", "Python基础语法和数据类型"),
                    ("第2章: 函数与模块", "函数定义、参数传递和模块使用"),
                    ("第3章: 面向对象编程", "类、对象和面向对象特性")
                ]
                
                for title, desc in sample_chapters:
                    conn.execute('''INSERT OR IGNORE INTO chapters 
                                (title, description, created_at)
                                VALUES (?, ?, ?)''',
                                (title, desc, datetime.now().isoformat()))
                
                conn.commit()
            
            # 检查是否有题目
            cursor = conn.execute("SELECT COUNT(*) FROM questions")
            question_count = cursor.fetchone()[0]
            
            if question_count == 0:
                logger.info("添加示例题目到数据库")
                # 获取章节ID
                chapters = conn.execute("SELECT id, title FROM chapters").fetchall()
                chapter_map = {title: id for id, title in chapters}
                
                sample_questions = [
                    {
                        "chapter": "第1章: Python基础",
                        "content": "Python 中用于输出内容的函数是？",
                        "options": ["print", "echo", "output", "log"],
                        "correct": "0",
                        "explanation": "在Python中，print()函数用于将内容输出到标准输出设备（通常是屏幕）。其他选项不是Python的内置函数。",
                        "type": "single",
                        "difficulty": "easy"
                    },
                    {
                        "chapter": "第1章: Python基础",
                        "content": "以下属于 Python 基本数据类型的是？",
                        "options": ["list", "int", "dict", "tuple"],
                        "correct": "1",
                        "explanation": "Python的基本数据类型包括：整型(int)、浮点型(float)、布尔型(bool)和字符串(str)。列表(list)、字典(dict)和元组(tuple)是复合数据类型，不属于基本数据类型。",
                        "type": "single",
                        "difficulty": "medium"
                    },
                    {
                        "chapter": "第1章: Python基础",
                        "content": "下列哪个选项可以创建一个包含数字1到5的列表？",
                        "options": ["list(range(1,6))", "list(range(1,5))", "[1,2,3,4,5]", "[1:6]"],
                        "correct": "0,2",
                        "explanation": "list(range(1,6))会生成[1,2,3,4,5]，因为range(1,6)包含1但不包含6。直接写[1,2,3,4,5]也是正确的。",
                        "type": "multiple",
                        "difficulty": "easy"
                    },
                    {
                        "chapter": "第2章: 函数与模块",
                        "content": "下列哪个关键字用于定义函数？",
                        "options": ["func", "def", "function", "define"],
                        "correct": "1",
                        "explanation": "在Python中，使用def关键字来定义函数。",
                        "type": "single",
                        "difficulty": "easy"
                    }
                ]
                
                for q in sample_questions:
                    chapter_id = chapter_map.get(q['chapter'])
                    if chapter_id:
                        conn.execute('''INSERT OR IGNORE INTO questions 
                                    (chapter_id, content, options, correct, explanation, type, difficulty)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                                    (chapter_id,
                                     q['content'], 
                                     json.dumps(q['options']), 
                                     q['correct'], 
                                     q['explanation'],
                                     q['type'], 
                                     q['difficulty']))
                conn.commit()
    except Exception as e:
        logger.error(f"初始化数据库失败: {str(e)}")
        raise

# 添加CORS头处理
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response

@app.route('/')
def serve_frontend():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/chapters', methods=['GET'])
def get_chapters():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute('''SELECT * FROM chapters''')
            chapters = []
            for row in cursor.fetchall():
                chapters.append({
                    'id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'created_at': row[3]
                })
        return jsonify({"status": "success", "data": chapters})
    except Exception as e:
        logger.error(f"获取章节失败: {str(e)}")
        return jsonify({"status": "error", "message": "服务器内部错误"}), 500

@app.route('/api/chapters', methods=['POST'])
def add_chapter():
    try:
        data = request.get_json()
        
        # 基本数据验证
        required_fields = ['title']
        if not all(field in data for field in required_fields):
            return jsonify({"status": "error", "message": "缺少必要字段"}), 400
        
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('''INSERT OR IGNORE INTO chapters 
                        (title, description, created_at)
                        VALUES (?, ?, ?)''',
                        (data['title'], 
                         data.get('description', ''),
                         datetime.now().isoformat()))
            conn.commit()
        return jsonify({"status": "success", "message": "章节添加成功"})
    except sqlite3.IntegrityError:
        return jsonify({"status": "error", "message": "章节已存在"}), 400
    except Exception as e:
        logger.error(f"添加章节失败: {str(e)}")
        return jsonify({"status": "error", "message": "服务器内部错误"}), 500

@app.route('/api/questions', methods=['POST'])
def add_question():
    try:
        data = request.get_json()
        
        # 基本数据验证
        required_fields = ['chapter_id', 'content', 'options', 'correct', 'type', 'difficulty']
        if not all(field in data for field in required_fields):
            return jsonify({"status": "error", "message": "缺少必要字段"}), 400
        
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('''INSERT OR IGNORE INTO questions 
                        (chapter_id, content, options, correct, explanation, type, difficulty)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                        (data['chapter_id'],
                         data['content'], 
                         json.dumps(data['options']), 
                         data['correct'], 
                         data.get('explanation', ''),
                         data['type'], 
                         data['difficulty']))
            conn.commit()
        return jsonify({"status": "success", "message": "题目添加成功"})
    except sqlite3.IntegrityError:
        return jsonify({"status": "error", "message": "题目已存在"}), 400
    except Exception as e:
        logger.error(f"添加题目失败: {str(e)}")
        return jsonify({"status": "error", "message": "服务器内部错误"}), 500

@app.route('/api/questions/random/<int:count>')
def get_random_questions(count=10):
    try:
        if count <= 0 or count > 50:  # 限制最大数量
            count = 10
            
        chapter_id = request.args.get('chapter_id')
        
        with sqlite3.connect(DB_PATH) as conn:
            query = '''SELECT q.*, c.title as chapter_title 
                    FROM questions q
                    JOIN chapters c ON q.chapter_id = c.id'''
            
            params = ()
            if chapter_id:
                query += " WHERE q.chapter_id = ?"
                params = (chapter_id,)
            
            query += " ORDER BY RANDOM() LIMIT ?"
            params += (count,)
            
            cursor = conn.execute(query, params)
            questions = []
            for row in cursor.fetchall():
                questions.append({
                    'id': row[0],
                    'chapter_id': row[1],
                    'chapter_title': row[8],
                    'content': row[2],
                    'options': json.loads(row[3]),
                    'correct': row[4],
                    'explanation': row[5],
                    'type': row[6],
                    'difficulty': row[7]
                })
        return jsonify({"status": "success", "data": questions})
    except Exception as e:
        logger.error(f"获取随机题目失败: {str(e)}")
        return jsonify({"status": "error", "message": "服务器内部错误"}), 500

@app.route('/api/questions/chapter/<int:chapter_id>')
def get_chapter_questions(chapter_id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute('''SELECT q.*, c.title as chapter_title 
                                  FROM questions q
                                  JOIN chapters c ON q.chapter_id = c.id
                                  WHERE q.chapter_id = ?''', (chapter_id,))
            questions = []
            for row in cursor.fetchall():
                questions.append({
                    'id': row[0],
                    'chapter_id': row[1],
                    'chapter_title': row[8],
                    'content': row[2],
                    'options': json.loads(row[3]),
                    'correct': row[4],
                    'explanation': row[5],
                    'type': row[6],
                    'difficulty': row[7]
                })
        return jsonify({"status": "success", "data": questions})
    except Exception as e:
        logger.error(f"获取章节题目失败: {str(e)}")
        return jsonify({"status": "error", "message": "服务器内部错误"}), 500

@app.route('/api/answers', methods=['POST'])
def save_answer():
    try:
        data = request.get_json()
        required_fields = ['user_id', 'question_id', 'answer']
        if not all(field in data for field in required_fields):
            return jsonify({"status": "error", "message": "缺少必要字段"}), 400
        
        # 获取正确答案
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT correct FROM questions WHERE id = ?", (data['question_id'],))
            question = cursor.fetchone()
            if not question:
                return jsonify({"status": "error", "message": "题目不存在"}), 404
            
            correct_answer = question[0].split(',')
            user_answer = [str(a) for a in data['answer']]
            is_correct = sorted(correct_answer) == sorted(user_answer)
            
            timestamp = datetime.now().isoformat()
            conn.execute('''INSERT INTO user_data
                        (user_id, question_id, answer, is_correct, timestamp)
                        VALUES (?, ?, ?, ?, ?)''',
                        (data['user_id'], 
                         data['question_id'], 
                         json.dumps(data['answer']), 
                         1 if is_correct else 0,
                         timestamp))
            conn.commit()
            
            # 获取题目解析
            cursor = conn.execute("SELECT explanation, correct FROM questions WHERE id = ?", (data['question_id'],))
            explanation_data = cursor.fetchone()
            
        return jsonify({
            "status": "success", 
            "message": "答案保存成功",
            "is_correct": is_correct,
            "explanation": explanation_data[0] if explanation_data else "",
            "correct_answer": explanation_data[1] if explanation_data else ""
        })
    except Exception as e:
        logger.error(f"保存答案失败: {str(e)}")
        return jsonify({"status": "error", "message": "服务器内部错误"}), 500

@app.route('/api/stats')
def get_stats():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # 获取题目总数
            cursor = conn.execute("SELECT COUNT(*) FROM questions")
            total_questions = cursor.fetchone()[0]
            
            # 获取章节总数
            cursor = conn.execute("SELECT COUNT(*) FROM chapters")
            chapter_count = cursor.fetchone()[0]
            
            # 获取已答题数
            cursor = conn.execute("SELECT COUNT(DISTINCT question_id) FROM user_data")
            answered_questions = cursor.fetchone()[0]
            
            # 获取正确题数
            cursor = conn.execute("SELECT COUNT(*) FROM user_data WHERE is_correct = 1")
            correct_answers = cursor.fetchone()[0]
            
            # 计算正确率
            accuracy = round((correct_answers / answered_questions * 100), 2) if answered_questions > 0 else 0
            
        return jsonify({
            "status": "success",
            "data": {
                "total_questions": total_questions,
                "chapter_count": chapter_count,
                "answered_questions": answered_questions,
                "accuracy": accuracy
            }
        })
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        return jsonify({"status": "error", "message": "服务器内部错误"}), 500

@app.route('/api/backup')
def backup_database():
    try:
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
            
        backup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f'quiz_backup_{backup_time}.db'
        backup_path = os.path.join(BACKUP_DIR, backup_filename)
        
        with sqlite3.connect(DB_PATH) as conn:
            with open(backup_path, 'wb') as f:
                for line in conn.iterdump():
                    f.write(f"{line}\n".encode())
        
        return jsonify({
            "status": "success", 
            "message": "备份创建成功",
            "backup_path": backup_path
        })
    except Exception as e:
        logger.error(f"数据库备份失败: {str(e)}")
        return jsonify({"status": "error", "message": "备份失败"}), 500

# 新增题库导入API
@app.route('/api/questions/import', methods=['POST'])
def import_questions():
    try:
        data = request.get_json()
        if not data or 'questions' not in data:
            return jsonify({"status": "error", "message": "无效的请求数据"}), 400
        
        mapping_type = data.get('mapping_type', 'auto')
        existing_chapter_id = data.get('existing_chapter_id')
        questions = data['questions']
        
        if not isinstance(questions, list):
            return jsonify({"status": "error", "message": "题目数据应该是列表"}), 400
        
        results = {
            "imported_count": 0,
            "new_chapters": [],
            "errors": []
        }
        
        with sqlite3.connect(DB_PATH) as conn:
            # 章节映射
            chapter_map = {}
            
            # 如果是使用现有章节，验证章节是否存在
            if mapping_type == 'existing' and existing_chapter_id:
                cursor = conn.execute("SELECT id FROM chapters WHERE id = ?", (existing_chapter_id,))
                if not cursor.fetchone():
                    return jsonify({"status": "error", "message": "指定章节不存在"}), 400
            
            # 处理题目
            for idx, q in enumerate(questions):
                try:
                    # 验证题目数据
                    required_fields = ['content', 'options', 'correct', 'type', 'difficulty']
                    if not all(field in q for field in required_fields):
                        raise ValueError("缺少必要字段")
                    
                    # 处理章节
                    chapter_title = q.get('chapter', '未分类') or '未分类'  # 确保不为None
                    chapter_id = None
                    
                    # 使用现有章节模式
                    if mapping_type == 'existing' and existing_chapter_id:
                        chapter_id = existing_chapter_id
                    # 自动映射模式
                    else:
                        # 检查章节是否已存在
                        if chapter_title not in chapter_map:
                            cursor = conn.execute("SELECT id FROM chapters WHERE title = ?", (chapter_title,))
                            chapter = cursor.fetchone()
                            
                            if chapter:
                                chapter_id = chapter[0]
                                chapter_map[chapter_title] = chapter_id
                            else:
                                # 创建新章节
                                conn.execute('''INSERT INTO chapters 
                                            (title, description, created_at)
                                            VALUES (?, ?, ?)''',
                                            (chapter_title, 
                                             f"{chapter_title} 题库导入",
                                             datetime.now().isoformat()))
                                chapter_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                                chapter_map[chapter_title] = chapter_id
                                
                                # 记录新章节
                                results["new_chapters"].append({
                                    "id": chapter_id,
                                    "title": chapter_title
                                })
                        else:
                            chapter_id = chapter_map[chapter_title]
                    
                    # 添加题目
                    conn.execute('''INSERT OR IGNORE INTO questions 
                                (chapter_id, content, options, correct, explanation, type, difficulty)
                                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                                (chapter_id,
                                 q['content'], 
                                 json.dumps(q['options']), 
                                 q['correct'], 
                                 q.get('explanation', ''),
                                 q['type'], 
                                 q['difficulty']))
                    
                    results["imported_count"] += 1
                    
                except Exception as e:
                    # 记录错误
                    results["errors"].append({
                        "index": idx,
                        "question": q.get('content', '未知题目'),
                        "reason": str(e)
                    })
                    logger.error(f"导入题目失败: {str(e)}")
            
            conn.commit()
        
        return jsonify({"status": "success", "message": "题库导入完成", "data": results})
    
    except Exception as e:
        logger.error(f"题库导入失败: {str(e)}")
        return jsonify({"status": "error", "message": "服务器内部错误"}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"status": "error", "message": "资源未找到"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"status": "error", "message": "服务器内部错误"}), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
