# RVS Application - Comprehensive Documentation
**Report Generated:** January 15, 2026

---

## 📋 Executive Summary

The **RVS (Registered Vital Statistics) Application** is a comprehensive desktop application for managing, searching, and verifying vital records (Birth, Death, and Marriage certificates). It's built as a **PyQt6/PySide6** desktop application with a **PostgreSQL backend** and a **Flask microservice** for external verification (eVerify) integration. The application is designed for use in Local Government Units (LGUs) and includes features for document digitization, record tagging, user management, and comprehensive audit logging.

**Application Name:** OCCR RVS (Office of Civil Registry - Registered Vital Statistics)  
**Technology Stack:** Python 3.x, PySide6, PostgreSQL, Flask, OpenCV, PyInstaller  
**Current Version:** 2.2.1+ (as of June 2025)

---

## 🏗️ Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    RVS Desktop Application (PySide6)             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────┐  ┌──────────────┐  ┌─────────────────┐    │
│  │  Login Dialog   │  │ Main Window  │  │  Menu System    │    │
│  └─────────────────┘  └──────────────┘  └─────────────────┘    │
│           │                  │                    │              │
│           └──────────────────┴────────────────────┘              │
│                              │                                   │
│  ┌────────────┬──────────────┼────────────┬──────────────────┐  │
│  │            │              │            │                  │  │
│  ▼            ▼              ▼            ▼                  ▼  │
│ Search   Verify      Tagging Tool   Release Docs      Statistics
│ Records  Records     (Birth/Death/   (Handover)       (Analytics)
│ (Birth/  (Birth/     Marriage)                        (Charts &
│  Death/   Death/                                       Reports)
│  Marr)   Marr)
│  │        │              │                 │              │
│  ├────────┼──────────────┼─────────────────┼──────────────┤
│  │                       │                 │              │
│  └──────────────────┬────┴─────────────────┴──────────────┘
│                     │
│    ┌────────────────┼────────────────┐
│    │                │                │
│    ▼                ▼                ▼
│ Auto Form      HTML Renderer    PDF Viewer
│ Generation     & Display        & Printing
│    │                │                │
│    └────────────────┼────────────────┘
│                     │
│      ┌──────────────┴──────────────┐
│      │                             │
│      ▼                             ▼
│   QR Scanner              Flask Server (Port 5000)
│   (Face Capture)               │
│                                ▼
│                        eVerify Integration
│                    (External Verification API)
│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────────┐
                    │  PostgreSQL Database │
                    │  (rvs_dbase)         │
                    └──────────────────────┘
