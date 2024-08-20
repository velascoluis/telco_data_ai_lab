import toml
import pandas as pd
import vertexai

from vertexai.generative_models import GenerativeModel, SafetySetting
from google.cloud import bigquery

CONFIG_TOML_FILE = "../config.toml"


def load_constants():
    with open(CONFIG_TOML_FILE, "r") as f:
        constants = toml.load(f)
    return constants


def run_query(query: str) -> pd.DataFrame:
    client = bigquery.Client()
    df = client.query_and_wait(query).to_dataframe()
    return df


def generate_sql_query(
    question: str,
    table_fqn: str,
    google_cloud_project: str,
    google_cloud_location: str,
    gemini_model: str,
) -> str:

    client = bigquery.Client()
    table = client.get_table(table_fqn)
    table_schema = "Table schema: {}".format(table.schema)
    df = client.query_and_wait(
        f"SELECT * FROM {table_fqn} TABLESAMPLE SYSTEM (10 PERCENT) "
    ).to_dataframe()

    system_instruction = f"You are a expert data analysis with high BigQuery SQL skills, you have to work with a table identified as {table_fqn}"
    prompt = f"Generate a SQL to anser the following question {question} over the BigQuery table with the schema {table_schema}. This is a sample of rows {df}. Output ONLY the SQL query"
    vertexai.init(project=google_cloud_project, location=google_cloud_location)
    safety_settings = [
        SafetySetting(
            category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=SafetySetting.HarmBlockThreshold.BLOCK_ONLY_HIGH,
        ),
        SafetySetting(
            category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=SafetySetting.HarmBlockThreshold.BLOCK_ONLY_HIGH,
        ),
        SafetySetting(
            category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=SafetySetting.HarmBlockThreshold.BLOCK_ONLY_HIGH,
        ),
        SafetySetting(
            category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=SafetySetting.HarmBlockThreshold.BLOCK_ONLY_HIGH,
        ),
    ]
    model = GenerativeModel(gemini_model, system_instruction=[system_instruction])

    response = model.generate_content([prompt], safety_settings=safety_settings)
    return response.text.replace("```sql", "").replace("```", "")
