import os
import re
import shutil
import random
import string
from datetime import datetime
import pandas as pd
import mysql.connector

SOURCE_DIR = "source"
LANDING_DIR = "landing"
ARCHIVE_DIR = "archive"

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Ikjot123@",
    "database": "ETL_Project",
}

file_groups = {
    "employee": "emp_",
    "course": "course_",
    "trainer": "trainer_",
    "enrollment": "enrollment_",
    "assessment": "assessment_",
}

ID_COL_MAP = {
    "employee":   {"col": "emp_id",        "prefix": "E"},
    "course":     {"col": "course_id",     "prefix": "C"},
    "trainer":    {"col": "trainer_id",    "prefix": "T"},
    "enrollment": {"col": "enrollment_id", "prefix": "En"},
    "assessment": {"col": "assessment_id", "prefix": "A"},
}

SCRIPT_NAME = "landing_extract.py"

random.seed(42)


def get_date_from_filename(fname):
    match = re.search(r"_(\d{6})\.", fname)
    if match:
        return match.group(1)
    return None

def find_lowest_date_file(prefix):
    files = os.listdir(SOURCE_DIR)
    matching = [f for f in files if f.startswith(prefix)]
    if not matching:
        return None
    matching.sort(key=lambda f: get_date_from_filename(f) or "")
    return matching[0]

def make_load_key():
    rand_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"LCK_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{rand_part}"

def read_file(filepath):
    if filepath.endswith(".csv"):
        return pd.read_csv(filepath)
    elif filepath.endswith(".xlsx"):
        return pd.read_excel(filepath)
    elif filepath.endswith(".json"):
        return pd.read_json(filepath)
    else:
        raise ValueError(f"unsupported file type: {filepath}")

def pad_id(value, prefix, width=5):
    s = str(value)
    if s.startswith(prefix):
        num_part = s[len(prefix):]
        if num_part.isdigit():
            return f"{prefix}{num_part.zfill(width)}"
    return s

def pad_id_column(df, table_name):
    info = ID_COL_MAP.get(table_name)
    if not info:
        return df
    col, prefix = info["col"], info["prefix"]
    if col in df.columns:
        df[col] = df[col].apply(lambda v: pad_id(v, prefix))
    # course_id / Emp_ID foreign key columns also need padding if present
    if "course_id" in df.columns and table_name != "course":
        df["course_id"] = df["course_id"].apply(lambda v: pad_id(v, "C"))
    if "Emp_ID" in df.columns:
        df["Emp_ID"] = df["Emp_ID"].apply(lambda v: pad_id(v, "E"))
    return df

def write_to_audit(conn, file_name, ts, load_key, status, file_path, row_count):
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO audit_table (file_name, ingest_timestamp, load_key, completion_status, file_path, row_count)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (file_name, ts, load_key, status, file_path, row_count),
    )
    conn.commit()
    cursor.close()

def create_audit_table(conn):
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_table (
            audit_id INT AUTO_INCREMENT PRIMARY KEY,
            file_name VARCHAR(100),
            ingest_timestamp DATETIME,
            load_key VARCHAR(50),
            completion_status VARCHAR(20),
            file_path VARCHAR(255),
            row_count INT
        )
        """
    )
    conn.commit()
    cursor.close()


def create_audit_table_2(conn):
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_table_2 (
            audit_id INT AUTO_INCREMENT PRIMARY KEY,
            table_name VARCHAR(100),
            file_name VARCHAR(100),
            ingest_timestamp DATETIME,
            load_key VARCHAR(50),
            status VARCHAR(20),
            file_path VARCHAR(255),
            row_count INT
        )
        """
    )
    conn.commit()
    cursor.close()


def write_to_audit_2(conn, table_name, file_name, ts, load_key, status, file_path, row_count):
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO audit_table_2 (table_name, file_name, ingest_timestamp, load_key, status, file_path, row_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (table_name, file_name, ts, load_key, status, file_path, row_count),
    )
    conn.commit()
    cursor.close()


def archive_old_files():
    for prefix in file_groups.values():
        files = [f for f in os.listdir(ARCHIVE_DIR) if f.startswith(prefix)]
        files.sort(key=lambda f: get_date_from_filename(f) or "")
        while len(files) > 7:
            old_file = files.pop(0)
            os.remove(os.path.join(ARCHIVE_DIR, old_file))
            print(f"removed old archive file: {old_file}")

def create_load_control_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS load_control (
            control_id INT AUTO_INCREMENT PRIMARY KEY,
            project_name VARCHAR(50),
            load_key VARCHAR(100),
            load_date DATETIME,
            status VARCHAR(20)
        )
    """)
    conn.commit()
    cursor.close()

def insert_load_control(conn, project_name, load_key, status):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO load_control
        (project_name, load_key, load_date, status)
        VALUES (%s, %s, %s, %s)
    """, (
        project_name,
        load_key,
        datetime.now(),
        status
    ))
    conn.commit()
    cursor.close()

