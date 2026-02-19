from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import json
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///research_group.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/photos'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['INSTANCE_DATA_PATH'] = os.path.join(app.instance_path, 'data')
db = SQLAlchemy(app)


# 数据库模型
class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100))
    research_area = db.Column(db.String(200))
    bio = db.Column(db.Text)
    photo_url = db.Column(db.String(200))


class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    resource_type = db.Column(db.String(50), nullable=False)
    file_url = db.Column(db.String(200))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.Column(db.String(100))


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100), nullable=False)
    post_date = db.Column(db.DateTime, default=datetime.utcnow)
    category = db.Column(db.String(50))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def export_members_to_json():
    """将 Member 表所有记录导出为 JSON 文件"""
    members = Member.query.all()
    data = []
    for m in members:
        photo = m.photo_url
        # 如果 photo 存在且尚未包含 static/ 前缀，则添加
        if photo and not photo.startswith('static/'):
            photo = 'static/' + photo
        data.append({
            'id': m.id,
            'name': m.name,
            'role': m.role,
            'email': m.email,
            'research_area': m.research_area,
            'bio': m.bio,
            'photo_url': photo
        })
    file_path = os.path.join(app.config['INSTANCE_DATA_PATH'], 'members.json')
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def export_resources_to_json():
    """将 Resource 表所有记录导出为 JSON 文件"""
    resources = Resource.query.all()
    data = []
    for r in resources:
        data.append({
            'id': r.id,
            'title': r.title,
            'description': r.description,
            'resource_type': r.resource_type,
            'file_url': r.file_url,
            'author': r.author,
            'upload_date': r.upload_date.strftime('%Y-%m-%d') if r.upload_date else None
        })
    file_path = os.path.join(app.config['INSTANCE_DATA_PATH'], 'resources.json')
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def export_posts_to_json():
    """将 Post 表所有记录导出为 JSON 文件"""
    posts = Post.query.all()
    data = []
    for p in posts:
        data.append({
            'id': p.id,
            'title': p.title,
            'content': p.content,
            'author': p.author,
            'post_date': p.post_date.strftime('%Y-%m-%d') if p.post_date else None,
            'category': p.category
        })
    file_path = os.path.join(app.config['INSTANCE_DATA_PATH'], 'posts.json')
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# 路由
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/about')
def about():
    members = Member.query.all()
    return render_template('about.html', members=members)


@app.route('/resources')
def resources():
    resources = Resource.query.all()
    return render_template('resources.html', resources=resources)


@app.route('/forum')
def forum():
    posts = Post.query.order_by(Post.post_date.desc()).all()
    return render_template('forum.html', posts=posts)


@app.route('/contact')
def contact():
    return render_template('contact.html')


