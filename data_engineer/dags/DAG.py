import pandas as pd
import datetime as dt
import psycopg2
from airflow import DAG
from elasticsearch import Elasticsearch
from airflow.operators.python_operator import PythonOperator

default_args = {
    'owner'           : 'SpecMatch',
    'depends_on_past' : False,
    'start_date'      : dt(2024, 11, 1),
    'retries'         : 1,
    'retry_delay'     : dt(minutes=5),
}

def fetchData():
    db_user = "airflow"
    db_pass = "airflow"
    db_host = "postgres"
    db_port = "5432"
    db_name = "airflow"

    connection = psycopg2.connect(
        user = db_user,
        password = db_pass,
        host = db_host,
        port = db_port,
        database = db_name
    )
    df = pd.read_sql("SELECT * FROM laptops", connection)
    connection.close()
    df.to_csv('/opt/airflow/dags/laptops_data_raw.csv', index=False)

def cleanData():
    df = pd.read_csv('/opt/airflow/dags/laptops_data_raw.csv')
    df.drop_duplicates()
    # Miss values
    num_cols = df.select_dtypes(include=['int64', 'float64']).columns
    cat_cols = df.select_dtypes(include=['object',]).columns
    for col in num_cols:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna(df[col].median())
            
    for col in cat_cols:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna(df[col].mode()[0])

    #clean 
    df['Ram_GB'] = df['Ram'].str.replace('GB','').astype(int)

    df['Weight_kg'] = df['Weight'].str.replace('kg','').astype(float)

    
    df.to_csv('/opt/airflow/dags/laptops_data_raw.csv', index=False)
    


with DAG(
    dag_id             = 'final_project',
    default_args       = default_args,
    description        = 'Pipeline: PostgreSQL → Data Cleaning',
    schedule_interval  = '10-30/10 9 * * 6',
    catchup            = False,
    tags               = ['final_project', 'postgres'],
) as dag:

    # Task 1
    task_fetch = PythonOperator(
        task_id         = 'fetch_from_postgres',
        python_callable = fetchData,
    )

    # Task 2
    task_clean = PythonOperator(
        task_id         = 'clean_data',
        python_callable = cleanData,
    )


    # Urutan eksekusi
    task_fetch >> task_clean 

