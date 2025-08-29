import psycopg2
import json
from dotenv import load_dotenv
import os

load_dotenv()

# Connect via Cloud SQL Proxy
conn = psycopg2.connect(
    host='127.0.0.1',
    port=5433,
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME')
)

cur = conn.cursor()

# Get all tables
cur.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE'
    ORDER BY table_name;
""")
tables = cur.fetchall()

print("=== NWSL DATABASE SCHEMA EXPLORATION ===\n")
print(f"Found {len(tables)} tables:\n")

schema_info = {}

for (table_name,) in tables:
    print(f"\n📊 TABLE: {table_name}")
    print("-" * 50)
    
    # Get columns
    cur.execute("""
        SELECT column_name, data_type, character_maximum_length, is_nullable
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position;
    """, (table_name,))
    columns = cur.fetchall()
    
    # Get row count
    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cur.fetchone()[0]
    
    # Get foreign keys
    cur.execute("""
        SELECT
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY' 
        AND tc.table_name = %s;
    """, (table_name,))
    foreign_keys = cur.fetchall()
    
    # Get sample data
    cur.execute(f"SELECT * FROM {table_name} LIMIT 2")
    sample_data = cur.fetchall()
    col_names = [desc[0] for desc in cur.description]
    
    print(f"Rows: {count:,}")
    print("\nColumns:")
    
    table_info = {
        "row_count": count,
        "columns": [],
        "foreign_keys": [],
        "sample_data": []
    }
    
    for col_name, data_type, max_length, nullable in columns:
        null_str = "NULL" if nullable == 'YES' else "NOT NULL"
        type_str = data_type
        if max_length:
            type_str += f"({max_length})"
        print(f"  - {col_name}: {type_str} {null_str}")
        
        table_info["columns"].append({
            "name": col_name,
            "type": data_type,
            "nullable": nullable == 'YES'
        })
    
    if foreign_keys:
        print("\nForeign Keys:")
        for col, ref_table, ref_col in foreign_keys:
            print(f"  - {col} → {ref_table}.{ref_col}")
            table_info["foreign_keys"].append({
                "column": col,
                "references_table": ref_table,
                "references_column": ref_col
            })
    
    if sample_data and count > 0:
        print(f"\nSample Data (first 2 rows):")
        for row in sample_data:
            row_dict = dict(zip(col_names, row))
            # Convert to string for display
            row_str = {k: str(v)[:50] for k, v in row_dict.items()}
            print(f"  {row_str}")
            table_info["sample_data"].append({k: str(v) for k, v in row_dict.items()})
    
    schema_info[table_name] = table_info

# Save schema
with open('nwsl_schema.json', 'w') as f:
    json.dump(schema_info, f, indent=2, default=str)

print("\n\n=== SUMMARY ===")
print(f"Total tables: {len(tables)}")
print(f"Total rows across all tables: {sum(t['row_count'] for t in schema_info.values()):,}")
print("\nKey tables:")
for table in ['team', 'player', 'match_registry', 'venue']:
    if table in schema_info:
        print(f"  - {table}: {schema_info[table]['row_count']:,} rows")

print("\nSchema saved to nwsl_schema.json")

cur.close()
conn.close()