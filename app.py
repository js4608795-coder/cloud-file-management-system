from flask import Flask, render_template_string, request, redirect, url_for, session, flash, send_file
import MySQLdb
import os
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'cloud-project-secret-key'
app.config['UPLOAD_FOLDER'] = '/var/www/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def get_db():
    return MySQLdb.connect(host='localhost', user='root', passwd='', db='student_files')

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Cloud File Management</title>
    <style>
        body { font-family: Arial; background: linear-gradient(135deg, #1e3c72, #2a5298); margin: 0; padding: 20px; }
        .container { max-width: 1000px; margin: 50px auto; background: white; padding: 30px; border-radius: 10px; }
        h1 { color: #2a5298; text-align: center; }
        input, button { width: 100%; padding: 10px; margin: 10px 0; }
        button { background: #2a5298; color: white; border: none; cursor: pointer; }
        .flash { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .success { background: #d4edda; color: #155724; }
        .danger { background: #f8d7da; color: #721c24; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; border-bottom: 1px solid #ddd; text-align: left; }
        th { background: #2a5298; color: white; }
        .btn { padding: 5px 10px; margin: 2px; text-decoration: none; border-radius: 3px; }
        .btn-download { background: #28a745; color: white; }
        .btn-delete { background: #dc3545; color: white; }
        .logout { background: #dc3545; padding: 10px 20px; color: white; text-decoration: none; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }
        .stat-card { background: #f8f9fa; padding: 20px; text-align: center; border-radius: 10px; }
        .stat-number { font-size: 32px; font-weight: bold; color: #2a5298; }
    </style>
</head>
<body>
<div class="container">
    {% if not session.user_id %}
        <h1>☁️ Cloud File Management System</h1>
        <h2>Login</h2>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% for category, message in messages %}
                <div class="flash {{ category }}">{{ message }}</div>
            {% endfor %}
        {% endwith %}
        <form method="POST">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
        <p><strong>Demo:</strong> student1 / pass123</p>
    {% else %}
        <div class="header">
            <h2>Welcome, {{ session.username }}!</h2>
            <a href="/logout" class="logout">Logout</a>
        </div>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% for category, message in messages %}
                <div class="flash {{ category }}">{{ message }}</div>
            {% endfor %}
        {% endwith %}
        <div class="stats">
            <div class="stat-card"><div class="stat-number">{{ total_files }}</div><div>Total Files</div></div>
            <div class="stat-card"><div class="stat-number">{{ total_size }}</div><div>Storage Used</div></div>
            <div class="stat-card"><div class="stat-number">{{ file_types }}</div><div>File Types</div></div>
        </div>
        <div style="background:#f8f9fa;padding:20px;border-radius:10px;">
            <h3>Upload File</h3>
            <form method="POST" action="/upload" enctype="multipart/form-data">
                <input type="file" name="file" required>
                <button type="submit">Upload</button>
            </form>
        </div>
        <h3>My Files</h3>
        <table>
            <thead><tr><th>Filename</th><th>Size</th><th>Date</th><th>Actions</th></tr></thead>
            <tbody>
                {% for file in files %}
                <tr>
                    <td>{{ file[1] }}</td><td>{{ file[2] }}</td><td>{{ file[3] }}</td>
                    <td><a href="/download/{{ file[0] }}" class="btn btn-download">Download</a>
                        <a href="/delete/{{ file[0] }}" class="btn btn-delete" onclick="return confirm('Delete?')">Delete</a>
                    </td>
                </tr>
                {% else %}
                <tr><td colspan="4">No files yet</td></tr>
                {% endfor %}
            </tbody>
        </table>
    {% endif %}
</div>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def home():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']
        db = get_db()
        c = db.cursor()
        c.execute("SELECT id, username FROM users WHERE username=%s AND password=%s", (u, p))
        user = c.fetchone()
        c.close()
        db.close()
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials!', 'danger')
    return render_template_string(HTML)

@app.route('/dashboard')
def dashboard():
    if not session.get('user_id'):
        return redirect(url_for('home'))
    db = get_db()
    c = db.cursor()
    c.execute("SELECT id, original_filename, file_size, DATE_FORMAT(uploaded_at, '%%Y-%%m-%%d %%H:%%i') FROM files WHERE user_id=%s", (session['user_id'],))
    files = c.fetchall()
    c.close()
    db.close()
    total = len(files)
    size_sum = sum(f[2] for f in files)
    if size_sum < 1024: size_str = f"{size_sum} B"
    elif size_sum < 1048576: size_str = f"{size_sum/1024:.1f} KB"
    else: size_str = f"{size_sum/1048576:.1f} MB"
    types = len(set(f[3] for f in files))
    return render_template_string(HTML, files=files, total_files=total, total_size=size_str, file_types=types)

@app.route('/upload', methods=['POST'])
def upload_file():
    if not session.get('user_id'):
        return redirect(url_for('home'))
    if 'file' not in request.files:
        flash('No file', 'danger')
        return redirect(url_for('dashboard'))
    file = request.files['file']
    if file.filename == '':
        flash('No file', 'danger')
        return redirect(url_for('dashboard'))
    name = file.filename
    ext = name.rsplit('.', 1)[1].lower() if '.' in name else ''
    if ext not in {'txt','pdf','png','jpg','jpeg','doc','docx'}:
        flash('Type not allowed', 'danger')
        return redirect(url_for('dashboard'))
    fname = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secure_filename(name)}"
    path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
    file.save(path)
    db = get_db()
    c = db.cursor()
    c.execute("INSERT INTO files (user_id, filename, original_filename, filepath, file_size) VALUES (%s,%s,%s,%s,%s)",
              (session['user_id'], fname, name, path, os.path.getsize(path)))
    db.commit()
    c.close()
    db.close()
    flash('Uploaded!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/download/<int:fid>')
def download_file(fid):
    if not session.get('user_id'):
        return redirect(url_for('home'))
    db = get_db()
    c = db.cursor()
    c.execute("SELECT filepath, original_filename FROM files WHERE id=%s AND user_id=%s", (fid, session['user_id']))
    f = c.fetchone()
    c.close()
    db.close()
    if f:
        return send_file(f[0], as_attachment=True, download_name=f[1])
    flash('Not found', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/delete/<int:fid>')
def delete_file(fid):
    if not session.get('user_id'):
        return redirect(url_for('home'))
    db = get_db()
    c = db.cursor()
    c.execute("SELECT filepath FROM files WHERE id=%s AND user_id=%s", (fid, session['user_id']))
    f = c.fetchone()
    if f and os.path.exists(f[0]):
        os.remove(f[0])
    c.execute("DELETE FROM files WHERE id=%s", (fid,))
    db.commit()
    c.close()
    db.close()
    flash('Deleted!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out!', 'success')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
