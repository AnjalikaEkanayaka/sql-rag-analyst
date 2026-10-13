import sqlite3

# mode=ro opens the file READ-ONLY. A preview of our safety design.
con = sqlite3.connect("file:data/chinook.db?mode=ro", uri=True)
cur = con.cursor()

tables = [r[0] for r in cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
print(len(tables), "tables")

for t in tables:
    n = cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    print(f"\n{t} ({n} rows)")
    for _cid, name, ctype, _notnull, _default, pk in cur.execute(f'PRAGMA table_info("{t}")'):
        print(f"  {name:20} {ctype:15} {'PK' if pk else ''}")
    for fk in cur.execute(f'PRAGMA foreign_key_list("{t}")'):
        print(f"  FK: {fk[3]} -> {fk[2]}.{fk[4]}")