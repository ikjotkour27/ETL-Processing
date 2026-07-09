import mysql.connector
from datetime import datetime, date, timedelta

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Ikjot123@",
    "database": "ETL_Project",
}

TABLE_CONFIG = {
    "employee":   ("staging_employee",   "emp_id"),
    "course":     ("staging_course",     "course_id"),
    "trainer":    ("staging_trainer",    "trainer_id"),
    "enrollment": ("staging_enrollment", "enrollment_id"),
    "assessment": ("staging_assessment", "assessment_id"),
}

END_OF_TIME = "9999-12-31"

SCRIPT_NAME = "base_extract.py"


def create_base_table(conn, table_name, columns, key_col):
    cursor = conn.cursor()
    col_defs = ",\n    ".join([f"`{col}` TEXT" for col in columns])
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS base_{table_name} (
            `{key_col}` VARCHAR(100) PRIMARY KEY,
            {col_defs},
            checksum VARCHAR(32),
            start_date DATE,
            end_date DATE,
            curr_ind CHAR(1)
        )
    """)
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


def fetch_staging_rows(conn, staging_table):
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"SELECT * FROM {staging_table}")
    rows = cursor.fetchall()
    cursor.close()
    return rows


def truncate_staging_table(conn, staging_table):
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {staging_table}")
    conn.commit()
    cursor.close()


def get_active_record(conn, table_name, id_col, id_value):
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"""
        SELECT * FROM base_{table_name}
        WHERE `{id_col}` = %s AND curr_ind = 'Y'
    """, (str(id_value),))
    row = cursor.fetchone()
    cursor.close()
    return row


def insert_base_row(conn, table_name, row):
    cursor = conn.cursor()
    cols         = list(row.keys())
    col_names    = ", ".join([f"`{c}`" for c in cols])
    placeholders = ", ".join(["%s"] * len(cols))
    sql          = f"INSERT INTO base_{table_name} ({col_names}) VALUES ({placeholders})"
    cursor.execute(sql, tuple(row[c] for c in cols))
    conn.commit()
    cursor.close()


def expire_active_record(conn, table_name, id_col, id_value, today):
    """
    SCD Type 2 expiry:
    end_date = today - 1 day, so the old record ends the day before
    the new record starts. No overlap in history.

    BUGFIX #5: if the active record's own start_date is already today
    (a same-day correction - the record was inserted earlier today and is
    being updated again today), end_date = today - 1 would be *before*
    start_date, producing an invalid interval. In that case we set
    end_date = today instead, so the interval is never inverted.
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"""
        SELECT start_date FROM base_{table_name}
        WHERE `{id_col}` = %s AND curr_ind = 'Y'
    """, (str(id_value),))
    active = cursor.fetchone()
    cursor.close()

    if active and active["start_date"] == today:
        end_date = today
    else:
        end_date = today - timedelta(days=1)

    cursor = conn.cursor()
    cursor.execute(f"""
        UPDATE base_{table_name}
        SET curr_ind = 'N',
            end_date = %s
        WHERE `{id_col}` = %s AND curr_ind = 'Y'
    """, (end_date, str(id_value)))
    conn.commit()
    cursor.close()


def process_row(conn, table_name, id_col, key_col, curr, today):
    """
    Reads change_flag from staging and acts on it:
      I -> new record, INSERT directly
      U -> SCD Type 2: expire old (end_date = today-1, or today for same-day
           corrections), insert new (start_date = today)
      N -> safety net, should never reach here since staging filters these out
    """
    change_flag = curr.get("change_flag")
    id_value    = curr.get(id_col)

    if change_flag == "N":
        return "skipped"

    new_row = {
        key_col: curr[key_col],
        **{k: v for k, v in curr.items() if k not in (key_col, "change_flag")},
        "start_date": today,
        "end_date":   END_OF_TIME,
        "curr_ind":   "Y",
    }

    if change_flag == "I":
        insert_base_row(conn, table_name, new_row)
        return "inserted"

    elif change_flag == "U":
        # expire old record with end_date = today - 1 (or today, if the old
        # record also started today - see expire_active_record)
        expire_active_record(conn, table_name, id_col, id_value, today)
        insert_base_row(conn, table_name, new_row)
        return "updated"

    return "skipped"


def run_base():
    conn  = mysql.connector.connect(**DB_CONFIG)
    create_audit_table_2(conn)   # CHANGE (audit_table_2)

    today  = date.today()
    run_ts = datetime.now()   # CHANGE (audit_table_2): timestamp for audit rows

    print(f"base layer execution: {datetime.now()}\n")

    for table_name, (staging_table, id_col) in TABLE_CONFIG.items():
        print(f"processing {table_name}...")
        base_table_name = f"base_{table_name}"   # CHANGE (audit_table_2)

        try:
            staging_rows = fetch_staging_rows(conn, staging_table)
            if not staging_rows:
                print(f"  SKIPPP!! no data found in {staging_table}")
                # CHANGE (audit_table_2)
                write_to_audit_2(conn, base_table_name, SCRIPT_NAME, run_ts,
                                  None, "no_data", None, 0)
                continue

            # CHANGE (audit_table_2): pull load_key through from staging so
            # base-layer audit rows can still be traced back to the run
            # that originally landed the data.
            load_key = staging_rows[0].get("load_key")

            key_col = f"{table_name}_key"

            sample         = staging_rows[0]
            base_data_cols = [
                c for c in sample.keys()
                if c not in (key_col, "checksum", "change_flag")
            ]

            create_base_table(conn, table_name, base_data_cols, key_col)

            counts = {"inserted": 0, "updated": 0, "skipped": 0}

            for i in staging_rows:
                curr = {key_col: i[key_col]}
                for col in base_data_cols:
                    curr[col] = i.get(col)
                curr["checksum"]    = i.get("checksum")
                curr["change_flag"] = i.get("change_flag")

                result = process_row(conn, table_name, id_col, key_col, curr, today)
                counts[result] += 1

            print(f"  inserted: {counts['inserted']}  updated: {counts['updated']}  skipped: {counts['skipped']}")

            truncate_staging_table(conn, staging_table)
            print(f"  staging_{table_name} cleared")

            # CHANGE (audit_table_2): row_count = rows actually written to base
            write_to_audit_2(
                conn, base_table_name, SCRIPT_NAME, run_ts, load_key,
                "success", None, counts["inserted"] + counts["updated"]
            )

        except Exception as e:
            print(f"  error processing {table_name}: {e}")
            print(f"  staging_{table_name} NOT cleared due to error")
            # CHANGE (audit_table_2)
            write_to_audit_2(conn, base_table_name, SCRIPT_NAME, run_ts,
                              None, "failed", None, 0)

    conn.close()
    print("\nbase layer run done")


if __name__ == "__main__":
    run_base()


# base extract takes the change_flag from staging layer
# I -> fresh INSERT, new active record (start_date=today, end_date=9999-12-31, curr_ind=Y)
# U -> SCD Type 2: old record expired (curr_ind=N, end_date=today-1, or today
#                  for a same-day correction so the interval is never inverted)
#                  new record inserted (curr_ind=Y, start_date=today, end_date=9999-12-31)
# N -> skipped (staging should never send these, safety net only)
# staging table is truncated only after full successful batch per table
# CHANGE (audit_table_2): every table processed here (success, no data, or
# failed) now writes one row to audit_table_2, tying base-layer results back
# to the same load_key used at landing/staging.