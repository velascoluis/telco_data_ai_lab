# ............................................................
# STREAMLIT App
# ............................................................

import streamlit as st
import pandas as pd

from google.cloud import bigquery


GOOGLE_CLOUD_BIGQUERY_DATASET_MULTI_REGION = "rca_data_us"
BASE_TABLE_NAME_INCIDENTS = "telco_rca_incidents"


def run_query(query: str) -> pd.DataFrame:
    client = bigquery.Client()
    df = client.query_and_wait(query).to_dataframe()
    return df


# .... App

st.markdown("### Issue diagnosis using Gen AI with BigQuery")
with st.form("rag_form"):
    user_query = st.text_input("Enter your problem")

    query_search = f"""
        SELECT *
        FROM VECTOR_SEARCH(
          TABLE `{GOOGLE_CLOUD_BIGQUERY_DATASET_MULTI_REGION}.{BASE_TABLE_NAME_INCIDENTS}_docs_embedded`, 'ml_generate_embedding_result',
          (
          SELECT ml_generate_embedding_result, content AS query
          FROM ML.GENERATE_EMBEDDING(
          MODEL `{GOOGLE_CLOUD_BIGQUERY_DATASET_MULTI_REGION}.gecko_embedder`,
          (SELECT '{user_query}' AS content))
          ),
          top_k => 5);"""

    query_rag = f"""SELECT ml_generate_text_result.candidates[0].content.parts[0].text
              FROM ML.GENERATE_TEXT(
                MODEL `{GOOGLE_CLOUD_BIGQUERY_DATASET_MULTI_REGION}.gemini_model`,
                (
                  SELECT CONCAT(
                    'Detail how to solve the issue using the following articles, produce a step by step guide ',
                    STRING_AGG(base.content)
                    ) AS prompt,
                  FROM VECTOR_SEARCH(
                TABLE `{GOOGLE_CLOUD_BIGQUERY_DATASET_MULTI_REGION}.{BASE_TABLE_NAME_INCIDENTS}_docs_embedded`, 'ml_generate_embedding_result',
                (
                SELECT ml_generate_embedding_result, content AS query
                FROM ML.GENERATE_EMBEDDING(
                MODEL `{GOOGLE_CLOUD_BIGQUERY_DATASET_MULTI_REGION}.gecko_embedder`,
                (SELECT '{user_query}' AS content))
                ),
                top_k => 5)
                ));"""
    run_rag = st.form_submit_button("Launch RAG on BQ")
    if run_rag:
        df_rag = run_query(query_rag)
        df_search = run_query(query_search)
        st.text("RAG result")
        st.dataframe(df_rag, use_container_width=True)
        st.text("Documents used")
        st.dataframe(df_search, use_container_width=True)
