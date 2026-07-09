CREATE database etl;
use etl;

create table AUDIT_TABLE{
	String file_name Primary Key,
    varchar load_key,
    -- timestamp ,completion_status,rows_processed 
};