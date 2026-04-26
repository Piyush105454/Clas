# CLAS - Class Learning & Attendance System

## 📋 Project Overview

**CLAS (Class Learning & Attendance System)** is a comprehensive education management platform designed to handle content-driven teaching, real-world session execution, and accurate attendance tracking across schools and classes.

### 🎯 Core Philosophy
> **Content is FIXED, Dates are FLEXIBLE**

CLAS separates **WHAT is taught** from **WHEN it is taught**, ensuring that learning content is never lost even when calendar days are skipped due to holidays, facilitator absence, or cancelled classes.

## 🏗️ System Architecture

### Key Design Principles
- **Two-Layer Session System**: Planned Sessions (content) + Actual Sessions (execution)
- **Automatic Session Shifting**: System automatically selects next incomplete session
- **Grouped Sessions & Step Tracking**: Support for multi-part sessions and granular progress tracking
- **Role-Based Access Control**: Admin, Facilitator, and Supervisor roles
- **PWA Ready**: Offline support and home screen installation for facilitators
- **Growth Intelligence**: Data-driven student progress analysis and at-risk tracking
- **Real-World Flexibility**: Handles holidays, cancellations, and irregular schedules

## 👥 User Roles

### 🔧 Admin (System Controller)
- Creates schools and class sections
- Defines syllabus using Planned Sessions
- Assigns facilitators to schools
- Views session history and attendance reports
- Manages users and system configuration

### 👨‍🏫 Facilitator (Teacher/Executor)
- Views assigned schools and classes
- Sees only today's actionable session
- Conducts sessions or marks holiday/cancellation
- Marks student attendance
- Handles daily execution

### 👀 Supervisor (Observer/Monitor)
- Views session progress
- Reviews attendance trends
- Identifies irregularities
- Monitors facilitator performance (read-only)

## 📁 Project Structure

```
CLAS/
├── 📁 CLAS/                          # Django project configuration
│   ├── __init__.py
│   ├── asgi.py                       # ASGI configuration
│   ├── settings.py                   # Django settings
│   ├── urls.py                       # Main URL configuration
│   └── wsgi.py                       # WSGI configuration
│
├── 📁 class/                         # Main Django app
│   ├── 📁 management/                # Django management commands
│   │   └── 📁 commands/
│   │       ├── create_admin.py       # Create admin user command
│   │       └── __init__.py
│   │
│   ├── 📁 migrations/                # Database migrations
│   │   └── ...
│   │
│   ├── 📁 models/                    # Django models (database schema)
│   │   ├── __init__.py              # Model imports
│   │   ├── calendar.py              # Supervisor calendar & holidays
│   │   ├── class_section.py         # ClassSection model
│   │   ├── cluster.py               # Geographic/admin school clusters
│   │   ├── curriculum_sessions.py   # Detailed syllabus structure
│   │   ├── facilitator_task.py      # Facilitator-specific assignments
│   │   ├── facilitor_school.py      # Facilitator-School relationship
│   │   ├── school.py                # School model
│   │   ├── student_growth.py        # Growth analysis metrics
│   │   ├── student_performance.py   # Student assessment data
│   │   ├── students.py              # Student, Enrollment, Attendance models
│   │   └── users.py                 # Custom User and Role models
│   │
│   ├── 📁 services/                  # Business logic services
│   │   ├── student_growth_service.py # Growth analysis logic
│   │   ├── curriculum_content_resolver.py # Content mapping
│   │   └── facilitator_session_continuation.py # Session flow logic
│   │
│   ├── admin.py                     # Django admin configuration
│   ├── forms.py                     # Django forms
│   ├── query_optimizations.py       # Optimized DB query patterns
│   ├── urls.py                      # App URL patterns
│   ├── views.py                     # Common View functions
│   ├── facilitator_views.py         # Facilitator-specific logic
│   ├── supervisor_views.py          # Supervisor-specific logic
│   └── __init__.py
│
├── 📁 Templates/                     # HTML templates
│   ├── 📁 admin/                    # Admin interface (Tailwind CSS)
│   │   ├── 📁 feedback/             # Teacher/session feedback management
│   │   ├── 📁 reports/              # Advanced system reports
│   │   ├── 📁 sessions/             # Admin session monitoring
│   │   ├── dashboard.html           # Admin dashboard
│   │   └── ...                     # Schools, Classes, Students, Users
│   │
│   ├── 📁 facilitator/              # Facilitator interface (Bootstrap 5)
│   │   ├── dashboard.html           # Facilitator dashboard
│   │   ├── Today_session.html       # Today's session interface
│   │   ├── mark_attendance.html     # Attendance marking (Grouped/Simple)
│   │   ├── my_attendance.html       # Facilitator's own attendance record
│   │   ├── office_work.html         # Record administrative/office tasks
│   │   ├── curriculum_session.html  # Access to overall curriculum
│   │   └── ...                     # Classes, Students, Performance
│   │
│   ├── 📁 supervisor/               # Supervisor interface (Tailwind CSS)
│   │   ├── 📁 calendar/             # Holiday & session calendar management
│   │   ├── 📁 clusters/             # Geographic cluster management
│   │   ├── 📁 facilitators/         # Facilitator performance monitoring
│   │   ├── dashboard.html           # Supervisor dashboard
│   │   └── ...                     # Schools, Classes, Reports
│   │
│   ├── 📁 auth/                     # Authentication (Login, etc.)
│   └── offline.html                 # PWA Offline fallback page
│
├── 📁 static/                       # Static files (CSS, JS, images)
├── 📁 facilitator_tasks/            # Storage for task-related files
├── 📁 lesson_plans/                 # Storage for curriculum lesson plans
├── manage.py                        # Django management script
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

## 🗄️ Database Models

### Core Models

#### 👤 User & Role
- **User**: Custom user model with role-based permissions
- **Role**: Admin, Facilitator, Supervisor roles

#### 🏫 School Management
- **School**: Educational institutions
- **Cluster**: Geographic or administrative grouping of schools
- **ClassSection**: Classes within schools (e.g., "Class 5-A")
- **FacilitatorSchool**: Relationship between facilitators and schools

#### 👨‍🎓 Student Management
- **Student**: Student demographic information
- **Enrollment**: Links students to class sections and schools
- **StudentGrowthAnalysis**: Intelligent progress tracking and risk analysis
- **StudentPerformance**: Assessment and quiz data records

#### 📚 Session Management
- **PlannedSession**: Syllabus content (WHAT to teach)
- **ActualSession**: Execution records (WHEN it was taught)
- **CurriculumSession**: Higher-level curriculum unit mapping
- **SupervisorCalendar**: Management of session dates, holidays, and office work
- **OfficeWorkAttendance**: Tracking facilitator attendance for non-teaching tasks
- **Attendance**: Student attendance records per session

### Key Relationships
```
School → ClassSection → PlannedSession → ActualSession → Attendance
   ↓         ↓              ↓              ↓              ↓
