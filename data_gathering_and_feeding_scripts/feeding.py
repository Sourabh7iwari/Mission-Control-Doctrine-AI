import psycopg2
import pandas as pd

# Load your CSV
df = pd.read_csv('/home/sourabh7iwari/Repository/wartime_strategy_chatbot/data_gathering_scripts/military_standies.csv')

# Connect to PostgreSQL
conn = psycopg2.connect(
    dbname="military_db",
    user="postgres",
    host="localhost"
)

# Create cursor
cursor = conn.cursor()

# Prepare the insert query
insert_query = """
    INSERT INTO military_personnel 
    (country, active_military, reserve_military, paramilitary, 
     total, per_1000_total, per_1000_active, ref)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""

# Insert data row by row
for _, row in df.iterrows():
    cursor.execute(insert_query, (
        row['Country'], 
        row['Active military'],
        row['Reserve military'],
        row['Paramilitary'],
        row['Total'],
        row['Per 1,000 capita (total)'],
        row['Per 1,000 capita (active)'],
        row['Ref']
    ))

# Commit and close
conn.commit()
cursor.close()
conn.close()
print("Data imported successfully!")