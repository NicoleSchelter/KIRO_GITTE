#!/usr/bin/env python3
from sqlalchemy import create_engine, inspect

db_url = 'postgresql+psycopg2://gitte:sicheres_passwort@localhost:5432/kiro_test'
engine = create_engine(db_url)
inspector = inspect(engine)

print('Current indexes on pseudonyms table:')
indexes = inspector.get_indexes('pseudonyms')
for idx in indexes:
    print(f'  - {idx["name"]}: {idx["column_names"]}')

print('\nCurrent columns on pseudonyms table:')
columns = inspector.get_columns('pseudonyms')
for col in columns:
    print(f'  - {col["name"]}: {col["type"]}')

print('\nCurrent foreign keys on pseudonyms table:')
fks = inspector.get_foreign_keys('pseudonyms')
for fk in fks:
    cols = ', '.join(fk['constrained_columns'])
    ref_cols = ', '.join(fk['referred_columns'])
    print(f'  - {cols} -> {fk["referred_table"]}.{ref_cols}')