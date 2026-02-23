# BlackRoad OS - Dashboard Builder

Grafana-inspired dashboard-as-code and metrics visualization system.

## Features

- **Dashboard Management**: Create and manage dashboards programmatically
- **Time-Series Metrics**: Store and query metrics with labels
- **Visualization Panels**: Support for timeseries, gauge, stat, bar, table, and heatmap panels
- **Template Variables**: Dynamic dashboard variables
- **JSON Export/Import**: Grafana-compatible JSON format
- **Statistics**: Min/max/avg/p95 calculations

## Architecture

- Python 3.11+
- SQLite backend at `~/.blackroad/dashboards.db`
- Prometheus-compatible data format
- Real-time metric ingestion

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```bash
# Push a metric
python src/dashboard_builder.py push cpu_usage 42.5 --labels '{"node":"server1"}'

# Query metrics
python src/dashboard_builder.py query cpu_usage --from 1h

# Create dashboard
python src/dashboard_builder.py dashboards --create --title "System Monitor"
```
