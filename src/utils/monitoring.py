#src/utils/monitoring.py
import logging
import time
from google.cloud import monitoring_v3
from src.config import settings


class MatchingEngineMonitor:
    """Monitor Matching Engine performance and usage."""

    def __init__(self):
        self.client = monitoring_v3.MetricServiceClient()
        self.project_name = f"projects/{settings.gcp_project_id}"

    def record_upsert_latency(self, batch_size: int, latency: float):
        """Record upsert latency metrics."""
        series = monitoring_v3.TimeSeries()
        series.metric.type = "custom.googleapis.com/matching_engine/upsert_latency"
        series.resource.type = "global"

        point = monitoring_v3.Point()
        point.value.double_value = latency
        point.interval.end_time.seconds = int(time.time())
        series.points = [point]

        self.client.create_time_series(name=self.project_name,
                                       time_series=[series])

    def record_search_latency(self, latency: float):
        """Record search latency metrics."""
        series = monitoring_v3.TimeSeries()
        series.metric.type = "custom.googleapis.com/matching_engine/search_latency"
        series.resource.type = "global"

        point = monitoring_v3.Point()
        point.value.double_value = latency
        point.interval.end_time.seconds = int(time.time())
        series.points = [point]

        self.client.create_time_series(name=self.project_name,
                                       time_series=[series])

    def record_error(self, operation: str, error: str):
        """Record error metrics."""
        series = monitoring_v3.TimeSeries()
        series.metric.type = "custom.googleapis.com/matching_engine/errors"
        series.resource.type = "global"

        point = monitoring_v3.Point()
        point.value.int64_value = 1
        point.interval.end_time.seconds = int(time.time())
        series.points = [point]

        # Add labels for operation and error type
        series.metric.labels["operation"] = operation
        series.metric.labels["error_type"] = error

        self.client.create_time_series(name=self.project_name,
                                       time_series=[series])
