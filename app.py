from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
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
app.config['PUBLICATIONS_UPLOAD_FOLDER'] = os.path.join('static', 'publications')
app.config['ALLOWED_PUB_EXTENSIONS'] = {'pdf', 'doc', 'docx', 'zip', 'tar', 'gz', 'py', 'ipynb', 'txt'}
db = SQLAlchemy(app)


# 数据库模型
class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    university = db.Column(db.String(100))          # 新增
    email = db.Column(db.String(100))
    research_area = db.Column(db.String(200))
    bio = db.Column(db.Text)
    photo_url = db.Column(db.String(200))
    # 新增复杂字段
    stats = db.Column(db.JSON, default=[])
    publications = db.Column(db.JSON, default=[])
    projects = db.Column(db.JSON, default=[])
    news = db.Column(db.JSON, default=[])
    education = db.Column(db.JSON, default=[])
    experience = db.Column(db.JSON, default=[])


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

def allowed_pub_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_PUB_EXTENSIONS']

def parse_json_field(value, field_name):
    if value and value.strip():
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            flash(f'{field_name} 格式错误，请输入有效的 JSON', 'danger')
            return None
    return []   # 空字符串返回空列表

def export_members_to_json():
    """将 Member 表所有记录导出为 JSON 文件，头像路径统一添加 static/ 前缀，出版物文件路径同样处理"""
    members = Member.query.all()
    data = []
    for m in members:
        # 头像处理
        photo = m.photo_url
        if photo and not photo.startswith('static/'):
            photo = 'static/' + photo

        # 出版物处理：为 links.pdf 和 links.code 添加 static/ 前缀（如果存在且是本地路径）
        publications = m.publications or []
        for pub in publications:
            links = pub.get('links', {})
            for key in ['pdf', 'code']:
                if key in links and links[key]:
                    path = links[key]
                    # 如果不是以 http:// 或 https:// 开头，且尚未添加 static/，则添加
                    if not path or path == '#' :
                        links[key] = '#'
                    elif not (path.startswith('http://') or path.startswith('https://') or path.startswith('static/')):
                        links[key] = path
            # 更新回 pub（links 是可变对象，直接修改即可）

        # 构建成员字典
        member_dict = {
            'id': m.id,
            'name': m.name,
            'role': m.role,
            'university': m.university,
            'email': m.email,
            'research_area': m.research_area,
            'bio': m.bio,
            'photo_url': photo,
            'stats': m.stats or [],
            'publications': publications,
            'projects': m.projects or [],
            'news': m.news or [],
            'education': m.education or [],
            'experience': m.experience or [],
        }
        data.append(member_dict)

    # 写入文件
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

@app.route('/memberInfo')
def memberInfo():
    return render_template('memberInfo.html')


