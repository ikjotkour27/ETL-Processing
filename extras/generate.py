import random
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

days_info = [
    {"suffix": "130525", "emp_file": "emp_130525.csv", "hire_col": "hire_date"},
    {"suffix": "140525", "emp_file": "emp_140525.csv", "hire_col": "Hire_Date"},
    {"suffix": "150525", "emp_file": "emp_150525.csv", "hire_col": "Hire_Date"},
]

trainer_files = {
    "130525": "trainer_130525.csv",
    "140525": "trainer_140525.csv",
    "150525": "trainer_150525.csv",
}

INPUT_DIR = Path("input")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# weights: Enrolled 20%, In Progress 25%, Completed 35%, Cancelled 20%
status_options = ["Enrolled", "In Progress", "Completed", "Cancelled"]
status_weights = [0.20, 0.25, 0.35, 0.20]

assessment_methods = ["Hands-on", "Competency", "Applied Project Simulation", "Client Interview"]

skill_to_course = {
    "Programming - Python": "Python for Everybody",
    "Server Admin - Linux": "Linux Server Administration",
    "Data_Analysis - R": "R for Data Analysis",
    "Risk_Management": "Risk Management Fundamentals",
    "Recruitment - Sourcing": "Recruitment and Talent Sourcing",
    "Budgeting_Forecasting": "Budgeting and Forecasting",
    "Customer_Service - Email": "Customer Service Excellence",
    "Agile - Scrum": "Agile Scrum Master Training",
    "Tools - Selenium": "Selenium WebDriver Automation",
    "Digital_Marketing - SEO": "SEO Mastery Course",
    "Campaign_Management": "Campaign Management Essentials",
    "Bug_Tracking": "Bug Tracking and Issue Management",
    "Escalation_Management": "Escalation Management for Support Teams",
    "HRIS_Systems": "HRIS Systems Training",
    "Version Control - Git": "Git and Version Control Mastery",
    "Visualization - Tableau": "Tableau for Data Visualization",
    "Digital_Marketing - SEM": "SEM Strategy and Optimization",
    "Network Management": "Network Security Essentials",
    "Programming - Java": "Java Programming Masterclass",
    "Requirement_Gathering": "Business Analysis and Requirement Gathering",
    "Financial_Reporting": "Financial Reporting and Analysis",
    "CRM - Zendesk": "Zendesk Support Professional Training",
    "Ticketing_Systems": "Ticketing Systems and IT Support",
    "CRM - Salesforce": "Salesforce Service Cloud Training",
    "Accounting - Tally": "Tally ERP with GST",
    "Programming - JavaScript": "Modern JavaScript Bootcamp",
    "Security - Network": "Network Security Essentials",
    "Visualization - Power_BI": "Power BI for Business Analytics",
    "Data_Analysis - Python": "Data Analysis with Python",
    "Product_Roadmapping": "Product Roadmapping and Strategy",
    "Testing - Automation": "Selenium WebDriver Automation",
    "Software Architecture": "Software Architecture Fundamentals",
    "Competitive_Analysis": "Competitive Analysis for Product Teams",
    "Testing - Manual": "Manual Software Testing Essentials",
    "Compliance - ISO27001": "ISO 27001 Compliance Training",
    "Technical_Product_Knowledge": "Technical Product Management",
    "Payroll_Management": "Payroll Management Certification",
    "Customer_Service - Voice": "Voice and Accent Training for Support Roles",
    "Recruitment - Interviewing": "Interviewing Skills for Recruiters",
    "Cloud Platform - Azure": "Azure Cloud Fundamentals",
    "Compliance - GAAP": "GAAP Principles and Practices",
    "Server Admin - Windows": "Windows Server Administration",
    "Penetration_Testing": "Ethical Hacking and Penetration Testing",
    "Tools - JIRA": "JIRA Project Management Mastery",
    "Security - Application": "Application Security Foundations",
    "Data_Engineering - SQL": "SQL for Data Engineering",
    "Accounting - SAP_FICO": "SAP FICO Complete Training",
    "Employee_Engagement": "Employee Engagement Strategies",
    "Stakeholder_Management": "Stakeholder Management Mastery",
    "Cloud Platform - AWS": "Cloud Computing with AWS",
}

random.seed(42)


def parse_date(val):
    if pd.isna(val):
        return None
    if isinstance(val, (datetime, pd.Timestamp)):
        return val.date() if hasattr(val, "date") else val
    val = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


def random_date(start, end):
    if start is None or end is None:
        return datetime.today().date()
    if end < start:
        end = start
    return start + timedelta(days=random.randint(0, (end - start).days))


def to_str(d):
    return d.strftime("%Y-%m-%d") if d else ""


