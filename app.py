from flask import Flask, render_template, g, redirect, request
import sqlite3
import os
from flask_login import UserMixin, LoginManager, login_required, login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

DATABASE = "flaskmemo.db"

app = Flask(__name__)
app.secret_key = os.urandom(24)

login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, userid):
        self.id = userid

@login_manager.user_loader
def load_user(userid):
    return User(userid)

@login_manager.unauthorized_handler
def unauthorized():
    return redirect('/login')

@app.route("/logout", methods=['GET'])
def logout():
    logout_user()
    return redirect('/login')

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    error_message = ''
    userid = ''
    if request.method == 'POST':
        userid = request.form.get('userid')
        password = request.form.get('password')
        pass_hash = generate_password_hash(password)
        db = get_db()
        user_check = db.execute(
            "select userid from user where userid=?",
            [userid]
        ).fetchall()
        if not user_check:
            db.execute(
                "insert into user (userid, password) values(?, ?)",
                [userid, pass_hash]
            )
            db.commit()
            return redirect('/login')
        else:
            error_message = '入力されたユーザIDはすでに登録されています'
    return render_template('signup.html', error_message=error_message, userid=userid)

@app.route("/login", methods=['GET', 'POST'])
def login():
    error_message = ''
    userid = ''

    if request.method == 'POST':
        userid = request.form.get('userid')
        password = request.form.get('password')

        user_data = get_db().execute(
            "select password from user where userid=?",
            [userid]
        ).fetchone()

        if user_data is not None:
            if check_password_hash(user_data[0], password):
                user = User(userid)
                login_user(user)
                return redirect('/')

        error_message = '入力されたIDもしくはパスワードが誤っています'

    return render_template('login.html', userid=userid, error_message=error_message)

@app.route("/")
@login_required
def top():
    memo_list = get_db().execute(
        "select id, facility_type, facility_name, prefecture, visit_date, favorite_animal, memo, photo_path "
        "from memo where user_id=? order by id desc",
        [current_user.id]
    ).fetchall()
    return render_template('index.html', memo_list=memo_list)

@app.route("/prefecture_detail")
@login_required
def prefecture_detail():
    prefecture_name = request.args.get('name')

    memo_list = get_db().execute(
        """
        select id, facility_type, facility_name, prefecture, visit_date, favorite_animal, memo, photo_path
        from memo
        where user_id=? and prefecture=?
        order by id desc
        """,
        [current_user.id, prefecture_name]
    ).fetchall()

    return render_template('prefecture_detail.html', prefecture_name=prefecture_name, memo_list=memo_list)

@app.route("/prefecture")
@login_required
def prefecture():
    prefecture_list = get_db().execute(
        """
        select prefecture, count(*) as count
        from memo
        where user_id=?
        group by prefecture
        order by prefecture
        """,
        [current_user.id]
    ).fetchall()

    achieved_count = len(prefecture_list)
    achievement_rate = round((achieved_count / 47) * 100, 1) if achieved_count > 0 else 0

    return render_template(
        'prefecture.html',
        prefecture_list=prefecture_list,
        achieved_count=achieved_count,
        achievement_rate=achievement_rate
    )

@app.route("/regist", methods=['GET', 'POST'])
@login_required
def regist():
    if request.method == 'POST':
        facility_type = request.form.get('facility_type')
        facility_name = request.form.get('facility_name')
        prefecture = request.form.get('prefecture')
        visit_date = request.form.get('visit_date')
        favorite_animal = request.form.get('favorite_animal')
        memo = request.form.get('memo')
        photo = request.files.get('photo')
        photo_path = ''

        if photo and photo.filename != '':
            filename = secure_filename(photo.filename)
            upload_dir = os.path.join(app.root_path, 'static', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)

            unique_name = datetime.now().strftime("%Y%m%d%H%M%S_") + filename
            save_path = os.path.join(upload_dir, unique_name)
            photo.save(save_path)

            photo_path = '/static/uploads/' + unique_name

        db = get_db()
        db.execute(
            "insert into memo (user_id, facility_type, facility_name, prefecture, visit_date, favorite_animal, memo, photo_path) "
            "values (?, ?, ?, ?, ?, ?, ?, ?)",
            [current_user.id, facility_type, facility_name, prefecture, visit_date, favorite_animal, memo, photo_path]
        )
        db.commit()
        return redirect('/')

    return render_template('regist.html')

@app.route("/<int:id>/edit", methods=['GET', 'POST'])
@login_required
def edit(id):
    db = get_db()
    post = db.execute(
        "select id, facility_type, facility_name, prefecture, visit_date, favorite_animal, memo, photo_path "
        "from memo where id=? and user_id=?",
        [id, current_user.id]
    ).fetchone()

    if post is None:
        return redirect('/')

    if request.method == 'POST':
        facility_type = request.form.get('facility_type')
        facility_name = request.form.get('facility_name')
        prefecture = request.form.get('prefecture')
        visit_date = request.form.get('visit_date')
        favorite_animal = request.form.get('favorite_animal')
        memo = request.form.get('memo')
        photo = request.files.get('photo')
        photo_path = post['photo_path']

        if photo and photo.filename != '':
            filename = secure_filename(photo.filename)
            upload_dir = os.path.join(app.root_path, 'static', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)

            unique_name = datetime.now().strftime("%Y%m%d%H%M%S_") + filename
            save_path = os.path.join(upload_dir, unique_name)
            photo.save(save_path)

            photo_path = '/static/uploads/' + unique_name

        db.execute(
            "update memo set facility_type=?, facility_name=?, prefecture=?, visit_date=?, favorite_animal=?, memo=?, photo_path=? "
            "where id=? and user_id=?",
            [facility_type, facility_name, prefecture, visit_date, favorite_animal, memo, photo_path, id, current_user.id]
        )
        db.commit()
        return redirect('/')

    return render_template('edit.html', post=post)

@app.route("/<int:id>/delete", methods=['GET', 'POST'])
@login_required
def delete(id):
    db = get_db()
    post = db.execute(
        "select id, facility_type, facility_name, prefecture, visit_date, favorite_animal, memo "
        "from memo where id=? and user_id=?",
        [id, current_user.id]
    ).fetchone()

    if post is None:
        return redirect('/')

    if request.method == 'POST':
        db.execute(
            "delete from memo where id=? and user_id=?",
            [id, current_user.id]
        )
        db.commit()
        return redirect('/')

    return render_template('delete.html', post=post)

def connect_db():
    rv = sqlite3.connect(DATABASE)
    rv.row_factory = sqlite3.Row
    return rv

def get_db():
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

if __name__ == "__main__":
    app.run(debug=True)