# 初始化数据库
with app.app_context():

    # 存放头像路径
    if not os.path.exists('static/photos'):
        os.makedirs('static/photos')

    # 创建 instance/data 目录（如果不存在）
    if not os.path.exists(app.config['INSTANCE_DATA_PATH']):
        os.makedirs(app.config['INSTANCE_DATA_PATH'])

    db.create_all()
    # 添加一些示例数据
    if not Member.query.first():
        # 添加导师信息
        advisor = Member(
            name="张三教授",
            role="课题组负责人",
            email="zhangsan@university.edu",
            research_area="人工智能、机器学习、计算机视觉",
            bio="张三教授是我校计算机科学与技术学院教授，博士生导师，主要从事人工智能和机器学习领域的研究。他在国际顶级期刊和会议上发表论文100余篇，主持国家级科研项目多项。",
            photo_url="photos/zhangsan_0219.jpg"
        )
        db.session.add(advisor)

        # 添加学生信息
        student1 = Member(
            name="李四",
            role="博士生",
            email="lisi@university.edu",
            research_area="自然语言处理",
            bio="李四是我校计算机科学与技术学院2022级博士生，主要研究方向为自然语言处理和对话系统。",
            photo_url="photos/lisi_0219.jpg"
        )
        db.session.add(student1)

        db.session.commit()

    if not Resource.query.first():
        # 添加示例资源
        resource1 = Resource(
            title="Python编程入门",
            description="这是一个Python编程入门教程，适合零基础的学生学习。",
            resource_type="教程",
            file_url="https://www.python.org/doc/",
            author="张三教授",
            upload_date=datetime.utcnow()
        )
        db.session.add(resource1)

        resource2 = Resource(
            title="机器学习实战",
            description="这是一本关于机器学习的实战书籍，包含大量的代码示例和项目实践。",
            resource_type="书籍",
            file_url="https://www.manning.com/books/machine-learning-in-action",
            author="李四",
            upload_date=datetime.utcnow()
        )
        db.session.add(resource2)

        db.session.commit()

    if not Post.query.first():
        # 添加示例帖子
        post1 = Post(
            title="欢迎新同学加入课题组",
            content="欢迎各位新同学加入我们的课题组！希望大家在这里能够学有所成，共同进步。",
            author="张三教授",
            category="通知",
            post_date=datetime.utcnow()
        )
        db.session.add(post1)

        post2 = Post(
            title="如何高效阅读科研论文",
            content="阅读科研论文是科研工作的重要环节，以下是一些高效阅读论文的方法：\n1. 先读摘要和结论，了解论文的主要内容\n2. 快速浏览图表，理解论文的核心结果\n3. 仔细阅读方法部分，了解实验设计\n4. 最后讨论部分，理解作者的观点和贡献",
            author="李四",
            category="经验分享",
            post_date=datetime.utcnow()
        )
        db.session.add(post2)

        db.session.commit()

    # 初始导出 JSON 文件
    export_members_to_json()
    export_resources_to_json()
    export_posts_to_json()

# ---------------------- admin ---------------------------
# 登录装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('请先登录', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# 登录路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # 简单硬编码验证，生产环境建议使用数据库
        if username == 'admin' and password == 'admin123':
            session['logged_in'] = True
            session['username'] = username
            flash('登录成功', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('admin_dashboard'))
        else:
            flash('用户名或密码错误', 'danger')
    return render_template('login.html')

# 登出
@app.route('/logout')
def logout():
    session.clear()
    flash('已退出登录', 'info')
    return redirect(url_for('index'))

# 管理仪表板
@app.route('/admin')
@login_required
def admin_dashboard():
    member_count = Member.query.count()
    resource_count = Resource.query.count()
    post_count = Post.query.count()
    return render_template('admin/dashboard.html',
                           member_count=member_count,
                           resource_count=resource_count,
                           post_count=post_count)

# ----- 成员管理 -----
@app.route('/admin/members')
@login_required
def admin_members():
    members = Member.query.all()
    return render_template('admin/members.html', members=members)


@app.route('/admin/members/add', methods=['GET', 'POST'])
@login_required
def admin_member_add():
    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        email = request.form['email']
        research_area = request.form['research_area']
        bio = request.form['bio']

        # 处理文件上传
        photo = request.files.get('photo')
        photo_url = ''
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            # 添加时间戳避免重名
            import time
            filename = f"{int(time.time())}_{filename}"
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            photo_url = f"photos/{filename}"
        else:
            # 如果没有上传，则使用手动输入的路径
            photo_url = request.form.get('photo_url', '')

        member = Member(name=name, role=role, email=email,
                        research_area=research_area, bio=bio, photo_url=photo_url)
        db.session.add(member)
        db.session.commit()
        export_members_to_json()
        flash('成员添加成功', 'success')
        return redirect(url_for('admin_members'))
    return render_template('admin/member_form.html')