```

---

## 📁 Project Structure

### Root Level Files

#### Core Application Files
- **app.py** (1617 lines) - Main application entry point
  - Initializes PySide6 GUI
  - Manages login dialog and authentication
  - Creates main window and handles user sessions
  - Manages window navigation and signal connections
  - Loads and starts Flask server in daemon thread
  
- **MainWindow.py** (128 lines) - Main UI definition (auto-generated from Qt Designer)
  - Menu bar with user, search, tools, release, and eVerify menus
  - Central widget with RVS logo display
  - Status bar for application status

#### Database Configuration
- **db_config.py** - PostgreSQL connection settings
  ```python
  POSTGRES_CONFIG = {
      'dbname': 'rvs_dbase',
      'user': 'postgres',
      'password': '***',
      'host': '192.168.254.108',
      'port': '5432'
  }
  ```

- **create_db_tables.py** - Database initialization script
- **create_tables.sql** - SQL schema definition for all database tables

#### Requirements
- **requirements.txt** - Python package dependencies
  - Core: PySide6, psycopg2-binary, Flask
  - Data Processing: numpy, pandas, matplotlib, reportlab
  - Image Processing: opencv-python, Pillow, PyMuPDF
  - QR Code: pyzbar
  - Web/API: requests, Flask-JWT-Extended, PyJWT
  - Deployment: pyinstaller

---

### 🔑 Key Feature Modules

#### 1. **User Authentication & Management**
- **Login_Dialog.py** - Login dialog with username/password
- **manage_users.py** (660 lines) - User management interface
  - Create/Edit/Delete user accounts
  - Superuser role management
  - Password management
  - User table display and filtering
  
- **Manage_User_Widget.py** - UI definition for user management

#### 2. **Search & Retrieval System**
- **search.py** (665 lines) - Search for vital records
  - **SearchWindowBase** - Base class for search windows
  - **SearchBirthWindow** - Search birth records
  - **SearchDeathWindow** - Search death records
  - **SearchMarriageWindow** - Search marriage records
  - Features:
    - Full-text search by multiple fields
    - PDF preview and navigation
    - Form creation from search results
    - eVerify integration
    - Audit logging for all searches

#### 3. **Record Verification**
- **verify.py** (1228 lines) - Verification workflows
  - **VerifyWindowBase** - Base for verification windows
  - **VerifyBirthWindow**, **VerifyDeathWindow**, **VerifyMarriageWindow**
  - Features:
    - Create official certification forms
    - Mark records as "No Record Found" or "Destroyed"
    - eVerify online verification
    - Print and save certification forms
    - Remarks and notes management

#### 4. **Automated Form Generation & Preview**
- **auto_form.py** (727 lines) - Automatic form population
  - **FormPreviewWindow** - Display and customize forms
  - Auto-fill form fields from database records
  - Field positioning and sizing for each form type
  - Remarks text editing
  - Print functionality with custom CSS removal
  - Save and formatting utilities

#### 5. **Record Tagging & Indexing**
- **tagging_main.py** (133 lines) - Tagging menu selection
- **tagging_birth.py** - Birth record tagging
- **tagging_death.py** - Death record tagging
- **tagging_marriage.py** - Marriage record tagging
- Features:
  - Extract and tag vital information from PDFs
  - Populate database indexes (birth_index, death_index, marriage_index)
  - Batch tagging operations

#### 6. **Document Release & Handover**
- **releasing_docs.py** (334 lines) - Release document management
  - Record document owner information
  - Track release date and released-by user
  - Generate release receipts
  - Audit trail for all releases

- **releasing_log_viewer.py** - View released documents
  - Display release history
  - Export to PDF
  - Date range filtering

#### 7. **eVerify Integration**
- **everify_form.py** (996 lines) - Online verification system
  - QR code scanning
  - Face liveness detection
  - PSA (Philippine Statistics Authority) integration
  - JWT-based authentication
  - Secure API communication
  
- **qr_scanner_window.py** (108 lines) - QR code scanning
  - Real-time video feed using OpenCV
  - QR code detection and decoding
  - Focus box visualization
  - Image preprocessing for better detection

#### 8. **Statistics & Analytics**
- **stats.py** (1012 lines) - Statistical analysis and reporting
  - Generate statistical reports from database
  - Export to PDF using ReportLab
  - Support for multiple report types:
    - Birth statistics
    - Death statistics
    - Marriage statistics
  - Date range filtering
  - Field-based analysis

#### 9. **Audit Logging & Monitoring**
- **audit_logger.py** (96 lines) - Comprehensive audit trail
  - PostgreSQL-backed logging
  - Retry logic with exponential backoff
  - User action tracking
  - Username validation
  - System actions logging
  
- **audit_log_viewer.py** - View audit trails
  - Display all system actions
  - Filter by user/date/action
  - Export audit logs to PDF

#### 10. **PDF Handling**
- **pdfviewer.py** (124 lines) - PDF viewing
  - Render PDF pages as images
  - Zoom functionality
  - Landscape optimization
  - Navigation between pages
  
- **book_viewer.py** - Book-style document viewer
  - Multi-page document display
  - Page navigation

#### 11. **HTML Forms & Rendering**
- **html_renderer.py** (166 lines) - HTML to PDF conversion
  - Jinja2 templating support
  - Field mapping and substitution
  - Temporary file generation
  - Browser-based preview
  
- **html_field_map.py** - Field mapping for HTML templates
  - Database field ↔ HTML template field mapping
  - Context building for Jinja2

- **html_forms/** - HTML template files
  - `form1a.html` - Birth Certificate
  - `form2a.html` - Death Certificate
  - `form3a.html` - Marriage Certificate

#### 12. **UI & Styling**
- **stylesheets.py** - Centralized stylesheet definitions
  - Custom button styles (pink/maroon theme: #ce305e)
  - Input field styling
  - Table widget styling
  - Message box styling
  - Consistent color scheme across app

#### 13. **Flask Microservice**
- **flask_server/app.py** (419 lines) - Backend API server
  - Runs on port 5000 in daemon thread
  - eVerify authentication and token management
  - JWT-based access control
  - Handles:
    - `/verify` - Verification endpoints
    - Face liveness checking
    - QR data processing
    - Token refresh and validation
  - Integrates with PSA eVerify system
  - Logging to `everify_server.log`

---

### 📊 Database Schema

The application uses PostgreSQL with the following main tables:

#### Core Record Tables
1. **birth_index**
   - Fields: name, date_of_birth, sex, place_of_birth, name_of_mother/father, attendant, late_registration, type_of_birth, file_path, remarks

2. **death_index**
   - Fields: name, date_of_death, sex, age (years/months/days/hours/mins), civil_status, nationality, place_of_death, cause_of_death, corpse_disposal, file_path, remarks

3. **marriage_index**
   - Fields: husband_name, wife_name, date_of_marriage, husband/wife age, civil_status, nationality, place_of_marriage, ceremony_type, file_path, remarks

#### System Tables
1. **users_list**
   - Fields: username, password, firstname, lastname, is_superuser
   - Used for authentication and authorization

2. **audit_log**
   - Fields: id, username, action, details, timestamp
   - Tracks all user actions for compliance

3. **releasing_log**
   - Fields: document_owner, released_by, release_date, receipt_info, timestamp
   - Records all document releases

4. **searchable_records**
   - Records the status of searches and verifications

---

## 🔄 Key Workflows

### 1. User Login Flow
```
Start → Login Dialog → Authenticate PostgreSQL → 
Load User Info (superuser status) → Main Window → 
Populate Menu Based on Permissions → Application Ready
```

### 2. Search & Verify Workflow
```
Search Window → Query Database → Display Results → 
Select Record → Auto-Form (populate fields) → 
FormPreviewWindow (customize) → Print/Save/eVerify → 
Log Action (Audit) → Release Document
```

### 3. Tagging Workflow
```
PDF Upload → TaggingWindow → Extract Data → 
Form Field Entry → Save to Database (Index) → 
Update searchable_records → Log Action
```

### 4. eVerify Workflow
```
QR Scan → Face Liveness Check → API Call to PSA → 
Get Verification Status → Update Record → 
Generate Certificate → Save & Log
```

### 5. Statistics & Reporting
```
Statistics Tool → Select Report Type → Choose Date Range → 
Query Database → Generate Charts/Tables → Export PDF
```

---

## 🛡️ Security Features

1. **Authentication**
   - PostgreSQL user table with hashed passwords
   - Login dialog validation
   - Session management with username tracking

2. **Authorization**
   - Superuser role management
   - Permission-based menu options
   - Role-based access control (RBAC)

3. **Audit Trail**
   - Comprehensive logging of all actions
   - User attribution for every action
   - PostgreSQL-backed for persistence
   - Retry logic for reliability

4. **Data Protection**
   - PostgreSQL for secure data storage
   - Network isolation (192.168.254.108)
   - Password protection in config files
   - JWT for API authentication (eVerify)
   - SSL/TLS support in Flask server

5. **API Security**
   - JWT tokens with expiration
   - Token refresh mechanisms
   - Client ID/Secret for OAuth-like flow
   - Request validation and logging

---

## 🎨 User Interface

### Theme & Styling
- **Primary Color:** Maroon (#ce305e) - Used for buttons and selected items
- **Secondary Color:** Pink (#e0446a) - Hover states
- **Background:** White (#FFFFFF) - Clean, professional
- **Text:** Dark gray (#212121) - Good contrast
- **Borders:** Light gray (#D1D0D0) - Subtle separation
- **Alternate:** Light gray (#F2F2F2) - Table backgrounds

### Main Menu Structure
```
Menu Bar (Right-to-Left Layout)
├── User Menu
│   ├── Manage Users (Superuser only)
│   ├── Change Password
│   └── Logout
├── Search Menu
│   ├── Search Birth Records
│   ├── Search Death Records
│   └── Search Marriage Records
├── Tools Menu
│   ├── Tagging Tool
│   ├── QR Scanner
│   └── Statistics
├── Release Menu
│   ├── Release Document
│   └── View Release Log
└── eVerify Menu
    └── eVerify Verification
