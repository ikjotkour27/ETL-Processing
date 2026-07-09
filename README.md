                                ETL_Project
Read CSV / Excel files , clean and standardize data using Python and load it into MySQL Data Warehouse Layers


Source - original csv files and is kept here so that if there is some data loss while transforming we have the data

Archive - Succesfully transformed data will be kept here so that we are not using same data again



CSV Files - Source Folder - Landing Layer - Staging Layer - Base Layer - Final Warehouse Layer


Landing Layer receives the raw data , no modifications , exact copy of source data
Staging Layer does the cleaning , transforming , standardizing , normalizing , validation (null values , date conversion , duplicates , invalid records)
Base Layer stores the trusted version of data in Archive folder

Audit Table - which tracks every file ingestion
    file_name
    file_path
    load_key
    timeStamp
    completion_status
    rows_processed

read csv files using pandas - extract krne ke liye


Extract → Read the CSV
Transform → Clean and standardize data
Load → Store into a database/data warehouse

isNull
dropDuplicates
replace
to_datetime
check phone length
str.strip


if data is coming from any source 
it is easily in readable format for pandas
it will read it and create dataframes and will be able to understand it


i have the updated emp
and updated courses 
i need, assessment and enrollment
we will have to generate the enrollment and assessment data again based on this.

Creates audit_table in MySQL automatically
For each of the 5 table types, finds the lowest-date file in source/
Adds ingest_timestamp + load_key (same load_key for all 5 files in one run)
Saves to landing/ as CSV
Moves original to archive/ (and trims archive to keep only last 7 per table type)
Logs file_name, timestamp, load_key, status, file_path, row_count into audit_table


LANDING
Landing layer tasks:

Pick the file with the lowest date (13 → 14 → 15) for each table (emp, course, trainer, enrollment, assessment) from source/
Add two columns to each file: ingest_timestamp and load_key (same load_key for all files in one run, format LCK_<date>_<time>_<random>)
Save the updated file to landing/
Move the original source file to archive/ (keep last 7 per table)
Log every file processed into audit_table with: file_name, ingest_timestamp, load_key, completion_status, file_path, row_count
Support both CSV and Excel/JSON as input, output as CSV

Walking through landing_extract.py step by step:
1. Setup
pythonload_key = make_load_key()
ts = datetime.now()
conn = mysql.connector.connect(**DB_CONFIG)
create_audit_table(conn)
One load_key and one timestamp generated once per run — shared across all 5 files. create_audit_table runs CREATE TABLE IF NOT EXISTS, so it's safe to call every time.
2. Finding the right file — find_lowest_date_file
pythondef find_lowest_date_file(prefix):
    files = os.listdir(SOURCE_DIR)
    matching = [f for f in files if f.startswith(prefix)]
    matching.sort(key=lambda f: get_date_from_filename(f))
    return matching[0]
For each table prefix (emp_, course_, etc.), it lists all matching files in source/, sorts them by the 6-digit date in the filename (130525 < 140525 < 150525 as strings, since they're same length and same order numerically), and picks the first — i.e. lowest date.
3. Reading the file — read_file
pythonif filepath.endswith(".csv"): return pd.read_csv(filepath)
elif filepath.endswith(".xlsx"): return pd.read_excel(filepath)
elif filepath.endswith(".json"): return pd.read_json(filepath)
Handles CSV, Excel, and JSON — whatever extension the source file has.
4. Adding the two columns
pythondf["ingest_timestamp"] = ts
df["load_key"] = load_key
Pandas broadcasts the single value to every row.
5. Saving to landing
pythonout_name = os.path.splitext(fname)[0] + ".csv"
df.to_csv(os.path.join(LANDING_DIR, out_name), index=False)
Always writes as .csv regardless of input format — so course_130525.xlsx becomes course_130525.csv in landing.
6. Archiving the original
pythonshutil.move(src_path, os.path.join(ARCHIVE_DIR, fname))
Moves (not copies) the original file from source/ to archive/ — so next run it's gone from source, and find_lowest_date_file will naturally pick the next date.
7. Logging to audit_table
pythonwrite_to_audit(conn, fname, ts, load_key, status, src_path, row_count)
Runs an INSERT for every file, whether it succeeded or failed (wrapped in try/except — if reading/writing fails, status = "failed" and row_count = 0, but it still logs the attempt).
8. Archive cleanup — archive_old_files
pythonfiles.sort(key=lambda f: get_date_from_filename(f) or "")
while len(files) > 7:
    old_file = files.pop(0)
    os.remove(...)
After archiving, for each table type it checks if more than 7 files exist in archive/ and deletes the oldest ones.
Why running it 3 times works: each run, source/ has one less date available per table (since the previous lowest got archived), so the script naturally progresses 13 → 14 → 15.

LCK_<YYYYMMDD>_<HHMMSS>_<6 random alphanumeric chars>


It still uses pandas to read the file (pd.read_csv, pd.read_excel, pd.read_json) and iterate rows — but the database writes are now pure SQL (INSERT via cursor.executemany) instead of df.to_sql().
<!-- STAGINF LAYER  -->

SHA256 hash value converter changes it to 64 bit hash , but i have used ,md5() funcction over it , to make it a 32 bit hash




<!-- start date can't be greater than end date  -->
<!-- and end date in  -->


chunking
dict out of archive files 