import mysql.connector

config = {
    "user": "root",
    "password": "123456",
    "host": "127.0.0.1",
    "port": 3306,
    "database": "HTTP_FAST"
}

db = mysql.connector.connect(**config)
cursor = db.cursor()

def row_to_dict(cursor, data):
    if data is None:
        return None
    return dict(zip(cursor.column_names, data))

def rows_to_list(cursor, datas):
    return [dict(zip(cursor.column_names, row)) for row in datas]
