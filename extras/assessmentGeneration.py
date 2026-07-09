import random
from datetime import datetime, timedelta
import pandas as pd
NUM_TRAINERS = 600
NUM_ASSESSMENTS = 1500
 
DEPARTMENTS = {
    'IT Support': ['Networking', 'Technical Troubleshooting', 'System Administration', 'Security Protocols'],
    'Sales': ['Sales Techniques', 'CRM', 'Lead Generation', 'Product Knowledge'],
    'Marketing': ['SEO', 'Digital Marketing', 'Content Creation', 'Branding'],
    'HR': ['Recruitment', 'Employee Relations', 'Payroll Management', 'Training & Development']
}
 
def generate_random_date(start_date, end_date):
    delta_days = (end_date - start_date).days
    if delta_days < 0:
        return start_date
    random_days = random.randint(0, delta_days)
    return start_date + timedelta(days=random_days)
 
def generate_trainers(employees, courses):
    trainers = []
    for _ in range(NUM_TRAINERS):
        trainer_employee = random.choice(employees)
        trainer_course = random.choice(courses)
        start_date = generate_random_date(trainer_employee['hire_date'], datetime.today().date() - timedelta(days=60))
        end_date = generate_random_date(start_date, min(start_date + timedelta(days=60), datetime.today().date()))
        trainers.append({
            'employee_id': trainer_employee['employee_id'],
            'course_id': trainer_course['course_id'],
            'start_date': start_date,
            'end_date': end_date,
        })
    return trainers
 
def generate_assessments(employees, courses):
    assessments = []
    assessment_id = 1
    course_end_dates = {}
 
    while len(assessments) < NUM_ASSESSMENTS:
        employee = random.choice(employees)
        department_courses = [
            course for course in courses
            if any(skill in DEPARTMENTS[employee['department']] for skill in course['skills'])
        ]
        if not department_courses:
            continue
        course = random.choice(department_courses)
        emp_id = employee['employee_id']
        course_id = course['course_id']
 
        # Simulate a course period (within 60 days from hire)
        start_date = generate_random_date(employee['hire_date'], datetime.today().date() - timedelta(days=60))
        end_date = generate_random_date(start_date, min(start_date + timedelta(days=60), datetime.today().date()))
        key = (emp_id, course_id)
        course_end_dates[key] = end_date
 
        score = random.randint(50, 100)
        assessment_type = random.choice(['Final Assessment', 'Quiz'])
 
        if assessment_type == 'Quiz':
            assessment_date = generate_random_date(end_date, end_date + timedelta(days=5))
 
        else:
            # Find prior quiz for same employee-course
            prior_quiz = next(
                (a for a in reversed(assessments)
                 if a['employee_id'] == emp_id
                 and a['course_id'] == course_id
                 and a['assessment_type'] == 'Quiz'),
                None
            )
            quiz_date = prior_quiz['assessment_date'] if prior_quiz else end_date
            assessment_date = generate_random_date(quiz_date + timedelta(days=1), quiz_date + timedelta(days=10))
 
 
        assessments.append({
            'assessment_id': assessment_id,
            'employee_id': emp_id,
            'course_id': course_id,
            'score': score,
            'assessment_type': assessment_type,
            'assessment_date': assessment_date,
        })
        assessment_id += 1
 
    return assessments