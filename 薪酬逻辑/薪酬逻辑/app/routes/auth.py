from flask import Blueprint, render_template,request, redirect, url_for, session
from app.db import get_db_connection

auth = Blueprint('auth', __name__)

@auth.route('/')
@auth.route('/login_identity')
def login_identity():
    return render_template('login_identity.html')

@auth.route('/login/member',methods=['GET', 'POST'])
def login_member():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM 成员 WHERE 姓名 = ? AND right(学号,6) = ?", (username, password))
        result = cursor.fetchone()
        conn.close()

        if result:
            session['user'] = username
            session['role'] = 'member'
            return redirect(url_for('member.member_dashboard'))
        else:
            error = "用户名或密码错误"

    return render_template('member/login.html', error=error)

# 固定的管理员账号密码
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = '123456'

@auth.route('/login/admin', methods=['GET', 'POST'])
def login_admin():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['user'] = username
            session['role'] = 'admin'
            return redirect(url_for('admin.admin_dashboard'))
        else:
            error = "用户名或密码错误"

    return render_template('admin/login.html', error=error)

'''
@auth.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('auth.login_admin'))
    return "<h1>欢迎，管理员！</h1>"

@auth.route('/member/dashboard')
def member_dashboard():
    if session.get('role') != 'member':
        return redirect(url_for('auth.login_member'))
    return "<h1>欢迎，团员！</h1>"

'''