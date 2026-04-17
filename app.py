from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime
import os, json, uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'motion-robotics-lms-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lms.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db = SQLAlchemy(app)

# ── Jinja filter ──────────────────────────────────────────────
@app.context_processor
def inject_enumerate():
    return dict(enumerate=enumerate)

@app.template_filter('from_json')
def from_json_filter(v):
    try: return json.loads(v)
    except: return []

# ═══════════════════════════════════════════════════════════════
#  MODELS
# ═══════════════════════════════════════════════════════════════

ROBOTICS_LEVELS = [
    'Level 1: Mech Tech',
    'Level 2: Electronics',
    'Level 3: Electro Mechanical',
    'Level 4: Digi-Coding',
    'Level 5: Digi-Sense',
    'Level 6: Wireless & IoT',
]

class User(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role          = db.Column(db.String(20), nullable=False)   # admin / teacher / student
    full_name     = db.Column(db.String(120))
    phone         = db.Column(db.String(20))
    school_name   = db.Column(db.String(120))
    roll_number   = db.Column(db.String(40))
    avatar_color  = db.Column(db.String(20), default='#4F46E5')
    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, p): self.password_hash = generate_password_hash(p)
    def check_password(self, p): return check_password_hash(self.password_hash, p)


class Class(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(100), nullable=False)
    school_name     = db.Column(db.String(120))
    robotics_level  = db.Column(db.String(80))   # one of ROBOTICS_LEVELS or None
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    teacher_classes = db.relationship('TeacherClass', backref='cls', cascade='all,delete-orphan')
    student_classes = db.relationship('StudentClass', backref='cls', cascade='all,delete-orphan')


