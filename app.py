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

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)          # 作品名称
    author = db.Column(db.String(200))                         # 作者
    time = db.Column(db.String(20))                            # 发表时间，如 "2025-01"
    type = db.Column(db.String(20), nullable=False)            # 类型：论文、专利
    url = db.Column(db.String(500))                            # 链接

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

def export_products_to_json():
    products = Product.query.all()
    data = []
    for p in products:
        data.append({
            'id': p.id,
            'name': p.name,
            'author': p.author,
            'time': p.time,
            'type': p.type,
            'url': p.url
        })
    file_path = os.path.join(app.config['INSTANCE_DATA_PATH'], 'publications.json')
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

@app.route('/publications')
def publications():
    products = Product.query.all()
    # 提取所有年份并排序
    years = sorted(set(p.time[:4] for p in products if p.time and len(p.time)>=4), reverse=True)
    # 按年份分组
    grouped = {}
    for p in products:
        year = p.time[:4] if p.time and len(p.time)>=4 else '其他'
        grouped.setdefault(year, []).append(p)
    # 对每个年份内的产品按时间倒序（假设time格式 YYYY-MM，可直接字符串排序）
    for year in grouped:
        grouped[year].sort(key=lambda x: x.time or '', reverse=True)
    return render_template('publications.html', years=years, grouped=grouped)

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

    if not Product.query.first():
        product1 = Product(
            name="Lgr5+ cells regulate small intestinal morphogenesis before villification",
            author="Zhao LZ, Xie YC, Song WL, Shen YH, Liu HD, Luo SW, Chen YG",
            time="2026-01",
            type="论文",
            url="#"
        )
        product2 = Product(
            name="Oral Delivery of R-spondin1-Loaded Small Extracellular Vesicles Activates WNT Signaling Pathway to Accelerate Intestinal Injury Repair and Reverse Aging",
            author="Yang LY, Wang X, Wei XY, Yu P, Wang SX, Lin YF, Yang Y, Jiang T, Liu Y, Qiao ZP, Zhang JX, Yu SC, Chen YG, Chan YS",
            time="2026-01",
            type="论文",
            url="#"
        )
        product3 = Product(
            name="Control of airway basal stem cell-mediated lung repair by TGF-β signaling",
            author="Zou T, Zhang S, Liu M, Chen Q, Wang S, Niu L, Chen YG, Zhang T, Zuo W",
            time="2026-01",
            type="论文",
            url="#"
        )
        product4 = Product(
            name="Crotonate enhances intestinal regeneration after injury via HBO1-mediated H3K14 crotonylation",
            author="Xiao YH, Yu SC, Zhang MX, Zhong NS, Hua S, Fang Z, Zhang Z, Liu HD, Tan RH, Liu Y, Chen YG",
            time="2025-01",
            type="论文",
            url="#"
        )
        db.session.add_all([product1, product2, product3, product4])
        db.session.commit()

    # 初始导出 JSON 文件
    export_members_to_json()
    export_resources_to_json()
    export_products_to_json()

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
    product_count = Product.query.count()
    return render_template('admin/dashboard.html',
                           member_count=member_count,
                           resource_count=resource_count,
                           product_count=product_count)

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

@app.route('/api/members')
def get_members():
    file_path = os.path.join(app.config['INSTANCE_DATA_PATH'], 'members.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify([])

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

# ----- 成果管理 -----
@app.route('/admin/products')
@login_required
def admin_products():
    products = Product.query.all()
    return render_template('admin/products.html', products=products)

@app.route('/admin/products/add', methods=['GET', 'POST'])
@login_required
def admin_product_add():
    if request.method == 'POST':
        name = request.form['name']
        author = request.form.get('author', '')
        time = request.form.get('time', '')
        type_ = request.form['type']
        url = request.form.get('url', '')
        product = Product(name=name, author=author, time=time, type=type_, url=url)
        db.session.add(product)
        db.session.commit()
        if 'export_products_to_json' in globals():
            export_products_to_json()
        flash('成果添加成功', 'success')
        return redirect(url_for('admin_products'))
    return render_template('admin/product_form.html')

@app.route('/admin/products/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_product_edit(id):
    product = Product.query.get_or_404(id)
    if request.method == 'POST':
        product.name = request.form['name']
        product.author = request.form.get('author', '')
        product.time = request.form.get('time', '')
        product.type = request.form['type']
        product.url = request.form.get('url', '')
        db.session.commit()
        if 'export_products_to_json' in globals():
            export_products_to_json()
        flash('成果已更新', 'success')
        return redirect(url_for('admin_products'))
    return render_template('admin/product_form.html', product=product)

@app.route('/admin/products/delete/<int:id>')
@login_required
def admin_product_delete(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    if 'export_products_to_json' in globals():
        export_products_to_json()
    flash('成果已删除', 'success')
    return redirect(url_for('admin_products'))

if __name__ == '__main__':
    app.run(debug=True)