FacilitatorSchool  Enrollment    (Content)    (Execution)  (Records)
```

## 🔄 Session Flow Logic

### 1. Planning Phase (Admin)
```
Admin creates PlannedSession:
- Day 1: Introduction to Math
- Day 2: Basic Addition  
- Day 3: Subtraction
- Day 4: Practice Problems
```

### 2. Execution Phase (Facilitator)
```
Facilitator sees "Today's Session": Day 1
Options:
- [Conduct Session] → Creates ActualSession(status="conducted") → Mark Attendance
- [Mark Holiday] → Creates ActualSession(status="holiday") → Skip to Day 2
- [Cancel] → Creates ActualSession(status="cancelled") → Skip to Day 2
```

### 3. Automatic Progression
```
System Logic:
- Find lowest day_number PlannedSession
- That has NO ActualSession record
- Show as "Today's Session"

Result: Content never skipped, dates are flexible
```

## 🚀 Key Features

### ✅ Cluster Management (New)
- **District/Block Organization**: Group schools by administrative regions
- **Geographic Mapping**: Map-based overview of clusters and schools
- **Centralized Monitoring**: Easier supervision of specific groups of schools

### ✅ Advanced Attendance System
- **Office Work Tracking**: Record and monitor non-teaching administrative attendance
- **Grouped Attendance**: Efficiency marking for combined or multi-part sessions
- **Facilitator History**: Facilitators can track their own session and office work history
- **Cascasding Filters**: Seamless school → class → student selection

### ✅ Supervisor Calendar & Holidays
- **Integrated Calendar**: Single view for sessions, holidays, and office work
- **Holiday Management**: Easy marking of regional or school-specific holidays
- **Session Scheduling**: Precise control over when content is delivered

### ✅ Intelligence & Reporting
- **Growth Analysis**: Automatic calculation of student progress trends
- **At-Risk Indicators**: Early warning system for low-performing students
- **Feedback Loop**: Comprehensive feedback system from facilitators and students
- **Excel/PDF Export**: Professional reports for schools and clusters

### ✅ Attendance System
- **Enhanced Filtering**: School → Class → Student cascading filters
- **Statistics Dashboard**: Attendance percentages and counts
- **Date-wise Tracking**: Session-by-session attendance records

### ✅ User Management
- **Role-based Access**: Different interfaces for different roles
- **School Assignments**: Facilitators assigned to specific schools
- **Permission Control**: Secure access to appropriate data only

### ✅ Data Management
- **CSV/Excel Import**: Bulk import of students and planned sessions
- **Export Capabilities**: Generate reports and data exports
- **Bulk Operations**: Manage multiple records efficiently

### ✅ Enhanced UI Features
- **Responsive Design**: Works on desktop and mobile
- **Real-time Updates**: AJAX-powered filtering and updates
- **Status Indicators**: Visual feedback for all system states
- **Debug Tools**: Built-in debugging for troubleshooting

## 🛠️ Technology Stack

### Backend
- **Django 5.1+**: Core web framework
- **PostgreSQL**: Production database (Neon serverless)
- **Redis & Cachalot**: Dual-layer caching for high performance
- **Python 3.13**: Programming language
- **Pandas & ReportLab**: Data processing and PDF generation

### Frontend
- **Tailwind CSS**: Modern utility-first styling (Admin & Supervisor)
- **Bootstrap 5**: Responsive layout framework (Facilitator)
- **Chart.js**: Dynamic data visualization
- **Service Workers**: PWA, local caching, and offline support
- **Vanilla JavaScript**: Interactive components and AJAX features

### Intelligence
- **Scikit-learn**: Progress prediction and risk analysis
- **NLTK**: Natural language processing for feedback analysis

### Development Tools

- **Git**: Version control
- **Virtual Environment**: Python dependency isolation

## 📦 Installation & Setup

### Prerequisites
- Python 3.13+
- PostgreSQL database
- Virtual environment

### Installation Steps

1. **Clone the repository**
```bash
git clone <repository-url>
cd CLAS
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure database**
- Update `CLAS/settings.py` with your database credentials
- Or use environment variables with `python-dotenv`

