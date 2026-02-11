import sqlite3

conn = sqlite3.connect('kivy-lcd-app/mangofy.db')
cur = conn.cursor()

print('Diseases:')
cur.execute('SELECT * FROM tbl_disease')
diseases = cur.fetchall()
for d in diseases:
    print(f'  {d[0]}. {d[1]}')

print('\nSeverity Levels:')
cur.execute('SELECT * FROM tbl_severity_level')
levels = cur.fetchall()
for l in levels:
    print(f'  {l[0]}. {l[1]}')

conn.close()
