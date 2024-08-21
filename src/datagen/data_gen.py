# ............................................................
# Data generation
# ............................................................

import pandas as pd
import random
import os
import datetime
import argparse
import toml

import vertexai

from typing import List, Tuple
from tqdm import tqdm
from dataclasses import dataclass

from google.cloud import bigquery
from vertexai.generative_models import GenerativeModel, SafetySetting

os.environ["GRPC_VERBOSITY"] = "NONE"

with open("../config.toml", "r") as f:
    constants = toml.load(f)

GOOGLE_CLOUD_PROJECT = constants["GCP"]["GOOGLE_CLOUD_PROJECT"]
GOOGLE_CLOUD_LOCATION = constants["GCP"]["GOOGLE_CLOUD_LOCATION"]
GOOGLE_GEMINI_MODEL_15 = constants["VERTEX"]["GOOGLE_GEMINI_MODEL_15"]

GOOGLE_CLOUD_BIGQUERY_PROJECT = constants["BIGQUERY"]["GOOGLE_CLOUD_BIGQUERY_PROJECT"]
GOOGLE_CLOUD_BIGQUERY_DATASET = constants["BIGQUERY"]["GOOGLE_CLOUD_BIGQUERY_DATASET"]

BASE_TABLE_NAME_EVENTS = constants["BIGQUERY"]["BASE_TABLE_NAME_EVENTS"]
BASE_TABLE_NAME_INCIDENTS = constants["BIGQUERY"]["BASE_TABLE_NAME_INCIDENTS"]


CSV_EVENTS_PATH = f"{BASE_TABLE_NAME_EVENTS}.csv"
CSV_INCIDENTS_PATH = f"{BASE_TABLE_NAME_INCIDENTS}.csv"


@dataclass
class NetworkElement:
    id: str
    metrics: List[str]


@dataclass
class Metric:
    name: str
    min_value: float
    max_value: float
    round_digits: int = 2


