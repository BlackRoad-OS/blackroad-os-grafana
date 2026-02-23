import pytest
from src.dashboard_builder import DashboardBuilder

def test_create_dashboard():
    builder = DashboardBuilder(":memory:")
    dashboard = builder.create_dashboard("Test Dashboard", "Test Desc")
    assert dashboard.title == "Test Dashboard"

def test_push_metric():
    builder = DashboardBuilder(":memory:")
    metric = builder.push_metric("test_metric", 100.0)
    assert metric.name == "test_metric"
    assert metric.value == 100.0
