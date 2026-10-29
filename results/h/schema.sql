CREATE TABLE departments (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE students (
    id INTEGER PRIMARY KEY,
    department_id INTEGER NOT NULL REFERENCES departments(id),
    advisor_id INTEGER NOT NULL,
    campus TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'leave', 'graduated')),
    entry_year INTEGER NOT NULL,
    last_name TEXT NOT NULL
);
CREATE TABLE courses (
    id INTEGER PRIMARY KEY,
    department_id INTEGER NOT NULL REFERENCES departments(id),
    code TEXT NOT NULL UNIQUE,
    credits INTEGER NOT NULL
);
CREATE TABLE enrollments (
    id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id),
    course_id INTEGER NOT NULL REFERENCES courses(id),
    term TEXT NOT NULL,
    grade REAL NOT NULL,
    completed INTEGER NOT NULL,
    enrolled_at TEXT NOT NULL
);