def enroll_course(cid, c, eid, hire_dt, trainer_map, enroll_rows, assess_rows, enroll_id, assess_id, today):
    c_start = c["course_start_date"]
    c_end = c["course_end_date"]

    e_start = max(hire_dt, c_start) if (hire_dt and c_start) else (hire_dt or c_start or today)
    e_end = min(c_end, today) if c_end else today
    if e_start is None:
        e_start = today
    e_date = random_date(e_start, e_end)

    trainers_list = trainer_map.get(cid, [])
    provider = random.choice(trainers_list) if trainers_list else "T0000"
    status = random.choices(status_options, status_weights)[0]

    enroll_rows.append({
        "enrollment_id": f"En{enroll_id:05d}",
        "Emp_ID": eid,
        "course_id": cid,
        "enrollment_date": to_str(e_date),
        "training_provider": provider,
        "course_status": status,
    })

    enroll_id += 1

    # only Completed gets an assessment
    # Enrolled -> just registered, not started yet
    # In Progress -> mid-course, no final assessment yet
    # Cancelled -> dropped, no assessment
    if status == "Completed":
        a_start = e_date + timedelta(days=1)
        a_end = e_date + timedelta(days=90)
        if a_end > today:
            a_end = today
        a_date = random_date(a_start, a_end)

        # realistic score spread across P1/P2/P3/P4 grade bands
        # P1: 85-100, P2: 70-84, P3: 55-69, P4: below 55
        score = random.choices(
            [random.randint(85, 100), random.randint(70, 84),
             random.randint(55, 69), random.randint(40, 54)],
            weights=[0.30, 0.35, 0.20, 0.15]
        )[0]

        assess_rows.append({
            "assessment_id": f"A{assess_id:04d}",
            "Emp_ID": eid,
            "course_id": cid,
            "score_prct": score,
            "method_of_assessment": random.choice(assessment_methods),
            "assessment_date": to_str(a_date),
        })
        assess_id += 1

    return enroll_id, assess_id


# load courses once
courses = pd.read_excel(INPUT_DIR / "course_130525.xlsx")
courses.columns = courses.columns.str.strip()
courses["course_start_date"] = courses["course_start_date"].apply(parse_date)
courses["course_end_date"] = courses["course_end_date"].apply(parse_date)

# build course name -> row lookup
course_by_name = {row["course_nm"]: row for _, row in courses.iterrows()}
course_by_id = {row["course_id"]: row for _, row in courses.iterrows()}

today = datetime.today().date()

enroll_id = 1
assess_id = 1

for day in days_info:
    suffix = day["suffix"]
    print(f"\ngenerating for {suffix}...")

    emp = pd.read_csv(INPUT_DIR / day["emp_file"])
    emp.columns = emp.columns.str.strip()
    emp["hire_date"] = emp[day["hire_col"]].apply(parse_date)

    skill_col = "primary_skill" if "primary_skill" in emp.columns else "Primary_Skill"

    trainers = pd.read_csv(INPUT_DIR / trainer_files[suffix])
    trainers.columns = trainers.columns.str.strip()
    trainer_map = trainers.groupby("course_id")["trainer_id"].apply(list).to_dict()

    enroll_rows = []
    assess_rows = []

    for _, row in emp.iterrows():
        eid = row["emp_id"]
        lvl = int(row["management_level"])
        hire_dt = row["hire_date"]
        skill = row[skill_col]

        enrolled_courses = set()

        # 1. enroll in skill-matched course first
        matched_course_nm = skill_to_course.get(skill)
        if matched_course_nm and matched_course_nm in course_by_name:
            c = course_by_name[matched_course_nm]
            cid = c["course_id"]
            if c["minimum_level"] <= lvl:
                enroll_id, assess_id = enroll_course(
                    cid, c, eid, hire_dt, trainer_map,
                    enroll_rows, assess_rows, enroll_id, assess_id, today
                )
                enrolled_courses.add(cid)

        # 2. add 0-2 more random eligible courses (excluding already enrolled)
        eligible = courses[
            (courses["minimum_level"] <= lvl) &
            (~courses["course_id"].isin(enrolled_courses))
        ]
        if not eligible.empty:
            n = random.randint(0, min(2, len(eligible)))
            extra = eligible.sample(n=n, random_state=None)
            for _, c in extra.iterrows():
                cid = c["course_id"]
                enroll_id, assess_id = enroll_course(
                    cid, c, eid, hire_dt, trainer_map,
                    enroll_rows, assess_rows, enroll_id, assess_id, today
                )
                enrolled_courses.add(cid)

    pd.DataFrame(enroll_rows).to_csv(OUTPUT_DIR / f"enrollment_{suffix}.csv", index=False)
    pd.DataFrame(assess_rows).to_csv(OUTPUT_DIR / f"assessment_{suffix}.csv", index=False)
    print(f"enrollment_{suffix}.csv -> {len(enroll_rows)} rows")
    print(f"assessment_{suffix}.csv -> {len(assess_rows)} rows")

print("\ndone")