```

### Window Management
- Modal dialogs for login and utility windows
- Fixed size windows for consistency
- Maximizable windows for tagging tools
- Centralized window management from main window
- User session passed to all child windows

---

## 📦 Deployment & Packaging

### PyInstaller Configuration (app.spec)
- **Executable Name:** OCCR RVS
- **Console:** Disabled (GUI only)
- **Icon:** icons/RVS-icon.ico
- **Binaries:** Includes pyzbar DLLs (libzbar-64.dll, libiconv.dll)
- **Data Files:** All resources bundled
  - flask_server directory
  - forms, html_forms, templates
  - icons, images, logos
  - Python source files
  - .env file for API keys

### Build Output
- Located in `build/app/` directory
- Standalone executable: `dist/app/OCCR RVS.exe`
- Current version: 2.2.1+ (as of June 2025)

---

## 🔧 Development Stack

### Python Libraries (Key Dependencies)
- **GUI:** PySide6 v6.10.1
- **Database:** psycopg2-binary v2.9.10
- **Web:** Flask v3.1.2, Flask-JWT-Extended
- **PDF:** PyMuPDF v1.26.4, ReportLab v4.4.4
- **Image Processing:** OpenCV v4.12.0, Pillow v11.3.0
- **QR Code:** pyzbar v0.1.9
- **Data:** numpy v2.2.6, matplotlib v3.10.7
- **Utilities:** requests v2.32.5, python-dotenv v1.1.1
- **Testing:** pytest v9.0.2
- **Packaging:** PyInstaller v6.17.0

### Database Server
- PostgreSQL v13+ (running on 192.168.254.108:5432)

### Development Environment
- Python 3.x
- Virtual environment (.venv)
- Git for version control

---

## 📋 Recent Updates & Development Timeline

### June 2025 Milestones
- **June 3:** Fixed IP address errors
- **June 4:** Created database indexes (birth_index, death_index, marriage_index)
- **June 5:** Created demo version
- **June 6:** Imported updated database with final schema
- **June 9:** Packaged v2.2.1 with city seal and office logo
- **June 10:** Completed tagging functionality for all record types
- **June 11:** Created book record search windows, started auto-form
- **June 13:** Completed FormPreviewWindow module
- **June 16-18:** Finalized form field layouts and positions
- **June 18:** Added auto-logging and user attribution

### Earlier Milestones (May 2025)
- **May 14-16:** Migrated from SQLite to PostgreSQL for all databases
- **May 20:** Fixed eVerify connection issues
- **May 26:** Updated color scheme to neutral palette
- **May 26:** Created .env file for API key security
- **May 27-28:** Finalized UI design and setup static IP

---

## 🐛 Known Issues & Areas for Improvement

1. **Database Constraints** - Some SQL table creation code is commented out, may need review
2. **Import Organization** - Could benefit from modular organization
3. **Error Handling** - Some modules have basic error handling, could be enhanced
4. **Testing** - Minimal unit test coverage (only test_*.py files exist)
5. **Documentation** - Inline code documentation could be more comprehensive

---

## 📝 File Manifest

### Python Modules (35+ files)
| File | Lines | Purpose |
|------|-------|---------|
| app.py | 1617 | Main application |
| MainWindow.py | 128 | Main UI |
| verify.py | 1228 | Verification workflows |
| auto_form.py | 727 | Auto form generation |
| manage_users.py | 660 | User management |
| search.py | 665 | Record search |
| stats.py | 1012 | Statistics |
| everify_form.py | 996 | eVerify integration |
| flask_server/app.py | 419 | Backend API |
| releasing_docs.py | 334 | Document release |
| pdfviewer.py | 124 | PDF viewing |
| tagging_main.py | 133 | Tagging menu |
| audit_logger.py | 96 | Audit logging |
| qr_scanner_window.py | 108 | QR scanning |
| html_renderer.py | 166 | HTML rendering |
| + 20+ more supporting modules | - | UI, dialogs, utilities |

### UI Files (8 .ui files)
- logindialog.ui
- mainwindow.ui
- manageuserwidget.ui
- recordstatusform.ui
- searchbirthwindow.ui
- searchdeathwindow.ui
- searchmarriagewindow.ui

### Resource Directories
- **icons/** - Application icons and images
- **images/faces/** - Face capture storage
- **logos/** - Office and city seal logos
- **html_forms/** - HTML templates for forms
- **templates/** - Jinja2 template files
- **forms/** - Form definitions
- **ui/** - Qt Designer UI files

### Database Scripts (dbase_scripts/)
- Migration scripts for PostgreSQL conversion
- Column addition scripts
- Superuser management
- Audit database initialization

### Configuration Files
- db_config.py - Database connection
- stylesheets.py - UI styling
- app.spec - PyInstaller spec
- requirements.txt - Python dependencies
- .env - API keys and secrets

---

## 🚀 Getting Started (For Developers)

### Prerequisites
1. Python 3.8+
2. PostgreSQL server (configured at 192.168.254.108)
3. Virtual environment

### Installation
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run application
python app.py
```

