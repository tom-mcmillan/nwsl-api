import asyncio
import asyncpg
from dotenv import load_dotenv
import os
import json

load_dotenv()

async def explore_database():
    # Connect to the database via Cloud SQL Proxy
    conn = await asyncpg.connect(
        host='127.0.0.1',
        port=5433,
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )
    
    try:
        # Get all tables
        tables_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name;
        """
        tables = await conn.fetch(tables_query)
        
        print("=== DATABASE SCHEMA EXPLORATION ===\n")
        print(f"Found {len(tables)} tables in database '{os.getenv('DB_NAME')}':\n")
        
        schema_info = {}
        
        for table in tables:
            table_name = table['table_name']
            print(f"\n📊 TABLE: {table_name}")
            print("-" * 50)
            
            # Get columns info
            columns_query = """
            SELECT 
                column_name,
                data_type,
                character_maximum_length,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = $1
            ORDER BY ordinal_position;
            """
            columns = await conn.fetch(columns_query, table_name)
            
            # Get row count
            count_query = f"SELECT COUNT(*) as count FROM {table_name}"
            count = await conn.fetchval(count_query)
            
            # Get foreign keys
            fk_query = """
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
            AND tc.table_name = $1;
            """
            foreign_keys = await conn.fetch(fk_query, table_name)
            
            # Get sample data
            sample_query = f"SELECT * FROM {table_name} LIMIT 3"
            sample_data = await conn.fetch(sample_query)
            
            print(f"Rows: {count}")
            print("\nColumns:")
            
            table_info = {
                "row_count": count,
                "columns": [],
                "foreign_keys": [],
                "sample_data": []
            }
            
            for col in columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                col_type = col['data_type']
                if col['character_maximum_length']:
                    col_type += f"({col['character_maximum_length']})"
                print(f"  - {col['column_name']}: {col_type} {nullable}")
                
                table_info["columns"].append({
                    "name": col['column_name'],
                    "type": col['data_type'],
                    "nullable": col['is_nullable'] == 'YES',
                    "max_length": col['character_maximum_length'],
                    "default": col['column_default']
                })
            
            if foreign_keys:
                print("\nForeign Keys:")
                for fk in foreign_keys:
                    print(f"  - {fk['column_name']} → {fk['foreign_table_name']}.{fk['foreign_column_name']}")
                    table_info["foreign_keys"].append({
                        "column": fk['column_name'],
                        "references_table": fk['foreign_table_name'],
                        "references_column": fk['foreign_column_name']
                    })
            
            if sample_data:
                print(f"\nSample Data (first 3 rows):")
                for row in sample_data[:3]:
                    print(f"  {dict(row)}")
                    table_info["sample_data"].append(dict(row))
            
            schema_info[table_name] = table_info
        
        # Save schema info to JSON
        with open('db_schema.json', 'w') as f:
            json.dump(schema_info, f, indent=2, default=str)
        
        print("\n\n=== SUMMARY ===")
        print(f"Total tables: {len(tables)}")
        print("Schema saved to db_schema.json")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(explore_database())