def update_load_control(conn, load_key, status):
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE load_control
        SET status = %s
        WHERE load_key = %s
    """, (status, load_key))
    conn.commit()
    cursor.close()

def already_processed(conn, file_name):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*)
        FROM audit_table
        WHERE file_name = %s
          AND completion_status = 'success'
    """, (file_name,))
    count = cursor.fetchone()[0]
    cursor.close()
    return count > 0


def create_landing_table(conn, table_name, columns):
    cursor = conn.cursor()
    col_defs = ",\n    ".join([f"`{col}` TEXT" for col in columns])
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS landing_{table_name} (
            landing_id INT AUTO_INCREMENT PRIMARY KEY,
            {col_defs}
        )
    """)
    conn.commit()
    cursor.close()


def insert_landing_rows(conn, table_name, df):
    if df.empty:
        return
    cursor = conn.cursor()
    cols = list(df.columns)
    col_names = ", ".join(f"`{c}`" for c in cols)
    placeholders = ", ".join(["%s"] * len(cols))
    sql = f"INSERT INTO landing_{table_name} ({col_names}) VALUES ({placeholders})"
    values = [
        tuple(None if pd.isna(v) else v for v in row)
        for row in df.itertuples(index=False, name=None)
    ]
    cursor.executemany(sql, values)
    conn.commit()
    cursor.close()


def run_landing():
    conn = mysql.connector.connect(**DB_CONFIG)
    create_audit_table(conn)
    create_load_control_table(conn)
    create_audit_table_2(conn)   # CHANGE (audit_table_2)

    load_key = make_load_key()
    ts = datetime.now()

    insert_load_control(conn, "LTM", load_key, "STARTED")

    any_failed = False
    any_succeeded = False

    for table_name, prefix in file_groups.items():
        fname = find_lowest_date_file(prefix)
        landing_table_name = f"landing_{table_name}"   # CHANGE (audit_table_2)

        if not fname:
            print(f"no file found for {table_name}, skipping")
            # CHANGE (audit_table_2): still log that this table had nothing to process
            write_to_audit_2(conn, landing_table_name, SCRIPT_NAME, ts, load_key,
                              "no_file_found", None, 0)
            continue

        src_path = os.path.join(SOURCE_DIR, fname)
        print(f"processing {fname} for table {table_name}...")

        # Skip files that were already processed successfully
        if already_processed(conn, fname):
            print(f"{fname} already processed. Skipping.")
            # CHANGE (audit_table_2)
            write_to_audit_2(conn, landing_table_name, SCRIPT_NAME, ts, load_key,
                              "already_processed", src_path, 0)
            continue

        status = "success"
        row_count = 0

        try:
            df = read_file(src_path)
            row_count = len(df)

            # Check if file is empty
            if df.empty:
                status = "EMPTY_FILE"
                print(f"{fname} is empty. Skipping processing.")
                write_to_audit(conn, fname, ts, load_key, status, src_path, row_count)
                write_to_audit_2(conn, landing_table_name, SCRIPT_NAME, ts, load_key,
                                  status, src_path, row_count)   # CHANGE (audit_table_2)
                shutil.move(src_path, os.path.join(ARCHIVE_DIR, fname))
                continue

            df = pad_id_column(df, table_name)

            df["ingest_timestamp"] = ts
            df["load_key"] = load_key

            out_name = os.path.splitext(fname)[0] + ".csv"
            out_path = os.path.join(LANDING_DIR, out_name)
            df.to_csv(out_path, index=False)

            create_landing_table(conn, table_name, list(df.columns))
            insert_landing_rows(conn, table_name, df)

            shutil.move(src_path, os.path.join(ARCHIVE_DIR, fname))
            any_succeeded = True

        except Exception as e:
            status = "failed"
            any_failed = True
            print(f"error processing {fname}: {e}")

        write_to_audit(conn, fname, ts, load_key, status, src_path, row_count)
        write_to_audit_2(conn, landing_table_name, SCRIPT_NAME, ts, load_key,
                          status, src_path, row_count)   # CHANGE (audit_table_2)

    archive_old_files()

    if any_failed and any_succeeded:
        final_status = "partial"
    elif any_failed:
        final_status = "failed"
    else:
        final_status = "success"
    update_load_control(conn, load_key, final_status)

    conn.close()
    print(f"\nlanding step done - load_control status: {final_status}")


if __name__ == "__main__":
    run_landing()