import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("mysql+mysqlconnector://root:AryanVmr0908@localhost/ETL_project")

# load each CSV into a table
emp = pd.read_csv("input/emp_130525.csv")
emp.to_sql("employee", con=engine, if_exists="replace", index=False)

enrollment = pd.read_csv("output/enrollment_130525.csv")
enrollment.to_sql("enrollment", con=engine, if_exists="replace", index=False)

print("tables loaded")
# csv
# excel
# json file
# add some unstructured info as well 
# and extract it and inform narunikka
# then again analyze the date and see for the changes and transformations