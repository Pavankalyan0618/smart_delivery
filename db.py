import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

def get_conn():
    return psycopg2.connect(
        host=st.secrets["DB_HOST"],
        dbname=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        sslmode=st.secrets["DB_SSLMODE"],
        cursor_factory=RealDictCursor
    )

def fetch_all(sql, params=None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()

def fetch_one(sql, params=None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchone()

def execute(sql, params=None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params or ())
        conn.commit()


