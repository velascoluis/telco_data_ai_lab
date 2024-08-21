# ............................................................
# PDF generation
# ............................................................


import os
import toml
import markdown

from google.cloud import storage

from google.cloud import bigquery
from weasyprint import HTML

os.environ["GRPC_VERBOSITY"] = "NONE"

with open("../config.toml", "r") as f:
    constants = toml.load(f)

GOOGLE_CLOUD_PROJECT = constants["GCP"]["GOOGLE_CLOUD_PROJECT"]
GOOGLE_CLOUD_LOCATION = constants["GCP"]["GOOGLE_CLOUD_LOCATION"]
GOOGLE_CLOUD_GCS_BUCKET = constants["GCP"]["GOOGLE_CLOUD_GCS_BUCKET"]
GOOGLE_CLOUD_GCS_BUCKET_MULTI_REGION = constants["GCP"][
    "GOOGLE_CLOUD_GCS_BUCKET_MULTI_REGION"
]
GOOGLE_GEMINI_MODEL_15 = constants["VERTEX"]["GOOGLE_GEMINI_MODEL_15"]

GOOGLE_CLOUD_BIGQUERY_PROJECT = constants["BIGQUERY"]["GOOGLE_CLOUD_BIGQUERY_PROJECT"]
GOOGLE_CLOUD_BIGQUERY_DATASET = constants["BIGQUERY"]["GOOGLE_CLOUD_BIGQUERY_DATASET"]


BASE_TABLE_NAME_EVENTS = constants["BIGQUERY"]["BASE_TABLE_NAME_EVENTS"]
BASE_TABLE_NAME_INCIDENTS = constants["BIGQUERY"]["BASE_TABLE_NAME_INCIDENTS"]


def _get_data():
    client = bigquery.Client()
    sql = f"""
           SELECT resolution_description FROM
            `{GOOGLE_CLOUD_BIGQUERY_PROJECT}.{GOOGLE_CLOUD_BIGQUERY_DATASET}.{BASE_TABLE_NAME_INCIDENTS}`
        """
    df = client.query_and_wait(sql).to_dataframe()
    return df


def gen_pdfs():
    df = _get_data()
    storage_client = storage.Client()
    bucket = storage_client.bucket(GOOGLE_CLOUD_GCS_BUCKET_MULTI_REGION)
    for index, row in df.iterrows():
        content_md = row["resolution_description"]
        content_html = markdown.markdown(content_md, extensions=["extra"])
        file_name = f"incident_resolution_{index}.pdf"
        HTML(string=content_html).write_pdf(file_name)
        print(f"Generated PDF: {file_name}")
        blob = bucket.blob(f"rca/{file_name}")
        blob.upload_from_filename(file_name)
        print(
            f"Uploaded {file_name} to GCS bucket {GOOGLE_CLOUD_GCS_BUCKET_MULTI_REGION}"
        )
        os.remove(file_name)


if __name__ == "__main__":
    gen_pdfs()
