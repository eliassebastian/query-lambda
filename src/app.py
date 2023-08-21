from datetime import datetime, timezone
import io
import json
import os
from typing import NamedTuple
from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import ValueTarget
import base64
import tafra
import xxhash
from itertools import repeat
import libsql_client

def clean_string(s):
    return s.lstrip('"').rstrip('"').strip()

def dtype_to_sqlite(dtype):
    return {
        'float64': 'REAL',
        'int64': 'INTEGER',
        'int32': 'INTEGER',
        'object': 'TEXT',
    }.get(dtype, 'TEXT') 

def statement_from_row(row: NamedTuple, table_name: str, placeholders: str) -> libsql_client.Statement:
    return libsql_client.Statement(f"INSERT INTO {table_name} VALUES ({placeholders})", tuple(row))

def lambda_handler(event, context):
    parser = StreamingFormDataParser(headers=event['headers'])
    user_id = ValueTarget()
    file_name = ValueTarget() 
    uploaded_file = ValueTarget()

    parser.register("userid", user_id)
    parser.register("filename", file_name)
    parser.register("file", uploaded_file)

    if event['isBase64Encoded']:
        body_bytes = base64.b64decode(event['body'])
    else:
        body_bytes = event['body'].encode('utf-8')

    parser.data_received(body_bytes)

    with io.TextIOWrapper(io.BufferedReader(io.BytesIO(uploaded_file.value)), encoding='utf-8') as wrapper:
        tf = tafra.read_csv(wrapper, guess_rows=10)
    
    file_name_decoded = file_name.value.decode()
    user_id_decoded = user_id.value.decode()
    table_name = f"{file_name_decoded}_{user_id_decoded}"
    hashed_table_name = "uu_" + xxhash.xxh64_hexdigest(table_name, seed=0)
    sqlite_types = {col.strip().strip('"'): dtype_to_sqlite(dtype) for col, dtype in tf.dtypes.items()}
    placeholders = ', '.join(repeat('?', len(tf.columns)))
    schema = f"CREATE TABLE IF NOT EXISTS {hashed_table_name} ({','.join([f'{column} {dtype}' for column, dtype in sqlite_types.items()])})"

    with libsql_client.create_client_sync(url=os.environ.get("TURSO_DB_URL"), auth_token=os.environ.get("TURSO_DB_AUTH_TOKEN")) as sql_client: 
        insert_statements = list(tf.tuple_map(statement_from_row, table_name=hashed_table_name, placeholders=placeholders))
        sql_client.batch([
            libsql_client.Statement(
                "INSERT INTO querylang_uploads (hashed, owner, name, schema) VALUES (?, ?, ?, ?)",
                [hashed_table_name, user_id_decoded, file_name_decoded, schema]
            ),
            libsql_client.Statement(
                schema
            )
        ] + insert_statements)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "status": "success",
            "message": "file uploaded successfully",
            "data": {
                "name": file_name_decoded,
                "hashed": hashed_table_name,
                "schema": schema,
                "uploaded_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            }
        }),
        "headers": {
            "content-type": "application/json"
        }
    }
