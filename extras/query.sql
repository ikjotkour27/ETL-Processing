USE ETL_Project;


TRUNCATE TABLE staging_employee;


INSERT INTO staging_employee
(
    employee_key,
    emp_id,
    emp_nm,
    email,
    gender,
    phone_no,
    management_level,
    checksum,
    change_flag
)

SELECT

CONCAT(
emp_id,'_',
DATE_FORMAT(NOW(),'%Y%m%d%H%i%s')
),

emp_id,

INITCAP(emp_nm),

LOWER(email),

CASE
WHEN UPPER(gender) IN ('MALE','M')
THEN 'M'

WHEN UPPER(gender) IN ('FEMALE','F')
THEN 'F'

ELSE NULL
END,

CASE
WHEN phone_no REGEXP '^[0-9]{7,15}$'
THEN phone_no
ELSE NULL
END,

management_level,

MD5(
CONCAT_WS('|',
emp_id,
emp_nm,
email,
gender,
phone_no,
management_level
)
),

CASE

WHEN NOT EXISTS
(
SELECT 1
FROM base_employee b
WHERE b.emp_id=l.emp_id
)

THEN 'I'

WHEN EXISTS
(
SELECT 1
FROM base_employee b
WHERE b.emp_id=l.emp_id
AND b.curr_ind='Y'
AND b.checksum<>
MD5(
CONCAT_WS('|',
emp_id,
emp_nm,
email,
gender,
phone_no,
management_level
)
)
)

THEN 'U'

ELSE 'N'

END

FROM landing_employee l

WHERE emp_id IS NOT NULL;