### Building Executable
```bash
# Build with PyInstaller
pyinstaller app.spec

# Executable location
dist/app/OCCR RVS.exe
```

---

## 📞 Support & Maintenance

### Key Contact Points
- Database Admin: PostgreSQL maintenance on 192.168.254.108
- API Keys: Stored in .env file
- Logs: everify_server.log for API issues

### Regular Maintenance
- Monitor PostgreSQL performance
- Archive old audit logs
- Update eVerify API credentials
- Review release logs monthly

---

## 📚 Additional Resources

### Documentation Files (in docs/)
- HTML_FORM_PREVIEW_IMPLEMENTATION.md
- html_render_decision.md
- LOGO_PATH_FIX.md
- updates.md (detailed changelog)

### Database Backups
- PostgreSQL dump: postgres_backup/rvs_dbase_backup.dump
- SQLite backup: sqlite_backups/users.db.backup_20250516_094812

---

## 📊 Application Statistics

| Metric | Value |
|--------|-------|
| Total Python Lines of Code | 10,000+ |
| Main Modules | 35+ |
| Database Tables | 7+ |
| UI Dialog Windows | 8+ |
| Feature Modules | 13+ |
| Resource Files | 100+ |
| Current Version | 2.2.1+ |

---

## 🎯 Core Features Summary

✅ **Record Management**
- Search vital records (Birth, Death, Marriage)
- View record details
- Generate certificates
- Add remarks and notes

✅ **Verification**
- Online eVerify integration
- QR code scanning
- Face liveness detection
- Batch verification

✅ **Document Management**
- Auto-form generation
- PDF viewing and printing
- Document release tracking
- Receipt generation

✅ **Data Entry**
- Automated field tagging
- Record indexing
- Database population
- Validation

✅ **Administration**
- User account management
- Role-based access control
- Comprehensive audit logging
- Statistical reporting

✅ **Security**
- Authentication and authorization
- Audit trail for compliance
- PostgreSQL encryption
- API authentication (JWT)

---

**End of Documentation**

*For technical support or updates, refer to the development team or check the `docs/` directory for implementation details.*
