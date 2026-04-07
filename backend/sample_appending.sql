/* 
This SQL file appends sample data points into the DB.
When user resets the DB, we delete from every relation.

However, we append sample data points so that we can practice manipulation.
*/

INSERT INTO department (dept_name, building, budget)
VALUES
    ('Biology', 'Watson', 90000.00),
    ('Comp. Sci.', 'Taylor', 100000.00),
    ('Elec. Eng.', 'Taylor', 85000.00),
    ('Finance', 'Painter', 120000.00),
    ('History', 'Painter', 50000.00),
    ('Music', 'Packard', 80000.00),
    ('Physics', 'Watson', 70000.00);

INSERT INTO course (course_id, title, dept_name, credits)
VALUES
    ('BIO-101', 'Intro. to Biology', 'Biology', 4),
    ('BIO-301', 'Genetics', 'Biology', 4),
    ('CS-101', 'Intro. to Computer Science', 'Comp. Sci.', 4),
    ('CS-190', 'Game Design', 'Comp. Sci.', 4),
    ('CS-315', 'Robotics', 'Comp. Sci.', 3),
    ('CS-319', 'Image Processing', 'Comp. Sci.', 3),
    ('EE-181', 'Intro. to Digital Systems', 'Elec. Eng.', 3),
    ('FIN-201', 'Investment Banking', 'Finance', 3),
    ('HIS-101', 'World History', 'History', 3),
    ('MU-199', 'Music Video Production', 'Music', 3),
    ('PHY-101', 'Physical Principles', 'Physics', 4);

INSERT INTO instructor (ID, name, dept_name, salary)
VALUES
    ('10101', 'Srinivasan', 'Comp. Sci.', 65000.00),
    ('12121', 'Wu', 'Finance', 90000.00),
    ('15151', 'Mozart', 'Music', 40000.00),
    ('22222', 'Einstein', 'Physics', 95000.00),
    ('32343', 'El Said', 'History', 60000.00),
    ('33456', 'Gold', 'Physics', 87000.00),
    ('45565', 'Katz', 'Comp. Sci.', 75000.00),
    ('58583', 'Califieri', 'History', 62000.00),
    ('76543', 'Singh', 'Finance', 80000.00),
    ('76766', 'Crick', 'Biology', 72000.00),
    ('83821', 'Brandt', 'Comp. Sci.', 92000.00),
    ('98345', 'Kim', 'Elec. Eng.', 80000.00);

INSERT INTO section (course_id, sec_id, semester, year, building, room_number, time_slot_id)
VALUES
    ('BIO-101', '1', 'Summer', 2017, 'Painter', '514', 'B'),
    ('BIO-301', '1', 'Summer', 2018, 'Painter', '514', 'A'),
    ('CS-101', '1', 'Fall', 2017, 'Packard', '101', 'H'),
    ('CS-101', '1', 'Spring', 2018, 'Packard', '101', 'F'),
    ('CS-190', '1', 'Spring', 2017, 'Taylor', '3128', 'E'),
    ('CS-190', '2', 'Spring', 2017, 'Taylor', '3128', 'A'),
    ('CS-315', '1', 'Spring', 2018, 'Watson', '120', 'D'),
    ('CS-319', '1', 'Spring', 2018, 'Watson', '100', 'B'),
    ('EE-181', '1', 'Spring', 2017, 'Taylor', '3128', 'C'),
    ('FIN-201', '1', 'Spring', 2018, 'Packard', '101', 'B'),
    ('HIS-101', '1', 'Fall', 2017, 'Painter', '514', 'C'),
    ('MU-199', '1', 'Spring', 2018, 'Packard', '101', 'D'),
    ('PHY-101', '1', 'Fall', 2017, 'Watson', '100', 'A');

INSERT INTO teaches (ID, course_id, sec_id, semester, year)
VALUES
    ('76766', 'BIO-101', '1', 'Summer', 2017),
    ('76766', 'BIO-301', '1', 'Summer', 2018),
    ('83821', 'CS-101', '1', 'Fall', 2017),
    ('83821', 'CS-101', '1', 'Spring', 2018),
    ('10101', 'CS-190', '1', 'Spring', 2017),
    ('10101', 'CS-190', '2', 'Spring', 2017),
    ('45565', 'CS-315', '1', 'Spring', 2018),
    ('45565', 'CS-319', '1', 'Spring', 2018),
    ('98345', 'EE-181', '1', 'Spring', 2017),
    ('12121', 'FIN-201', '1', 'Spring', 2018),
    ('32343', 'HIS-101', '1', 'Fall', 2017),
    ('15151', 'MU-199', '1', 'Spring', 2018),
    ('22222', 'PHY-101', '1', 'Fall', 2017);
