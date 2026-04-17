# 🤖 Motion Robotics LMS v2

## Quick Start

```bash
# 1. Install dependencies
pip install flask flask-sqlalchemy werkzeug

# 2. Run
python app.py

# 3. Open browser
http://localhost:5000
```

## Demo Accounts

| Role    | Email                           | Password     |
|---------|---------------------------------|--------------|
| Admin   | admin@motionrobotics.in         | admin123     |
| Teacher | teacher@motionrobotics.in       | teacher123   |
| Student | student@motionrobotics.in       | student123   |

## Structure

```
lms/
├── app.py                        # Flask backend — all routes & models
├── requirements.txt
├── static/
│   ├── logo.png                  # Motion Robotics logo
│   ├── css/main.css              # Full design system + dark/light mode
│   └── js/main.js                # Theme, sidebar, animations
├── templates/
│   ├── index.html                # Public homepage
│   ├── login.html                # Unified login with role tabs
│   ├── base.html                 # Shared sidebar layout
│   ├── admin/                    # 9 admin pages
│   ├── teacher/                  # 4 teacher pages
│   └── student/                  # 9 student pages
└── uploads/                      # Uploaded files
```

## Features

### 🌐 Public Homepage
- Navigation bar with Student / Teacher / Admin login buttons
- Hero section with animated gradient
- 6-feature grid (Hands-on Kits, Arduino Labs, Certificates, Teacher Dashboard, 6-Level Curriculum, Exam System)
- 6-Level Curriculum overview cards
- CTA section + Footer with links

### 🛡️ Admin Portal (School Admin)
- Dashboard with stats and quick actions
- **Classes** — Add classes, assign robotics levels (6 levels)
- **Teachers** — Add teachers, assign to classes
- **Students** — Add students with roll numbers, auto-assign program by class level
- **Courses** — Upload experiments per level + Digital Books
- **Exams** — Create MCQ exams per level, publish/unpublish
- **Reports** — Exam results + experiment progress
- **Settings** — General, security, appearance settings

### 👩‍🏫 Teacher Portal (no sidebar, clean top-bar)
- Dashboard with class cards showing progress bars
- Pending Approvals widget — approve/reject student submissions
- **Experiments** — Unlock/lock experiments for each class with optional deadlines
- **Reports** — Per-class student progress table

### 🎒 Student Portal (sidebar layout)
- **Dashboard** — Welcome banner, 4 stat cards, progress bar, nav cards
- **Experiments** — List of unlocked experiments with Start/Review/Approve status
- **Digital Books** — Level-specific PDF books
- **Examination** — Take MCQ exams with live timer + progress bar
- **Results** — History of all attempts with scores
- **Certificate** — Earned on completing all experiments + passing exam

### 🎨 Design
- Clean white/gray palette (light) + deep navy (dark)
- Inter + Poppins fonts
- Full dark/light mode toggle (persisted in localStorage)
- Mobile responsive with hamburger sidebar
- Modal forms for adding users/classes
- Animated stat counters + progress bars
