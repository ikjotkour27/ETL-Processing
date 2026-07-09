USE ETL_project;
CREATE OR REPLACE VIEW vw_employee_training AS
SELECT
    e.emp_id,
    e.first_nm,
    e.last_nm,
    e.email,
    e.primary_skill,
    e.management_level,
    en.course_id,
    c.course_nm,
    en.course_status,
    -- score: NULL if cancelled OR not yet assessed
    CASE
        WHEN en.course_status = 'Cancelled' THEN NULL
        ELSE a.score_prct
    END AS score_prct,
    -- grade: NULL if cancelled OR not yet assessed
    CASE
        WHEN en.course_status = 'Cancelled'                        THEN NULL
        WHEN a.score_prct IS NULL                                  THEN NULL
        WHEN CAST(a.score_prct AS DECIMAL(5,2)) BETWEEN 0  AND 40  THEN 'P1'
        WHEN CAST(a.score_prct AS DECIMAL(5,2)) BETWEEN 41 AND 60  THEN 'P2'
        WHEN CAST(a.score_prct AS DECIMAL(5,2)) BETWEEN 61 AND 80  THEN 'P3'
        WHEN CAST(a.score_prct AS DECIMAL(5,2)) BETWEEN 81 AND 100 THEN 'P4'
        ELSE NULL
    END AS grade,
    -- CHANGE 5: explicit status flag for BI reporting
    CASE
        WHEN en.course_status = 'Cancelled'          THEN 'Cancelled'
        WHEN a.score_prct IS NULL                    THEN 'Not Appeared'
        --  if it is p1 and p2 , then retest
        ELSE 'Passed'
    END AS assessment_status
FROM base_employee e
JOIN base_enrollment en
    ON e.emp_id    = en.emp_id
    AND en.curr_ind = 'Y'
LEFT JOIN base_course c
    ON c.course_id  = en.course_id
    AND c.curr_ind  = 'Y'
LEFT JOIN base_assessment a
    ON a.emp_id    = en.emp_id
    AND a.course_id = en.course_id
    AND a.curr_ind  = 'Y'
WHERE e.curr_ind = 'Y';

SELECT
    CASE
        WHEN course_status = 'Cancelled' THEN 'Cancelled'
        WHEN assessment_status = 'Not Appeared' THEN 'Did Not Give Assessment'
        ELSE 'Gave Assessment'
    END AS Assessment_Category,
    COUNT(*) AS Total
FROM vw_employee_training
GROUP BY Assessment_Category;