class TelcoDataGenerator:
    def __init__(self, start_date: datetime.datetime, end_date: datetime.datetime):
        self.start_date = start_date
        self.end_date = end_date
        self.network_elements = [
            NetworkElement(
                "Cell Tower-A",
                ["Signal Strength", "Call Drop Rate", "RSRP", "RSRQ", "Throughput"],
            ),
            NetworkElement(
                "Cell Tower-B",
                ["Signal Strength", "Call Drop Rate", "RSRP", "RSRQ", "Throughput"],
            ),
            NetworkElement(
                "Cell Tower-C",
                ["Signal Strength", "Call Drop Rate", "RSRP", "RSRQ", "Throughput"],
            ),
            NetworkElement(
                "Router-1",
                [
                    "Packet Loss",
                    "Latency",
                    "Throughput",
                    "CPU Utilization",
                    "Memory Utilization",
                    "Interface Errors",
                ],
            ),
            NetworkElement(
                "Switch-2",
                [
                    "Packet Loss",
                    "Latency",
                    "Throughput",
                    "CPU Utilization",
                    "Memory Utilization",
                    "Interface Errors",
                ],
            ),
            NetworkElement(
                "OLT-3",
                [
                    "Signal Strength",
                    "Throughput",
                    "Optical Power",
                    "ONU Registration Status",
                ],
            ),
            NetworkElement(
                "DSLAM-4", ["Signal Strength", "Throughput", "SNR Margin", "CRC Errors"]
            ),
            NetworkElement(
                "Core Router-5",
                [
                    "Packet Loss",
                    "Latency",
                    "Throughput",
                    "BGP Peer Status",
                    "CPU Utilization",
                    "Memory Utilization",
                ],
            ),
            NetworkElement(
                "DNS Server-6",
                [
                    "DNS Query Latency",
                    "DNS Query Failure Rate",
                    "CPU Utilization",
                    "Memory Utilization",
                ],
            ),
            NetworkElement(
                "Firewall-7",
                [
                    "Connection Attempts",
                    "Blocked Connections",
                    "CPU Utilization",
                    "Memory Utilization",
                ],
            ),  # Added
            NetworkElement(
                "Load Balancer-8",
                [
                    "Active Connections",
                    "Request Rate",
                    "CPU Utilization",
                    "Memory Utilization",
                ],
            ),
            NetworkElement(
                "VPN Gateway-9",
                [
                    "Connected Users",
                    "VPN Tunnel Status",
                    "CPU Utilization",
                    "Memory Utilization",
                ],
            ),
        ]
        self.metrics = {
            "Signal Strength": Metric("Signal Strength", -110, -50, 0),
            "Call Drop Rate": Metric("Call Drop Rate", 0, 10),
            "Equipment Temperature": Metric("Equipment Temperature", 20, 80, 0),
            "Packet Loss": Metric("Packet Loss", 0, 5),
            "Latency": Metric("Latency", 10, 100, 0),
            "Throughput": Metric("Throughput", 100, 1000, 0),
            "RSRP": Metric("RSRP", -140, -44),
            "RSRQ": Metric("RSRQ", -20, -3),
            "CPU Utilization": Metric("CPU Utilization", 0, 100),
            "Memory Utilization": Metric("Memory Utilization", 0, 100),
            "Optical Power": Metric("Optical Power", -30, 0),
            "SNR Margin": Metric("SNR Margin", 6, 30),
            "DNS Query Latency": Metric("DNS Query Latency", 0, 500),
            "DNS Query Failure Rate": Metric("DNS Query Failure Rate", 0, 10),
            "BGP Peer Status": Metric("BGP Peer Status", 0, 1),
            "Interface Errors": Metric("Interface Errors", 0, 100),
            "ONU Registration Status": Metric("ONU Registration Status", 0, 1),
            "CRC Errors": Metric("CRC Errors", 0, 100),
            "Connection Attempts": Metric("Connection Attempts", 0, 1000),
            "Blocked Connections": Metric("Blocked Connections", 0, 100),
            "Active Connections": Metric("Active Connections", 0, 10000),
            "Request Rate": Metric("Request Rate", 0, 1000),
            "Connected Users": Metric("Connected Users", 0, 1000),
            "VPN Tunnel Status": Metric("VPN Tunnel Status", 0, 1),  # 0: Down, 1: Up
        }
        self.alerts_events = [
            "High Call Drop Rate Alert",
            "High Temperature Alarm",
            "Network Congestion Alert",
            "Equipment Failure Alarm",
            "Customer Complaints",
            "Low Signal Strength Warning",
            "High Packet Loss Alert",
            "High Latency Alert",
            "Low Throughput Warning",
            "High CPU Utilization Warning",
            "High Memory Utilization Warning",
            "Low Optical Power Alarm",
            "Low SNR Margin Warning",
            "High DNS Query Latency Alert",
            "High DNS Query Failure Rate Alert",
            "BGP Peer Down Alert",
            "High Interface Error Rate Alert",
            "ONU Offline Alert",
            "High CRC Error Rate Alert",
            "Unusual Connection Attempt Rate Alert",
            "High Blocked Connection Rate Alert",
            "High Active Connection Count Alert",
            "High Request Rate Alert",
            "VPN Tunnel Down Alert",
            "DoS Attack Suspected",
            "Unauthorized Access Attempt",
            "Service Degradation Reported",
        ]

    def random_timestamp(self) -> datetime.datetime:
        delta = self.end_date - self.start_date
        int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
        random_second = random.randrange(int_delta)
        return self.start_date + datetime.timedelta(seconds=random_second)

    def generate_event(self) -> Tuple[datetime.datetime, str, str, float, str]:
        timestamp = self.random_timestamp()
        network_element = random.choice(self.network_elements)
        metric = random.choice(network_element.metrics)
        value = round(
            random.uniform(
                self.metrics[metric].min_value, self.metrics[metric].max_value
            ),
            self.metrics[metric].round_digits,
        )
        alert_event = random.choice(self.alerts_events) if random.random() < 0.2 else ""
        return timestamp, network_element.id, metric, value, alert_event

    def generate_events(self, no_events: int) -> pd.DataFrame:
        data = [
            self.generate_event()
            for _ in tqdm(range(no_events), desc="Generating Events")
        ]
        return pd.DataFrame(
            data,
            columns=[
                "timestamp",
                "network_element_id",
                "metric",
                "value",
                "event",
            ],
        )

    @staticmethod
    def generate_incident_postmorten(
        incident_name: str, correlated_events: List[str]
    ) -> str:
        if not correlated_events:
            return "No specific events associated with this incident."

        si = "You are an expert network operator, you are filling a incident root cause analysus solution knowlege base"
        prompt = f"Generate a comprehensive description of to solve this particular incident {incident_name} which originated from the following events : {', '.join(correlated_events)}. Add keywords and the correlated events to make the content easily searchable. Add specific details / commands on the resolution step by step guide."
        vertexai.init(project=GOOGLE_CLOUD_PROJECT, location=GOOGLE_CLOUD_LOCATION)
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
        model = GenerativeModel(GOOGLE_GEMINI_MODEL_15, system_instruction=[si])

        response = model.generate_content([prompt], safety_settings=safety_settings)
        return response.text

    @staticmethod
    def generate_incident_name(correlated_events: List[str]) -> str:
        if not correlated_events:
            return "Unknown Incident"

        priority_events = {
            "High Call Drop Rate Alert": "Call Drop Outage",
            "High Temperature Alarm": "Equipment Overheating Incident",
            "Network Congestion Alert": "Network Congestion Incident",
            "Equipment Failure Alarm": "Equipment Failure Incident",
            "Customer Complaints": "Customer Service Issue",
            "Low Signal Strength Warning": "Poor Signal Quality Issue",
            "High Packet Loss Alert": "Network Packet Loss Incident",
            "High Latency Alert": "Network Latency Issue",
            "Low Throughput Warning": "Low Network Throughput Issue",
            "High CPU Utilization Warning": "High CPU Load",
            "High Memory Utilization Warning": "High Memory Load",
            "Low Optical Power Alarm": "Optical Power Degradation",
            "Low SNR Margin Warning": "Low Signal-to-Noise Ratio",
            "High DNS Query Latency Alert": "Slow DNS Resolution",
            "High DNS Query Failure Rate Alert": "DNS Resolution Failures",
            "BGP Peer Down Alert": "BGP Peering Issue",
            "High Interface Error Rate Alert": "Network Interface Errors",
            "ONU Offline Alert": "ONU Connectivity Issue",
            "High CRC Error Rate Alert": "Data Transmission Errors",
            "Unusual Connection Attempt Rate Alert": "Potential Security Threat",
            "High Blocked Connection Rate Alert": "Potential Security Threat",
            "High Active Connection Count Alert": "High Network Load",
            "High Request Rate Alert": "High System Load",
            "VPN Tunnel Down Alert": "VPN Connectivity Issue",
            "DoS Attack Suspected": "Security Incident",
            "Unauthorized Access Attempt": "Security Incident",
            "Service Degradation Reported": "Service Disruption",
        }

        for event in correlated_events:
            if event in priority_events:
                return priority_events[event]

        return "Network Performance Issue"

    def generate_incidents(
        self, df_main: pd.DataFrame, no_incidents: int
    ) -> pd.DataFrame:
        incidents = []
        for _ in tqdm(range(no_incidents), desc="Generating Incidents"):
            start_time = self.random_timestamp()
            end_time = start_time + datetime.timedelta(minutes=random.randint(30, 120))

            correlated_events = (
                df_main[
                    (df_main["timestamp"] >= start_time)
                    & (df_main["timestamp"] <= end_time)
                    & (df_main["event"] != "")
                ]["event"]
                .unique()
                .tolist()
            )
            correlated_events = [x for x in correlated_events if x is not None]
            incident_name = self.generate_incident_name(correlated_events)
            incident_description = self.generate_incident_postmorten(
                incident_name, correlated_events
            )
            incidents.append(
                [
                    incident_name,
                    start_time,
                    end_time,
                    correlated_events,
                    incident_description,
                ]
            )

        return pd.DataFrame(
            incidents,
            columns=[
                "incident_name",
                "start_time",
                "end_time",
                "correlated_events",
                "resolution_description",
            ],
        )