class TeacherClass(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    class_id   = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    teacher    = db.relationship('User', backref='teacher_classes')


class StudentClass(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    class_id   = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    student    = db.relationship('User', backref='student_classes')


class Experiment(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    level       = db.Column(db.String(80))
    exp_number  = db.Column(db.Integer, default=0)
    video_url   = db.Column(db.String(500))
    file_path   = db.Column(db.String(300))
    file_name   = db.Column(db.String(200))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)


class ExperimentUnlock(db.Model):
    """Teacher unlocks an experiment for a class"""
    id            = db.Column(db.Integer, primary_key=True)
    experiment_id = db.Column(db.Integer, db.ForeignKey('experiment.id'), nullable=False)
    class_id      = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    teacher_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    deadline      = db.Column(db.DateTime)
    unlocked_at   = db.Column(db.DateTime, default=datetime.utcnow)
    experiment    = db.relationship('Experiment', backref='unlocks')
    cls           = db.relationship('Class', backref='unlocks')


class StudentProgress(db.Model):
    """Student submits completion of an experiment"""
    id            = db.Column(db.Integer, primary_key=True)
    student_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    experiment_id = db.Column(db.Integer, db.ForeignKey('experiment.id'), nullable=False)
    class_id      = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    status        = db.Column(db.String(20), default='pending')  # pending/approved/rejected
    submitted_at  = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at   = db.Column(db.DateTime)
    notes         = db.Column(db.Text)
    student       = db.relationship('User', backref='progress')
    experiment    = db.relationship('Experiment', backref='progress')
    cls           = db.relationship('Class', backref='progress')


class Exam(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    title        = db.Column(db.String(200), nullable=False)
    level        = db.Column(db.String(80))
    status       = db.Column(db.String(20), default='draft')  # draft/published
    scheduled_at = db.Column(db.DateTime)
    time_limit   = db.Column(db.Integer, default=30)
    passing_score= db.Column(db.Integer, default=60)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    questions    = db.relationship('ExamQuestion', backref='exam', cascade='all,delete-orphan')
    attempts     = db.relationship('ExamAttempt', backref='exam', cascade='all,delete-orphan')


class ExamQuestion(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    exam_id       = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    options_json  = db.Column(db.Text)  # JSON list
    correct       = db.Column(db.Text)
    points        = db.Column(db.Integer, default=1)
    order_index   = db.Column(db.Integer, default=0)


class ExamAttempt(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    student_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exam_id      = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    score        = db.Column(db.Float, default=0)
    total        = db.Column(db.Integer, default=0)
    percentage   = db.Column(db.Float, default=0)
    passed       = db.Column(db.Boolean, default=False)
    answers_json = db.Column(db.Text, default='{}')
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    student      = db.relationship('User', backref='exam_attempts')


class DigitalBook(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    level       = db.Column(db.String(80))
    description = db.Column(db.Text)
    file_path   = db.Column(db.String(300))
    file_name   = db.Column(db.String(200))
    cover_emoji = db.Column(db.String(10), default='📘')
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

# ═══════════════════════════════════════════════════════════════
#  AUTH HELPERS
# ═══════════════════════════════════════════════════════════════

def login_required(f):
    @wraps(f)
    def d(*a, **kw):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*a, **kw)
    return d

def role_required(*roles):
    def dec(f):
        @wraps(f)
        def d(*a, **kw):
            if 'user_id' not in session: return redirect(url_for('login'))
            if session.get('role') not in roles:
                flash('Access denied.', 'error')
                return redirect(url_for('dashboard'))
            return f(*a, **kw)
        return d
    return dec

def get_current_user():
    if 'user_id' in session: return User.query.get(session['user_id'])
    return None

@app.context_processor
def inject_globals():
    return dict(current_user=get_current_user(), ROBOTICS_LEVELS=ROBOTICS_LEVELS)

# ═══════════════════════════════════════════════════════════════
#  PUBLIC HOMEPAGE
# ═══════════════════════════════════════════════════════════════

@app.route('/')
def index():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    r = session.get('role')
    if r == 'admin':   return redirect(url_for('admin_dashboard'))
    if r == 'teacher': return redirect(url_for('teacher_dashboard'))
    return redirect(url_for('student_dashboard'))

@app.route('/login', methods=['GET','POST'])
def login():
    role = request.args.get('role', '')
    if request.method == 'POST':
        email    = request.form.get('email','').strip()
        password = request.form.get('password','')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password) and user.is_active:
            session['user_id']  = user.id
            session['role']     = user.role
            session['username'] = user.username
            session['full_name']= user.full_name or user.username
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.', 'error')
    return render_template('login.html', role=role)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ═══════════════════════════════════════════════════════════════
#  ADMIN
# ═══════════════════════════════════════════════════════════════

@app.route('/admin')
@role_required('admin')
def admin_dashboard():
    stats = dict(
        total_classes  = Class.query.count(),
        total_teachers = User.query.filter_by(role='teacher').count(),
        total_students = User.query.filter_by(role='student').count(),
        total_schools  = db.session.query(db.func.count(db.func.distinct(User.school_name))).filter(User.role=='student').scalar() or 0,
        total_exams    = Exam.query.count(),
    )
    recent_students = User.query.filter_by(role='student').order_by(User.created_at.desc()).limit(5).all()
    return render_template('admin/dashboard.html', **stats, recent_students=recent_students)

# ── Classes ──────────────────────────────────────────────────
@app.route('/admin/classes')
@role_required('admin')
def admin_classes():
    classes = Class.query.order_by(Class.created_at.desc()).all()
    stats = dict(
        total_classes   = Class.query.count(),
        with_level      = Class.query.filter(Class.robotics_level != None, Class.robotics_level != '').count(),
        schools_count   = db.session.query(db.func.count(db.func.distinct(Class.school_name))).scalar() or 0,
        total_students  = StudentClass.query.count(),
    )
    return render_template('admin/classes.html', classes=classes, **stats)

@app.route('/admin/classes/add', methods=['POST'])
@role_required('admin')
def admin_add_class():
    name   = request.form.get('name','').strip()
    school = request.form.get('school','').strip()
    level  = request.form.get('level','').strip() or None
    if name:
        c = Class(name=name, school_name=school, robotics_level=level)
        db.session.add(c); db.session.commit()
        flash(f'Class "{name}" created!', 'success')
    return redirect(url_for('admin_classes'))

@app.route('/admin/classes/<int:cid>/level', methods=['POST'])
@role_required('admin')
def admin_set_class_level(cid):
    c = Class.query.get_or_404(cid)
    c.robotics_level = request.form.get('level') or None
    db.session.commit()
    flash('Robotics level updated!', 'success')
    return redirect(url_for('admin_classes'))

@app.route('/admin/classes/<int:cid>/delete', methods=['POST'])
@role_required('admin')
def admin_delete_class(cid):
    c = Class.query.get_or_404(cid); db.session.delete(c); db.session.commit()
    flash('Class deleted.', 'success')
    return redirect(url_for('admin_classes'))

# ── Teachers ─────────────────────────────────────────────────
@app.route('/admin/teachers')
@role_required('admin')
def admin_teachers():
    q = request.args.get('q','')
    query = User.query.filter_by(role='teacher')
    if q: query = query.filter(User.full_name.contains(q)|User.email.contains(q))
    teachers = query.order_by(User.created_at.desc()).all()
    classes  = Class.query.order_by(Class.name).all()
    stats = dict(
        total_teachers  = User.query.filter_by(role='teacher').count(),
        schools_covered = db.session.query(db.func.count(db.func.distinct(User.school_name))).filter(User.role=='teacher').scalar() or 0,
        classes_assigned= TeacherClass.query.count(),
    )
    return render_template('admin/teachers.html', teachers=teachers, classes=classes, q=q, **stats)

@app.route('/admin/teachers/add', methods=['POST'])
@role_required('admin')
def admin_add_teacher():
    full_name  = request.form.get('full_name','').strip()
    email      = request.form.get('email','').strip()
    password   = request.form.get('password','')
    phone      = request.form.get('phone','').strip()
    school     = request.form.get('school','').strip()
    class_ids  = request.form.getlist('class_ids')
    colors = ['#4F46E5','#0EA5E9','#10B981','#F59E0B','#EF4444','#8B5CF6']
    import random
    if User.query.filter_by(email=email).first():
        flash('Email already exists.', 'error')
        return redirect(url_for('admin_teachers'))
    username = email.split('@')[0] + str(random.randint(10,99))
    t = User(username=username, email=email, role='teacher', full_name=full_name,
             phone=phone, school_name=school, avatar_color=random.choice(colors))
    t.set_password(password); db.session.add(t); db.session.flush()
    for cid in class_ids:
        db.session.add(TeacherClass(teacher_id=t.id, class_id=int(cid)))
    db.session.commit()
    flash(f'Teacher {full_name} added!', 'success')
    return redirect(url_for('admin_teachers'))

@app.route('/admin/teachers/<int:tid>/delete', methods=['POST'])
@role_required('admin')
def admin_delete_teacher(tid):
    t = User.query.get_or_404(tid); db.session.delete(t); db.session.commit()
    flash('Teacher deleted.', 'success')
    return redirect(url_for('admin_teachers'))

# ── Students ─────────────────────────────────────────────────
@app.route('/admin/students')
@role_required('admin')
def admin_students():
    q = request.args.get('q','')
    query = User.query.filter_by(role='student')
    if q: query = query.filter(User.full_name.contains(q)|User.email.contains(q)|User.roll_number.contains(q))
    students = query.order_by(User.created_at.desc()).all()
    classes  = Class.query.order_by(Class.name).all()
    stats = dict(
        total_students = User.query.filter_by(role='student').count(),
        schools        = db.session.query(db.func.count(db.func.distinct(User.school_name))).filter(User.role=='student').scalar() or 0,
        programs       = db.session.query(db.func.count(db.func.distinct(StudentClass.class_id))).scalar() or 0,
        classes_count  = Class.query.count(),
    )
    return render_template('admin/students.html', students=students, classes=classes, q=q, **stats)

@app.route('/admin/students/add', methods=['POST'])
@role_required('admin')
def admin_add_student():
    full_name   = request.form.get('full_name','').strip()
    email       = request.form.get('email','').strip()
    password    = request.form.get('password','')
    roll_number = request.form.get('roll_number','').strip()
    school      = request.form.get('school','').strip()
    class_id    = request.form.get('class_id','')
    colors = ['#F59E0B','#10B981','#3B82F6','#EC4899','#8B5CF6','#14B8A6']
    import random
    if User.query.filter_by(email=email).first():
        flash('Email already exists.', 'error')
        return redirect(url_for('admin_students'))
    username = email.split('@')[0] + str(random.randint(10,99))
    s = User(username=username, email=email, role='student', full_name=full_name,
             roll_number=roll_number, school_name=school, avatar_color=random.choice(colors))
    s.set_password(password); db.session.add(s); db.session.flush()
    if class_id:
        db.session.add(StudentClass(student_id=s.id, class_id=int(class_id)))
    db.session.commit()
    flash(f'Student {full_name} added!', 'success')
    return redirect(url_for('admin_students'))

@app.route('/admin/students/<int:sid>/delete', methods=['POST'])
@role_required('admin')
def admin_delete_student(sid):
    s = User.query.get_or_404(sid); db.session.delete(s); db.session.commit()
    flash('Student deleted.', 'success')
    return redirect(url_for('admin_students'))

# ── Experiments (Admin manages master list) ───────────────────
@app.route('/admin/courses')
@role_required('admin')
def admin_courses():
    level_filter = request.args.get('level','')
    query = Experiment.query
    if level_filter: query = query.filter_by(level=level_filter)
    experiments = query.order_by(Experiment.level, Experiment.exp_number).all()
    books = DigitalBook.query.order_by(DigitalBook.level).all()
    return render_template('admin/courses.html', experiments=experiments, books=books, level_filter=level_filter)

@app.route('/admin/courses/experiment/add', methods=['POST'])
@role_required('admin')
def admin_add_experiment():
    title      = request.form.get('title','').strip()
    desc       = request.form.get('description','').strip()
    level      = request.form.get('level','')
    exp_number = int(request.form.get('exp_number', 0) or 0)
    video_url  = request.form.get('video_url','').strip()
    file_path = file_name = None
    if 'file' in request.files:
        f = request.files['file']
        if f and f.filename:
            fname = secure_filename(f'{uuid.uuid4()}_{f.filename}')
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
            file_path = fname; file_name = f.filename
    e = Experiment(title=title, description=desc, level=level,
                   exp_number=exp_number, video_url=video_url,
                   file_path=file_path, file_name=file_name)
    db.session.add(e); db.session.commit()
    flash(f'Experiment "{title}" added!', 'success')
    return redirect(url_for('admin_courses'))

@app.route('/admin/courses/experiment/<int:eid>/delete', methods=['POST'])
@role_required('admin')
def admin_delete_experiment(eid):
    e = Experiment.query.get_or_404(eid); db.session.delete(e); db.session.commit()
    flash('Experiment deleted.', 'success')
    return redirect(url_for('admin_courses'))

@app.route('/admin/courses/book/add', methods=['POST'])
@role_required('admin')
def admin_add_book():
    title = request.form.get('title','').strip()
    level = request.form.get('level','')
    desc  = request.form.get('description','').strip()
    emoji = request.form.get('cover_emoji','📘')
    file_path = file_name = None
    if 'file' in request.files:
        f = request.files['file']
        if f and f.filename:
            fname = secure_filename(f'{uuid.uuid4()}_{f.filename}')
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
            file_path = fname; file_name = f.filename
    b = DigitalBook(title=title, level=level, description=desc, cover_emoji=emoji,
                    file_path=file_path, file_name=file_name)
    db.session.add(b); db.session.commit()
    flash(f'Book "{title}" added!', 'success')
    return redirect(url_for('admin_courses'))

# ── Exams ────────────────────────────────────────────────────
@app.route('/admin/exams')
@role_required('admin')
def admin_exams():
    exams = Exam.query.order_by(Exam.created_at.desc()).all()
    stats = dict(
        total_exams = Exam.query.count(),
        upcoming    = Exam.query.filter(Exam.scheduled_at > datetime.utcnow()).count(),
        completed   = ExamAttempt.query.distinct(ExamAttempt.exam_id).count(),
    )
    return render_template('admin/exams.html', exams=exams, **stats)

@app.route('/admin/exams/add', methods=['POST'])
@role_required('admin')
def admin_add_exam():
    title        = request.form.get('title','').strip()
    level        = request.form.get('level','')
    time_limit   = int(request.form.get('time_limit', 30) or 30)
    passing_score= int(request.form.get('passing_score', 60) or 60)
    e = Exam(title=title, level=level, time_limit=time_limit, passing_score=passing_score)
    db.session.add(e); db.session.commit()
    flash(f'Exam "{title}" created!', 'success')
    return redirect(url_for('admin_exam_detail', eid=e.id))

@app.route('/admin/exams/<int:eid>')
@role_required('admin')
def admin_exam_detail(eid):
    exam = Exam.query.get_or_404(eid)
    return render_template('admin/exam_detail.html', exam=exam)

@app.route('/admin/exams/<int:eid>/publish', methods=['POST'])
@role_required('admin')
def admin_publish_exam(eid):
    exam = Exam.query.get_or_404(eid)
    exam.status = 'published' if exam.status == 'draft' else 'draft'
    db.session.commit()
    flash(f'Exam {"published" if exam.status=="published" else "unpublished"}!', 'success')
    return redirect(url_for('admin_exams'))

@app.route('/admin/exams/<int:eid>/question/add', methods=['POST'])
@role_required('admin')
def admin_add_question(eid):
    exam = Exam.query.get_or_404(eid)
    qtext   = request.form.get('question_text','').strip()
    correct = request.form.get('correct_answer','').strip()
    options = [request.form.get(f'opt_{i}','').strip() for i in range(1,5)]
    options = [o for o in options if o]
    count   = ExamQuestion.query.filter_by(exam_id=eid).count()
    q = ExamQuestion(exam_id=eid, question_text=qtext,
                     options_json=json.dumps(options),
                     correct=correct, order_index=count)
    db.session.add(q); db.session.commit()
    flash('Question added!', 'success')
    return redirect(url_for('admin_exam_detail', eid=eid))

@app.route('/admin/exams/<int:eid>/delete', methods=['POST'])
@role_required('admin')
def admin_delete_exam(eid):
    e = Exam.query.get_or_404(eid); db.session.delete(e); db.session.commit()
    flash('Exam deleted.', 'success')
    return redirect(url_for('admin_exams'))

# ── Reports ──────────────────────────────────────────────────
@app.route('/admin/reports')
@role_required('admin')
def admin_reports():
    attempts = ExamAttempt.query.order_by(ExamAttempt.completed_at.desc()).all()
    progress = StudentProgress.query.filter_by(status='approved').order_by(StudentProgress.submitted_at.desc()).all()
    return render_template('admin/reports.html', attempts=attempts, progress=progress)

# ── Settings ─────────────────────────────────────────────────
@app.route('/admin/settings')
@role_required('admin')
def admin_settings():
    return render_template('admin/settings.html')

# ═══════════════════════════════════════════════════════════════
#  TEACHER PORTAL
# ═══════════════════════════════════════════════════════════════

@app.route('/teacher')
@role_required('teacher')
def teacher_dashboard():
    teacher = get_current_user()
    my_classes = [tc.cls for tc in teacher.teacher_classes]
    class_ids  = [c.id for c in my_classes]
    total_students  = StudentClass.query.filter(StudentClass.class_id.in_(class_ids)).count() if class_ids else 0
    total_exps      = sum(
        Experiment.query.filter_by(level=c.robotics_level).count()
        for c in my_classes if c.robotics_level
    )
    pending = StudentProgress.query.filter(
        StudentProgress.class_id.in_(class_ids),
        StudentProgress.status=='pending'
    ).all() if class_ids else []

    class_data = []
    for c in my_classes:
        students_in  = StudentClass.query.filter_by(class_id=c.id).count()
        unlocked     = ExperimentUnlock.query.filter_by(class_id=c.id, teacher_id=teacher.id).count()
        total_exp    = Experiment.query.filter_by(level=c.robotics_level).count() if c.robotics_level else 0
        approved     = StudentProgress.query.filter_by(class_id=c.id, status='approved').count()
        pend_count   = StudentProgress.query.filter_by(class_id=c.id, status='pending').count()
        completions  = approved
        class_data.append(dict(
            cls=c, students=students_in, unlocked=unlocked,
            total_exp=total_exp, approved=approved, pend_count=pend_count,
            completions=completions
        ))

    return render_template('teacher/dashboard.html',
        my_classes=class_data, total_students=total_students,
        total_exps=total_exps, pending=pending)

@app.route('/teacher/class/<int:cid>/experiments')
@role_required('teacher')
def teacher_class_experiments(cid):
    teacher = get_current_user()
    cls     = Class.query.get_or_404(cid)
    experiments = Experiment.query.filter_by(level=cls.robotics_level).order_by(Experiment.exp_number).all() if cls.robotics_level else []
    unlocked_ids = {u.experiment_id for u in ExperimentUnlock.query.filter_by(class_id=cid, teacher_id=teacher.id).all()}
    exp_data = []
    for e in experiments:
        unlock_obj = ExperimentUnlock.query.filter_by(experiment_id=e.id, class_id=cid).first()
        exp_data.append(dict(exp=e, is_unlocked=e.id in unlocked_ids, unlock=unlock_obj))
    students = [sc.student for sc in StudentClass.query.filter_by(class_id=cid).all()]
    return render_template('teacher/experiments.html', cls=cls, exp_data=exp_data, students=students)

@app.route('/teacher/class/<int:cid>/experiment/<int:eid>/unlock', methods=['POST'])
@role_required('teacher')
def teacher_unlock_experiment(cid, eid):
    teacher  = get_current_user()
    deadline_str = request.form.get('deadline','').strip()
    deadline = None
    if deadline_str:
        try: deadline = datetime.fromisoformat(deadline_str)
        except: pass
    existing = ExperimentUnlock.query.filter_by(experiment_id=eid, class_id=cid).first()
    if not existing:
        u = ExperimentUnlock(experiment_id=eid, class_id=cid, teacher_id=teacher.id, deadline=deadline)
        db.session.add(u)
        db.session.commit()
        flash('Experiment unlocked for class!', 'success')
    else:
        flash('Already unlocked.', 'info')
    return redirect(url_for('teacher_class_experiments', cid=cid))

@app.route('/teacher/class/<int:cid>/experiment/<int:eid>/lock', methods=['POST'])
@role_required('teacher')
def teacher_lock_experiment(cid, eid):
    u = ExperimentUnlock.query.filter_by(experiment_id=eid, class_id=cid).first()
    if u: db.session.delete(u); db.session.commit(); flash('Experiment locked.', 'success')
    return redirect(url_for('teacher_class_experiments', cid=cid))

@app.route('/teacher/progress/<int:pid>/approve', methods=['POST'])
@role_required('teacher')
def teacher_approve_progress(pid):
    p = StudentProgress.query.get_or_404(pid)
    p.status = 'approved'; p.reviewed_at = datetime.utcnow()
    db.session.commit(); flash('Progress approved!', 'success')
    return redirect(url_for('teacher_dashboard'))

@app.route('/teacher/progress/<int:pid>/reject', methods=['POST'])
@role_required('teacher')
def teacher_reject_progress(pid):
    p = StudentProgress.query.get_or_404(pid)
    p.status = 'rejected'; p.reviewed_at = datetime.utcnow()
    db.session.commit(); flash('Submission rejected.', 'info')
    return redirect(url_for('teacher_dashboard'))

@app.route('/teacher/class/<int:cid>/reports')
@role_required('teacher')
def teacher_reports(cid):
    cls      = Class.query.get_or_404(cid)
    students = [sc.student for sc in StudentClass.query.filter_by(class_id=cid).all()]
    progress = StudentProgress.query.filter_by(class_id=cid).order_by(StudentProgress.submitted_at.desc()).all()
    return render_template('teacher/reports.html', cls=cls, students=students, progress=progress)

# ═══════════════════════════════════════════════════════════════
#  STUDENT PORTAL
# ═══════════════════════════════════════════════════════════════

@app.route('/student')
@role_required('student')
def student_dashboard():
    student = get_current_user()
    sc      = StudentClass.query.filter_by(student_id=student.id).first()
    cls     = sc.cls if sc else None
    level   = cls.robotics_level if cls else None

    total_exp   = Experiment.query.filter_by(level=level).count() if level else 0
    unlocked    = ExperimentUnlock.query.filter_by(class_id=cls.id).count() if cls else 0
    approved    = StudentProgress.query.filter_by(student_id=student.id, status='approved').count()
    pending     = StudentProgress.query.filter_by(student_id=student.id, status='pending').count()
    progress_pct= round((approved / total_exp * 100), 1) if total_exp else 0

    return render_template('student/dashboard.html',
        cls=cls, level=level, total_exp=total_exp,
        unlocked=unlocked, approved=approved, pending=pending,
        progress_pct=progress_pct)

@app.route('/student/experiments')
@role_required('student')
def student_experiments():
    student = get_current_user()
    sc      = StudentClass.query.filter_by(student_id=student.id).first()
    cls     = sc.cls if sc else None
    if not cls:
        return render_template('student/experiments.html', cls=None, exp_data=[])
    unlocked_exps = (db.session.query(Experiment)
        .join(ExperimentUnlock, ExperimentUnlock.experiment_id == Experiment.id)
        .filter(ExperimentUnlock.class_id == cls.id)
        .order_by(Experiment.exp_number).all())
    approved_ids = {p.experiment_id for p in StudentProgress.query.filter_by(student_id=student.id, status='approved').all()}
    pending_ids  = {p.experiment_id for p in StudentProgress.query.filter_by(student_id=student.id, status='pending').all()}
    exp_data = []
    for e in unlocked_exps:
        unlock = ExperimentUnlock.query.filter_by(experiment_id=e.id, class_id=cls.id).first()
        exp_data.append(dict(
            exp=e, unlock=unlock,
            is_approved=e.id in approved_ids,
            is_pending=e.id in pending_ids,
        ))
    return render_template('student/experiments.html', cls=cls, exp_data=exp_data)

@app.route('/student/experiments/<int:eid>/submit', methods=['POST'])
@role_required('student')
def student_submit_experiment(eid):
    student = get_current_user()
    sc      = StudentClass.query.filter_by(student_id=student.id).first()
    if not sc: return redirect(url_for('student_experiments'))
    existing = StudentProgress.query.filter_by(student_id=student.id, experiment_id=eid).first()
    if not existing:
        p = StudentProgress(student_id=student.id, experiment_id=eid, class_id=sc.class_id)
        db.session.add(p); db.session.commit()
        flash('Submitted for teacher approval!', 'success')
    else:
        flash('Already submitted.', 'info')
    return redirect(url_for('student_experiments'))

@app.route('/student/books')
@role_required('student')
def student_books():
    student = get_current_user()
    sc      = StudentClass.query.filter_by(student_id=student.id).first()
    level   = sc.cls.robotics_level if sc and sc.cls else None
    books   = DigitalBook.query.filter_by(level=level).all() if level else []
    return render_template('student/books.html', books=books, level=level)

@app.route('/student/exams')
@role_required('student')
def student_exams():
    student = get_current_user()
    sc      = StudentClass.query.filter_by(student_id=student.id).first()
    level   = sc.cls.robotics_level if sc and sc.cls else None
    exams   = Exam.query.filter_by(level=level, status='published').all() if level else []
    attempted_ids = {a.exam_id for a in ExamAttempt.query.filter_by(student_id=student.id).all()}
    return render_template('student/exams.html', exams=exams, attempted_ids=attempted_ids)

@app.route('/student/exams/<int:eid>/take')
@role_required('student')
def student_take_exam(eid):
    exam = Exam.query.get_or_404(eid)
    student = get_current_user()
    existing = ExamAttempt.query.filter_by(student_id=student.id, exam_id=eid).first()
    qs = sorted(exam.questions, key=lambda x: x.order_index)
    for q in qs:
        q.options_list = json.loads(q.options_json or '[]')
    return render_template('student/take_exam.html', exam=exam, questions=qs, existing=existing)

@app.route('/student/exams/<int:eid>/submit', methods=['POST'])
@role_required('student')
def student_submit_exam(eid):
    exam    = Exam.query.get_or_404(eid)
    student = get_current_user()
    answers = {}; score = 0
    total   = sum(q.points for q in exam.questions)
    for q in exam.questions:
        ans = request.form.get(f'q_{q.id}','').strip()
        answers[str(q.id)] = ans
        if ans.lower() == q.correct.lower(): score += q.points
    pct    = round(score / total * 100, 1) if total else 0
    passed = pct >= exam.passing_score
    a = ExamAttempt(student_id=student.id, exam_id=eid,
                    score=score, total=total, percentage=pct,
                    passed=passed, answers_json=json.dumps(answers))
    db.session.add(a); db.session.commit()
    return redirect(url_for('student_exam_result', aid=a.id))

@app.route('/student/results')
@role_required('student')
def student_results():
    student  = get_current_user()
    attempts = ExamAttempt.query.filter_by(student_id=student.id).order_by(ExamAttempt.completed_at.desc()).all()
    return render_template('student/results.html', attempts=attempts)

@app.route('/student/results/<int:aid>')
@role_required('student')
def student_exam_result(aid):
    attempt  = ExamAttempt.query.get_or_404(aid)
    answers  = json.loads(attempt.answers_json or '{}')
    questions= sorted(attempt.exam.questions, key=lambda x: x.order_index)
    for q in questions:
        q.student_answer = answers.get(str(q.id),'')
        q.is_correct     = q.student_answer.lower() == q.correct.lower()
        q.options_list   = json.loads(q.options_json or '[]')
    return render_template('student/exam_result.html', attempt=attempt, questions=questions)

@app.route('/student/certificate')
@role_required('student')
def student_certificate():
    student = get_current_user()
    sc      = StudentClass.query.filter_by(student_id=student.id).first()
    cls     = sc.cls if sc else None
    level   = cls.robotics_level if cls else None
    total_exp = Experiment.query.filter_by(level=level).count() if level else 0
    approved  = StudentProgress.query.filter_by(student_id=student.id, status='approved').count()
    eligible  = total_exp > 0 and approved >= total_exp
    passed_exams = ExamAttempt.query.filter_by(student_id=student.id, passed=True).count()
    return render_template('student/certificate.html',
        cls=cls, level=level, eligible=eligible,
        approved=approved, total_exp=total_exp, passed_exams=passed_exams)

# ── File serving ─────────────────────────────────────────────
@app.route('/uploads/<path:filename>')
@login_required
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ═══════════════════════════════════════════════════════════════
#  DB INIT + SEED
# ═══════════════════════════════════════════════════════════════

def init_db():
    with app.app_context():
        db.create_all()
        if User.query.filter_by(role='admin').first(): return

        # Admin
        admin = User(username='admin', email='admin@motionrobotics.in',
                     role='admin', full_name='System Administrator', avatar_color='#4F46E5')
        admin.set_password('admin123')
        db.session.add(admin)

        # Teacher
        teacher = User(username='teacher1', email='teacher@motionrobotics.in',
                       role='teacher', full_name='Ms. Sanika Sharma',
                       phone='9255452350', school_name='CIS', avatar_color='#0EA5E9')
        teacher.set_password('teacher123')
        db.session.add(teacher)

        # Student
        student = User(username='student1', email='student@motionrobotics.in',
                       role='student', full_name='Johe Kumar',
                       roll_number='CIS001', school_name='CIS', avatar_color='#F59E0B')
        student.set_password('student123')
        db.session.add(student)
        db.session.flush()

        # Class
        cls = Class(name='Grade 3A', school_name='CIS', robotics_level='Level 2: Electronics')
        db.session.add(cls); db.session.flush()
        db.session.add(TeacherClass(teacher_id=teacher.id, class_id=cls.id))
        db.session.add(StudentClass(student_id=student.id, class_id=cls.id))

        # Experiments
        sample_exps = [
            ('Introduction to Electronics', 'Learn basic electronics concepts', 1),
            ('Building a Simple Circuit', 'Build your first LED circuit', 2),
            ('LED Blink with Arduino', 'Program Arduino to blink an LED', 3),
            ('Reading a Sensor', 'Interface a temperature sensor', 4),
            ('Connecting Two LEDs in Series', 'Build a series LED circuit', 5),
            ('Switching ON/OFF Buzzer by Switch', 'Control a buzzer with a switch', 6),
            ('Explore Magnetic Reed Switch', 'Build a circuit with magnetic reed switch', 7),
            ('Connecting Resistor in Circuit', 'Add resistors to your circuits', 8),
            ('Connecting LDR in Circuit', 'Build a light-sensing circuit', 9),
        ]
        exps = []
        for title, desc, num in sample_exps:
            e = Experiment(title=title, description=desc,
                           level='Level 2: Electronics', exp_number=num)
            db.session.add(e); exps.append(e)
        db.session.flush()

        # Unlock first 6 for teacher
        for e in exps[:6]:
            db.session.add(ExperimentUnlock(experiment_id=e.id, class_id=cls.id, teacher_id=teacher.id))

        # Exams
        for lvl in ROBOTICS_LEVELS:
            ex = Exam(title=f'{lvl.split(": ")[1]} Final Assessment', level=lvl,
                      status='draft', time_limit=30, passing_score=60)
            db.session.add(ex)
        db.session.flush()

        # Book
        b = DigitalBook(title='Electronics Fundamentals', level='Level 2: Electronics',
                        description='Complete guide to electronics for beginners', cover_emoji='📘')
        db.session.add(b)
        db.session.commit()
        print('✅ Database seeded!')

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
