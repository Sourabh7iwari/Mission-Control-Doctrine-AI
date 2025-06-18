import pandas as pd

url = "https://en.wikipedia.org/wiki/List_of_countries_by_number_of_military_and_paramilitary_personnel"

tables = pd.read_html(url)

print(f"Number of tables found: {len(tables)}")

first_table = tables[1]
print(first_table.head())

first_table.to_csv('military_standies.csv', index=False)