5. **Run migrations**
```bash
python manage.py migrate
```

6. **Create admin user**
```bash
python manage.py create_admin
```

7. **Run development server**
```bash
python manage.py runserver
```

8. **Access the application**
- Open http://127.0.0.1:8000
- Login with admin credentials

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the project root:
```env
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:password@host:port/database
```

### Database Configuration
The system supports PostgreSQL databases. Update `settings.py` or use environment variables for database connection.

## 📊 Usage Guide

### For Administrators
1. **Setup Schools & Clusters**: Create geographic clusters and educational institutions
2. **Add Users**: Create facilitator and supervisor accounts
3. **Assign Facilitators**: Link facilitators to specific schools and classes
4. **Monitor Feedback**: Review session-wise feedback from both students and teachers
5. **Analyze Reports**: Generate system-wide attendance and performance reports

### For Facilitators
1. **View Classes**: Access assigned schools and classes via the dashboard
2. **Execute Sessions**: Conduct the current planned session or handle exceptions (Holiday/Cancel)
3. **Mark Attendance**: Record student attendance (Grouped or Simple models)
4. **Record Office Work**: Track administrative tasks and non-classroom duties
5. **View Personal History**: Access a detailed log of your own attendance and sessions

### For Supervisors
1. **Monitor Clusters**: Oversight of multiple schools within an assigned geographic area
2. **Manage Calendar**: Set holidays and schedule sessions across the cluster
3. **Analyze Progress**: Review detailed student growth and facilitator performance trends
4. **Quality Assurance**: Audit actual sessions and identify irregularities

## 🔍 Troubleshooting

### Common Issues

#### "All sessions completed" showing incorrectly
- Use the debug tool: `/facilitator/class/{id}/debug/`
- Check if more planned sessions need to be added
- Verify session status in admin panel

#### Facilitator not seeing assigned schools
- Check FacilitatorSchool records in admin
- Verify `is_active=True` for assignments
- Ensure correct user role assignment

#### Import errors with CSV/Excel
- Use UTF-8 encoding for CSV files
- Download sample CSV from import page
- Check column headers match required format

### Debug Tools
- **Session Debug**: `/facilitator/class/{id}/debug/` - Shows all session statuses
- **Admin Messages**: Debug information appears in admin interface
- **Django Admin**: Direct database access for troubleshooting

## 🤝 Contributing

### Development Workflow
1. Create feature branch from main
2. Implement changes following Django best practices
3. Test thoroughly with different user roles
4. Update documentation as needed
5. Submit pull request with detailed description

### Code Standards
- Follow PEP 8 for Python code
- Use Django conventions for models, views, and templates
- Add comments for complex business logic
- Write tests for new features

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For support and questions:
- Check the troubleshooting section above
- Review the debug tools and error messages
- Contact the development team

## 🎯 Future Enhancements

### Planned Features
- **Mobile Application**: Native Android/iOS apps for facilitator offline usage
- **ML Recommendations**: Automated lesson plan suggestions based on class performance
- **Integration APIs**: RESTful APIs for integration with external ERP systems
- **Notification Engine**: Automated WhatsApp/Email alerts for low attendance
- **Multi-language Support**: Full internationalization for diverse regions

### Technical Improvements
- **Live Monitoring**: WebSocket integration for real-time attendance visualization
- **Advanced Caching**: Fine-tuned Redis/Cachalot strategies for high concurrent loads
- **Automated QA**: AI-driven detection of anomalous attendance patterns
- **Compliance Reporting**: Standardized government-format reporting tools

---

**CLAS** - Ensuring no learning content is ever lost, regardless of calendar disruptions.