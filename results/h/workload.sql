-- student_history; weight=30
SELECT e.term, c.code, e.grade
                   FROM enrollments AS e JOIN courses AS c ON c.id = e.course_id
                  WHERE e.student_id = ? AND e.term = ?
                  ORDER BY c.code;

-- course_roster; weight=25
SELECT s.id, s.last_name, e.grade
                   FROM enrollments AS e JOIN students AS s ON s.id = e.student_id
                  WHERE e.course_id = ? AND e.term = ?
                  ORDER BY s.last_name;

-- advisor_active_students; weight=20
SELECT id, last_name, campus
                   FROM students
                  WHERE advisor_id = ? AND status = ?
                  ORDER BY last_name;

-- department_term_gpa; weight=15
SELECT c.code, COUNT(*), ROUND(AVG(e.grade), 3)
                   FROM courses AS c JOIN enrollments AS e ON e.course_id = c.id
                  WHERE c.department_id = ? AND e.term = ?
                  GROUP BY c.id, c.code
                  ORDER BY c.code;

-- campus_at_risk; weight=10
SELECT s.campus, COUNT(*), ROUND(AVG(e.grade), 3)
                   FROM enrollments AS e JOIN students AS s ON s.id = e.student_id
                  WHERE e.term = ? AND e.grade < ? AND s.campus = ?
                  GROUP BY s.campus;