@app.route('/admin/members/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_member_edit(id):
    member = Member.query.get_or_404(id)
    if request.method == 'POST':
        member.name = request.form['name']
        member.role = request.form['role']
        member.email = request.form['email']
        member.research_area = request.form['research_area']
        member.bio = request.form['bio']

        # 处理文件上传
        photo = request.files.get('photo')
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            import time
            filename = f"{int(time.time())}_{filename}"
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            member.photo_url = f"photos/{filename}"
        else:
            # 未上传新图片时，允许手动修改路径（兼容旧数据）
            member.photo_url = request.form.get('photo_url', member.photo_url)

        db.session.commit()
        export_members_to_json()
        flash('成员信息已更新', 'success')
        return redirect(url_for('admin_members'))
    return render_template('admin/member_form.html', member=member)

@app.route('/admin/members/delete/<int:id>')
@login_required
def admin_member_delete(id):
    member = Member.query.get_or_404(id)
    if member.photo_url:
        filepath = os.path.join('static', member.photo_url)
        if os.path.exists(filepath):
            os.remove(filepath)
    db.session.delete(member)
    db.session.commit()
    export_members_to_json()
    flash('成员已删除', 'success')
    return redirect(url_for('admin_members'))

# ----- 资源管理 -----
@app.route('/admin/resources')
@login_required
def admin_resources():
    resources = Resource.query.all()
    return render_template('admin/resources.html', resources=resources)

@app.route('/admin/resources/add', methods=['GET', 'POST'])
@login_required
def admin_resource_add():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        resource_type = request.form['resource_type']
        file_url = request.form['file_url']
        author = request.form['author']
        resource = Resource(title=title, description=description,
                            resource_type=resource_type, file_url=file_url,
                            author=author)
        db.session.add(resource)
        db.session.commit()
        export_resources_to_json()
        flash('资源添加成功', 'success')
        return redirect(url_for('admin_resources'))
    return render_template('admin/resource_form.html')

@app.route('/admin/resources/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_resource_edit(id):
    resource = Resource.query.get_or_404(id)
    if request.method == 'POST':
        resource.title = request.form['title']
        resource.description = request.form['description']
        resource.resource_type = request.form['resource_type']
        resource.file_url = request.form['file_url']
        resource.author = request.form['author']
        db.session.commit()
        export_resources_to_json()
        flash('资源已更新', 'success')
        return redirect(url_for('admin_resources'))
    return render_template('admin/resource_form.html', resource=resource)

@app.route('/admin/resources/delete/<int:id>')
@login_required
def admin_resource_delete(id):
    resource = Resource.query.get_or_404(id)
    db.session.delete(resource)
    db.session.commit()
    export_resources_to_json()
    flash('资源已删除', 'success')
    return redirect(url_for('admin_resources'))

# ----- 帖子管理 -----
@app.route('/admin/posts')
@login_required
def admin_posts():
    posts = Post.query.all()
    return render_template('admin/posts.html', posts=posts)

@app.route('/admin/posts/add', methods=['GET', 'POST'])
@login_required
def admin_post_add():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        author = request.form['author']
        category = request.form['category']
        post = Post(title=title, content=content, author=author, category=category)
        db.session.add(post)
        db.session.commit()
        export_posts_to_json()
        flash('帖子添加成功', 'success')
        return redirect(url_for('admin_posts'))
    return render_template('admin/post_form.html')

@app.route('/admin/posts/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_post_edit(id):
    post = Post.query.get_or_404(id)
    if request.method == 'POST':
        post.title = request.form['title']
        post.content = request.form['content']
        post.author = request.form['author']
        post.category = request.form['category']
        db.session.commit()
        export_posts_to_json()
        flash('帖子已更新', 'success')
        return redirect(url_for('admin_posts'))
    return render_template('admin/post_form.html', post=post)

@app.route('/admin/posts/delete/<int:id>')
@login_required
def admin_post_delete(id):
    post = Post.query.get_or_404(id)
    db.session.delete(post)
    db.session.commit()
    export_posts_to_json()
    flash('帖子已删除', 'success')
    return redirect(url_for('admin_posts'))

if __name__ == '__main__':
    app.run(debug=True)