def load_data_bq(df, table_fqn: str):
    client = bigquery.Client()
    job = client.load_table_from_dataframe(df, table_fqn)
    job.result()


def gen_data(
    generate_events: bool, generate_incidents: bool, no_events: int, no_incidents: int
):
    start_date = datetime.datetime(2023, 8, 10, 0, 0, 0)
    end_date = datetime.datetime(2023, 8, 12, 23, 59, 59)

    generator = TelcoDataGenerator(start_date, end_date)

    if generate_events:
        print("Generating events ..")
        df_main = generator.generate_events(no_events)
        df_main.to_csv(CSV_EVENTS_PATH, index=False)
        load_data_bq(
            df_main,
            f"{GOOGLE_CLOUD_BIGQUERY_PROJECT}.{GOOGLE_CLOUD_BIGQUERY_DATASET}.{BASE_TABLE_NAME_EVENTS}",
        )
        print("Ammending event types ..")
        client = bigquery.Client()
        sql = f"""
            CREATE OR REPLACE TABLE `{GOOGLE_CLOUD_BIGQUERY_PROJECT}.{GOOGLE_CLOUD_BIGQUERY_DATASET}.{BASE_TABLE_NAME_EVENTS}`
            AS SELECT * EXCEPT(timestamp),CAST(timestamp as TIMESTAMP) AS timestamp FROM
            `{GOOGLE_CLOUD_BIGQUERY_PROJECT}.{GOOGLE_CLOUD_BIGQUERY_DATASET}.{BASE_TABLE_NAME_EVENTS}`
        """
        _ = client.query(sql)
        print("Type ammended loaded")
    else:
        print("Loading events from BQ ..")
        client = bigquery.Client()
        sql = f"""
            SELECT *
            FROM `{GOOGLE_CLOUD_BIGQUERY_PROJECT}.{GOOGLE_CLOUD_BIGQUERY_DATASET}.{BASE_TABLE_NAME_EVENTS}` TABLESAMPLE SYSTEM (10 PERCENT)
        """
        df_main = client.query(sql).to_dataframe()
        df_main["timestamp"] = df_main["timestamp"].dt.tz_localize(None)
        print("Events loaded")

    if generate_incidents:
        print("Generating incidents ..")
        incidents_generated = 0
        while incidents_generated < no_incidents:
            batch_size = min(20, no_incidents - incidents_generated)
            df_incidents = generator.generate_incidents(df_main, batch_size)
            df_incidents.to_csv(
                CSV_INCIDENTS_PATH,
                index=False,
                mode="a",
                header=incidents_generated == 0,
            )
            df_incidents["end_time"] = pd.to_datetime(df_incidents["end_time"])
            df_incidents["start_time"] = pd.to_datetime(df_incidents["start_time"])
            df_incidents["correlated_events"] = df_incidents[
                "correlated_events"
            ].astype("str")
            load_data_bq(
                df_incidents,
                f"{GOOGLE_CLOUD_BIGQUERY_PROJECT}.{GOOGLE_CLOUD_BIGQUERY_DATASET}.{BASE_TABLE_NAME_INCIDENTS}",
            )

            print("Ammending incident types ..")
            client = bigquery.Client()
            sql = f"""
                CREATE OR REPLACE TABLE `{GOOGLE_CLOUD_BIGQUERY_PROJECT}.{GOOGLE_CLOUD_BIGQUERY_DATASET}.{BASE_TABLE_NAME_INCIDENTS}`
                AS SELECT * EXCEPT(`start_time`, `end_time`),
                CAST(`start_time` AS TIMESTAMP) as `start_time`,
                CAST(`end_time` AS TIMESTAMP) as `end_time`
                FROM `{GOOGLE_CLOUD_BIGQUERY_PROJECT}.{GOOGLE_CLOUD_BIGQUERY_DATASET}.{BASE_TABLE_NAME_INCIDENTS}`
            """
            _ = client.query(sql)
            print("Type ammended loaded")
            incidents_generated += batch_size
    else:
        print("Loading incidents from BQ ..")
        client = bigquery.Client()
        sql = f"""
            SELECT *
            FROM `{GOOGLE_CLOUD_BIGQUERY_PROJECT}.{GOOGLE_CLOUD_BIGQUERY_DATASET}.{BASE_TABLE_NAME_INCIDENTS}`
        """
        df_incidents = client.query(sql).to_dataframe()
        print("Incidents loaded")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate events and incidents.")
    parser.add_argument(
        "--generate_events",
        action="store_true",
        help="Set this flag to generate new events. If not set, events will be loaded from BigQuery.",
    )
    parser.add_argument(
        "--generate_incidents",
        action="store_true",
        help="Set this flag to generate new incidents. If not set, incidents will be loaded from BigQuery.",
    )
    parser.add_argument(
        "--no_events",
        type=int,
        default=100000000,
        help="Number of events to generate (only used if --generate_events is set).",
    )
    parser.add_argument(
        "--no_incidents",
        type=int,
        default=5000,
        help="Number of incidents to generate.",
    )

    args = parser.parse_args()
    print(f"args: {args}")
    gen_data(
        args.generate_events, args.generate_incidents, args.no_events, args.no_incidents
    )
