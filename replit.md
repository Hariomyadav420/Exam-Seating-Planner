# Exam Seating Plan Generator

## Overview

The Exam Seating Plan Generator is a Flask-based web application designed to automate the allocation of students to exam seats while implementing anti-cheating measures. The system manages student data, room configurations, and generates seating allocations that separate students taking the same subject by at least two seats. It provides admit cards with QR codes, Excel exports of seating plans, and role-based interfaces for administrators, students, and invigilators.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Application Framework
- **Web Framework**: Flask serves as the core web framework, handling routing, request processing, and template rendering
- **Template Engine**: Jinja2 templates with Bootstrap 5 for responsive UI components
- **Session Management**: Flask sessions for maintaining user state across requests

### Data Storage
- **Database**: SQLite for serverless, file-based data persistence
- **Schema Design**: 
  - Students table: Stores student information (roll_no, name, course, semester, email, subject_code)
  - Rooms table: Stores room configurations (room_no, building, rows, columns, capacity)
  - Seating allocations table: Maps students to specific seats with allocation method tracking
  - Activity logs table: Tracks system operations for audit purposes
- **Data Access**: Direct SQLite connections with row factory for dictionary-like result access

### Seating Allocation Engine
- **Primary Algorithm**: Anti-cheating allocation that groups students by subject code and ensures minimum 2-seat separation between students with identical subjects
- **Secondary Algorithm**: Roll-wise sequential allocation as a fallback option
- **Allocation Strategy**: 
  - Students sorted by subject code and roll number
  - Room seats generated as a flat list with row/column coordinates
  - Constraint validation to maintain separation requirements
  - Random placement with separation enforcement

### File Processing
- **Upload Handling**: Support for CSV, XLSX, and XLS formats with 16MB file size limit
- **Data Validation**: 
  - Duplicate roll number detection
  - Capacity verification (total students vs. available seats)
  - Column presence validation for required fields
- **File Storage**: Temporary storage in uploads/ directory with secure filename generation

### Document Generation
- **PDF Generation**: ReportLab library for creating admit cards
  - Individual cards per student with allocation details
  - QR code generation using qrcode library encoding roll number and seat information
  - A4/Letter page size support
- **Excel Export**: Pandas DataFrames converted to Excel format for seating plan distribution
- **Export Storage**: Generated files stored in exports/ directory

### User Interfaces
- **Admin Dashboard**: 
  - File upload forms for students and rooms data
  - Statistics display (student count, room count, allocation count, utilization percentage)
  - Allocation trigger controls
  - Data clearing functionality
- **Student Portal**: 
  - Roll number search interface
  - Seat allocation display
  - Downloadable admit card access
- **Invigilator Panel**:
  - Room selection dropdown
  - Visual seat map display showing allocation status
  - Room-specific student list export
  - Real-time allocation information

### API Architecture
- **RESTful Endpoints**:
  - `/api/upload_students` - POST endpoint for student data upload
  - `/api/upload_rooms` - POST endpoint for room data upload
  - `/api/allocate` - POST endpoint triggering allocation algorithms
  - `/api/student/<roll_no>` - GET endpoint for student allocation lookup
  - `/api/room/<room_no>` - GET endpoint for room-specific data
- **Response Format**: JSON responses with success/error status and descriptive messages
- **Error Handling**: Try-catch blocks with user-friendly error messages

### Frontend Architecture
- **CSS Framework**: Bootstrap 5 for responsive grid layout and pre-built components
- **Icons**: Bootstrap Icons for UI visual elements
- **JavaScript**:
  - Vanilla JS for API interactions via fetch()
  - Dynamic DOM manipulation for real-time updates
  - Chart.js for utilization visualization
  - Form validation and user feedback mechanisms

### Security Considerations
- **Session Secret**: Environment variable-based secret key (SESSION_SECRET) with fallback for development
- **File Upload Security**: 
  - Werkzeug secure_filename() for safe file naming
  - File extension whitelist validation
  - Size limit enforcement
- **Database Security**: Parameterized queries to prevent SQL injection
- **Input Sanitization**: String conversion and validation for user inputs

### Configuration Management
- **Environment Variables**: SESSION_SECRET for production deployment
- **File Paths**: Configurable upload and export directories
- **Database Location**: exam_seating.db in application root directory
- **Static Assets**: Served from static/ directory with CSS and JS subdirectories

## External Dependencies

### Python Libraries
- **Flask**: Web application framework and routing
- **Pandas**: Excel/CSV file processing and DataFrame operations
- **ReportLab**: PDF document generation for admit cards
- **qrcode**: QR code image generation
- **Werkzeug**: File upload utilities and security helpers
- **sqlite3**: Database connectivity (Python standard library)

### Frontend Libraries (CDN)
- **Bootstrap 5.3.0**: UI component framework and responsive grid
- **Bootstrap Icons 1.10.0**: Icon set for visual elements
- **Chart.js 4.4.0**: Data visualization for utilization charts

### File Format Support
- **openpyxl** (implied): Excel file reading/writing via Pandas
- **xlrd** (implied): Legacy Excel format support

### Database
- **SQLite**: Embedded relational database, no external server required
- **Connection Pattern**: Context-managed connections with row factory for dict-like access

### Storage Requirements
- **uploads/**: Temporary storage for uploaded CSV/Excel files
- **exports/**: Storage for generated PDF admit cards and Excel exports
- **exam_seating.db**: SQLite database file containing all persistent data