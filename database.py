import sqlite3
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv('DB_NAME')
TABLE_NAME = os.getenv('TABLE_NAME')

def get_events_by_type(event_type=None, limit=10):
    conn = sqlite3.connect(DB_NAME)
    
    if event_type and event_type != "all":
        query = f"SELECT * FROM {TABLE_NAME} WHERE detected_type = ? ORDER BY date DESC LIMIT ?"
        df = pd.read_sql_query(query, conn, params=(event_type, limit))
    else:
        query = f"SELECT * FROM {TABLE_NAME} ORDER BY date DESC LIMIT ?"
        df = pd.read_sql_query(query, conn, params=(limit,))
    
    conn.close()
    return df

def get_event_types():
    conn = sqlite3.connect(DB_NAME)
    query = f"SELECT DISTINCT detected_type FROM {TABLE_NAME} WHERE detected_type != ''"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df['detected_type'].tolist()

def search_events(query, limit=10):
    conn = sqlite3.connect(DB_NAME)
    search_query = f"""
    SELECT * FROM {TABLE_NAME} 
    WHERE title LIKE ? OR description LIKE ? 
    ORDER BY date DESC 
    LIMIT ?
    """
    df = pd.read_sql_query(search_query, conn, params=(f'%{query}%', f'%{query}%', limit))
    conn.close()
    return df

def get_stats():
    conn = sqlite3.connect(DB_NAME)
    
    total_events = pd.read_sql_query(f"SELECT COUNT(*) as count FROM {TABLE_NAME}", conn).iloc[0]['count']
    
    type_stats = pd.read_sql_query(
        f"SELECT detected_type, COUNT(*) as count FROM {TABLE_NAME} GROUP BY detected_type ORDER BY count DESC", 
        conn
    )
    
    last_update = pd.read_sql_query(
        f"SELECT MAX(date) as last_date FROM {TABLE_NAME} WHERE date != ''", 
        conn
    ).iloc[0]['last_date']
    
    conn.close()
    
    return {
        'total_events': total_events,
        'type_stats': type_stats,
        'last_update': last_update
    }