# 初始化数据库
with app.app_context():

    # 存放头像路径
    if not os.path.exists('static/photos'):
        os.makedirs('static/photos')

    # 创建 instance/data 目录（如果不存在）
    if not os.path.exists(app.config['INSTANCE_DATA_PATH']):
        os.makedirs(app.config['INSTANCE_DATA_PATH'])

    if not os.path.exists(app.config['PUBLICATIONS_UPLOAD_FOLDER']):
        os.makedirs(app.config['PUBLICATIONS_UPLOAD_FOLDER'])

    db.create_all()
    # 添加一些示例数据
    if not Member.query.first():
        # 添加导师信息（包含复杂字段）
        advisor = Member(
            name="张三教授",
            role="课题组负责人",
            university="计算机科学与技术学院",  # 新增
            email="zhangsan@university.edu",
            research_area="人工智能、机器学习、计算机视觉",
            bio="张三教授是我校计算机科学与技术学院教授，博士生导师，主要从事人工智能和机器学习领域的研究。他在国际顶级期刊和会议上发表论文100余篇，主持国家级科研项目多项。",
            photo_url="photos/zhangsan_0219.jpg",  # 去掉 static/ 前缀
            # 复杂字段
            stats=[
                {"value": "100+", "label": "出版物"},
                {"value": "2000+", "label": "引用"},
                {"value": "10+", "label": "项目"}
            ],
            publications=[
                {
                    "year": 2025,
                    "title": "高效深度神经网络压缩算法",
                    "authors": "张三教授, 李四, 王五",
                    "venue": "CVPR 2025",
                    "links": {"pdf": "中国移动：端侧算力网络白皮书2022年.pdf", "code": "#"},
                    "url": "#"
                },
                {
                    "year": 2024,
                    "title": "多模态对话系统中的知识融合",
                    "authors": "张三教授, 赵六",
                    "venue": "ACL 2024",
                    "links": {"pdf": "#"},
                    "url": "#"
                }
            ],
            projects=[
                {
                    "name": "轻量化视觉Transformer",
                    "desc": "面向移动端的实时视觉识别模型",
                    "tags": ["Python", "PyTorch", "Transformer"],
                    "url": "#"
                }
            ],
            news=[
                {"date": "2025.01", "badge": "New", "text": "课题组获得国家自然科学基金重点项目"},
                {"date": "2024.09", "badge": "Award", "text": "张三教授荣获CCF青年科学家奖"}
            ],
            education=[
                {"period": "2005–2010", "degree": "计算机科学博士", "institution": "清华大学"}
            ],
            experience=[
                {"period": "2010–至今", "role": "教授", "institution": "计算机科学与技术学院"}
            ]
        )
        db.session.add(advisor)

        # 添加学生信息（同样包含复杂字段，此处为空）
        student1 = Member(
            name="李四",
            role="博士生",
            university="计算机科学与技术学院",  # 新增
            email="lisi@university.edu",
            research_area="自然语言处理",
            bio="李四是我校计算机科学与技术学院2022级博士生，主要研究方向为自然语言处理和对话系统。",
            photo_url="",  # 空字符串表示无头像
            stats=[],
            publications=[],
            projects=[],
            news=[],
            education=[],
            experience=[]
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

def member_to_dict(member):
    return {
        'id': member.id,
        'name': member.name,
        'role': member.role,
        'university': member.university,
        'email': member.email,
        'research_area': member.research_area,
        'bio': member.bio,
        'photo_url': member.photo_url,
        'stats': member.stats,
        'publications': member.publications,
        'projects': member.projects,
        'news': member.news,
        'education': member.education,
        'experience': member.experience
    }

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
        # 基础字段（与之前相同）
        name = request.form['name']
        role = request.form['role']
        email = request.form['email']
        research_area = request.form['research_area']
        bio = request.form['bio']
        university = request.form['university']

        # JSON 字段（出版物除外）
        stats = parse_json_field(request.form.get('stats'), '统计信息')
        if stats is None: return render_template('admin/member_form.html')
        projects = parse_json_field(request.form.get('projects'), '项目')
        if projects is None: return render_template('admin/member_form.html')
        news = parse_json_field(request.form.get('news'), '新闻')
        if news is None: return render_template('admin/member_form.html')
        education = parse_json_field(request.form.get('education'), '教育经历')
        if education is None: return render_template('admin/member_form.html')
        experience = parse_json_field(request.form.get('experience'), '工作经历')
        if experience is None: return render_template('admin/member_form.html')

        # 头像处理
        photo = request.files.get('photo')
        photo_url = ''
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            import time
            filename = f"{int(time.time())}_{filename}"
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            photo_url = f"photos/{filename}"
        else:
            photo_url = request.form.get('photo_url', '')

        # 出版物处理（索引式）
        publications = []
        import re
        pattern = re.compile(r'^publication_title_(\d+)$')
        indices = set()
        for key in request.form.keys():
            match = pattern.match(key)
            if match:
                indices.add(int(match.group(1)))

        for idx in sorted(indices):
            title = request.form.get(f'publication_title_{idx}')
            if not title:
                continue
            authors = request.form.get(f'publication_authors_{idx}', '')
            year = request.form.get(f'publication_year_{idx}', '')
            venue = request.form.get(f'publication_venue_{idx}', '')

            links = {}
            # PDF 文件
            pdf_file = request.files.get(f'publication_pdf_{idx}')
            if pdf_file and allowed_pub_file(pdf_file.filename):
                filename = secure_filename(pdf_file.filename)
                import time
                filename = f"{int(time.time())}_{filename}"
                save_path = os.path.join(app.config['PUBLICATIONS_UPLOAD_FOLDER'], filename)
                pdf_file.save(save_path)
                links['pdf'] = f"static/publications/{filename}"

            # Code 文件
            code_file = request.files.get(f'publication_code_{idx}')
            if code_file and allowed_pub_file(code_file.filename):
                filename = secure_filename(code_file.filename)
                import time
                filename = f"{int(time.time())}_{filename}"
                save_path = os.path.join(app.config['PUBLICATIONS_UPLOAD_FOLDER'], filename)
                code_file.save(save_path)
                links['code'] = f"static/publications/{filename}"

            pub = {
                'year': int(year) if year.isdigit() else None,
                'title': title,
                'authors': authors,
                'venue': venue,
                'links': links,
                'url': request.form.get(f'publication_url_{idx}', '#')
            }
            publications.append(pub)

        # 创建成员对象
        member = Member(
            name=name, role=role, university=university, email=email,
            research_area=research_area, bio=bio, photo_url=photo_url,
            stats=stats, publications=publications, projects=projects,
            news=news, education=education, experience=experience
        )
        db.session.add(member)
        db.session.commit()
        export_members_to_json()
        flash('成员添加成功', 'success')
        return redirect(url_for('admin_members'))

    return render_template('admin/member_form.html', member=None, member_dict=None)


@app.route('/admin/members/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_member_edit(id):
    member = Member.query.get_or_404(id)
    if request.method == 'POST':
        # 基础字段
        member.name = request.form['name']
        member.role = request.form['role']
        member.university = request.form.get('university', '')
        member.email = request.form.get('email', '')
        member.research_area = request.form.get('research_area', '')
        member.bio = request.form.get('bio', '')

        # 头像处理
        photo = request.files.get('photo')
        if photo and allowed_file(photo.filename):
            # 删除旧头像（可选）
            if member.photo_url:
                old_path = os.path.join('static', member.photo_url)
                if os.path.exists(old_path):
                    os.remove(old_path)
            filename = secure_filename(photo.filename)
            import time
            filename = f"{int(time.time())}_{filename}"
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            member.photo_url = f"photos/{filename}"
        else:
            # 未上传新图片，使用手动输入的路径
            member.photo_url = request.form.get('photo_url', member.photo_url)

        # JSON 字段解析
        stats = parse_json_field(request.form.get('stats'), '统计信息')
        if stats is None: return render_template('admin/member_form.html', member=member, member_dict=member_to_dict(member))
        member.stats = stats

        # 出版物
        publications = []
        # 从 request.form 中找出所有 publication_title_ 前缀的键，提取索引
        import re
        pattern = re.compile(r'^publication_title_(\d+)$')
        indices = set()
        for key in request.form.keys():
            match = pattern.match(key)
            if match:
                indices.add(int(match.group(1)))

        for idx in sorted(indices):
            title = request.form.get(f'publication_title_{idx}')
            if not title:  # 如果标题为空，跳过该条目
                continue
            authors = request.form.get(f'publication_authors_{idx}', '')
            year = request.form.get(f'publication_year_{idx}', '')
            venue = request.form.get(f'publication_venue_{idx}', '')
            # 获取原有路径（隐藏字段）
            old_pdf = request.form.get(f'publication_pdf_path_{idx}', '')
            old_code = request.form.get(f'publication_code_path_{idx}', '')

            links = {}
            # 处理 PDF 文件上传
            pdf_file = request.files.get(f'publication_pdf_{idx}')
            if pdf_file and allowed_pub_file(pdf_file.filename):
                filename = secure_filename(pdf_file.filename)
                import time
                filename = f"{int(time.time())}_{filename}"
                save_path = os.path.join(app.config['PUBLICATIONS_UPLOAD_FOLDER'], filename)
                pdf_file.save(save_path)
                links['pdf'] = f"static/publications/{filename}"  # 存储相对路径
            else:
                # 没有上传新文件，则使用原有路径（可能为空）
                if old_pdf:
                    links['pdf'] = old_pdf

            # 处理 Code 文件上传（同理）
            code_file = request.files.get(f'publication_code_{idx}')
            if code_file and allowed_file(code_file.filename):
                filename = secure_filename(code_file.filename)
                import time
                filename = f"{int(time.time())}_{filename}"
                save_path = os.path.join(app.config['PUBLICATIONS_UPLOAD_FOLDER'], filename)
                code_file.save(save_path)
                links['code'] = f"static/publications/{filename}"
            else:
                if old_code:
                    links['code'] = old_code

            # 构建出版物对象
            pub = {
                'year': int(year) if year.isdigit() else None,
                'title': title,
                'authors': authors,
                'venue': venue,
                'links': links,
                'url': request.form.get(f'publication_url_{idx}', '#')
            }
            publications.append(pub)
        member.publications = publications

        projects = parse_json_field(request.form.get('projects'), '项目')
        if projects is None: return render_template('admin/member_form.html', member=member, member_dict=member_to_dict(member))
        member.projects = projects

        news = parse_json_field(request.form.get('news'), '新闻')
        if news is None: return render_template('admin/member_form.html', member=member, member_dict=member_to_dict(member))
        member.news = news

        education = parse_json_field(request.form.get('education'), '教育经历')
        if education is None: return render_template('admin/member_form.html', member=member, member_dict=member_to_dict(member))
        member.education = education

        experience = parse_json_field(request.form.get('experience'), '工作经历')
        if experience is None: return render_template('admin/member_form.html', member=member, member_dict=member_to_dict(member))
        member.experience = experience

        db.session.commit()
        export_members_to_json()
        flash('成员信息已更新', 'success')
        return redirect(url_for('admin_members'))

    member_dict = member_to_dict(member)
    return render_template('admin/member_form.html', member=member, member_dict=member_dict)

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

@app.route('/api/members')
def get_members():
    file_path = os.path.join(app.config['INSTANCE_DATA_PATH'], 'members.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify([])

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