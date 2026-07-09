import random
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# file inputs
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

status_options = ["Enrolled", "In Progress", "Completed", "Cancelled"]
status_weights = [0.25, 0.22, 0.25, 0.28]

assessment_methods = ["Hands-on", "Competency", "Applied Project Simulation", "Client Interview"]

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


# load courses once, used for all 3 days
courses = pd.read_excel(INPUT_DIR / "course_130525.xlsx")
courses.columns = courses.columns.str.strip()
courses["course_start_date"] = courses["course_start_date"].apply(parse_date)
courses["course_end_date"] = courses["course_end_date"].apply(parse_date)

today = datetime.today().date()

# counters carry over across all 3 days
enroll_id = 1
assess_id = 1

for day in days_info:
    suffix = day["suffix"]
    print(f"\ngenerating for {suffix}...")

    emp = pd.read_csv(INPUT_DIR / day["emp_file"])
    emp.columns = emp.columns.str.strip()
    emp["hire_date"] = emp[day["hire_col"]].apply(parse_date)

    trainers = pd.read_csv(INPUT_DIR / trainer_files[suffix])
    trainers.columns = trainers.columns.str.strip()
    # trainer lookup by course
    trainer_map = trainers.groupby("course_id")["trainer_id"].apply(list).to_dict()

    enroll_rows = []
    assess_rows = []

    for _, row in emp.iterrows():
        eid = row["emp_id"]
        lvl = int(row["management_level"])
        hire_dt = row["hire_date"]

        eligible = courses[courses["minimum_level"] <= lvl]
        if eligible.empty:
            continue

        # pick 1 to 3 courses randomly
        n = random.randint(1, min(3, len(eligible)))
        picked = eligible.sample(n=n, random_state=None)

        for _, c in picked.iterrows():
            cid = c["course_id"]
            c_start = c["course_start_date"]
            c_end = c["course_end_date"]

            # enrollment date should be after hire and within course window
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

            # assessment date is sometime after enrollment
            a_start = e_date + timedelta(days=1)
            a_end = e_date + timedelta(days=90)
            if a_end > today:
                a_end = today
            a_date = random_date(a_start, a_end)

            assess_rows.append({
                "assessment_id": f"A{assess_id:04d}",
                "Emp_ID": eid,
                "course_id": cid,
                "score_prct": random.randint(50, 100),
                "method_of_assessment": random.choice(assessment_methods),
                "assessment_date": to_str(a_date),
            })

            enroll_id += 1
            assess_id += 1

    pd.DataFrame(enroll_rows).to_csv(OUTPUT_DIR / f"enrollment_{suffix}.csv", index=False)
    pd.DataFrame(assess_rows).to_csv(OUTPUT_DIR / f"assessment_{suffix}.csv", index=False)
    print(f"enrollment_{suffix}.csv -> {len(enroll_rows)} rows")
    print(f"assessment_{suffix}.csv -> {len(assess_rows)} rows")

print("\ndone")