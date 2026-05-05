import pandas as pd
import datetime as dt
import psycopg2
from airflow import DAG
from elasticsearch import Elasticsearch
from airflow.operators.python_operator import PythonOperator

default_args = {
    'owner'           : 'SpecMatch',
    'depends_on_past' : False,
    'start_date'      : dt.datetime(2026, 5, 1),
    'retries'         : 1,
    'retry_delay'     : dt.timedelta(minutes=5),
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
    df.columns = df.columns.str.strip().str.lower()
    df = df.drop_duplicates()
    # Miss values
    num_cols = df.select_dtypes(include=['int64', 'float64']).columns
    cat_cols = df.select_dtypes(include=['object',]).columns
    for col in num_cols:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna(df[col].median())
            
    for col in cat_cols:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna(df[col].mode()[0])

    # clean ram
    df['ram_gb'] = df['ram'].str.replace('GB','').astype(int)
    # clean weight
    df['weight_kg'] = df['weight'].str.replace('kg','').astype(float)
    
    # clean memory
    def memory_parse(memory_str):
        total = 0
        parts = memory_str.split('+')

        for part in parts:
            part = part.strip()

            if 'TB' in part:
                num = float(part.split('TB')[0])
                total += num*1024 #Convert ke GB

            elif 'GB' in part:
                num = float(part.split('GB')[0])
                total += num

        return total

    df['storage_gb'] = df['memory'].apply(memory_parse)

    # clean GPU
    def get_gpu_brand(gpu):
        if 'Nvidia' in gpu :
            return 'Nvidia'
        elif 'AMD' in gpu:
            return 'AMD'
        else:
            return 'Intel'

    df['gpu_brand'] = df['gpu'].apply(get_gpu_brand)

    # convert price to idr
    EUR_TO_IDR = 20336.62
    df['price_idr'] = (df['price_euros'] * EUR_TO_IDR).round(0).astype(int)
    df.to_csv('/opt/airflow/dags/laptops_data_clean.csv', index=False)
    


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

