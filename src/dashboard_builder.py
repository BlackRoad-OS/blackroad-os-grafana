"""
BlackRoad Dashboard Builder - Grafana-inspired metrics visualization
Dashboard-as-code for time-series data and monitoring
"""
import sqlite3
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from enum import Enum
from pathlib import Path
import statistics


class PanelType(Enum):
    TIMESERIES = "timeseries"
    GAUGE = "gauge"
    STAT = "stat"
    BAR = "bar"
    TABLE = "table"
    TEXT = "text"
    HEATMAP = "heatmap"


class VariableType(Enum):
    QUERY = "query"
    CUSTOM = "custom"
    INTERVAL = "interval"


@dataclass
class Position:
    """Panel position and size on dashboard grid"""
    x: int = 0
    y: int = 0
    w: int = 12
    h: int = 8


@dataclass
class Panel:
    """Represents a visualization panel"""
    id: str
    title: str
    type: str
    datasource: str = "prometheus"
    query: str = ""
    options: Dict = field(default_factory=dict)
    position: Position = field(default_factory=Position)


@dataclass
class Variable:
    """Template variable for dashboard"""
    name: str
    type: str = "query"
    query: str = ""
    current_value: str = ""


@dataclass
class Dashboard:
    """Represents a monitoring dashboard"""
    id: str
    uid: str
    title: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    panels: List[Panel] = field(default_factory=list)
    variables: List[Variable] = field(default_factory=list)
    refresh_interval: str = "30s"
    time_range: str = "1h"
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Metric:
    """Time-series metric data point"""
    name: str
    labels: Dict[str, str] = field(default_factory=dict)
    value: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class DashboardBuilder:
    """Grafana-inspired dashboard builder and metrics system"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path == ":memory:":
            self.db_path = ":memory:"
        else:
            self.db_path = db_path or str(Path.home() / ".blackroad" / "dashboards.db")
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database schema"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS dashboards (
                id TEXT PRIMARY KEY,
                uid TEXT UNIQUE,
                title TEXT NOT NULL,
                description TEXT,
                tags TEXT,
                panels TEXT,
                variables TEXT,
                refresh_interval TEXT DEFAULT '30s',
                time_range TEXT DEFAULT '1h',
                created_at TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                labels TEXT,
                value REAL,
                timestamp TEXT,
                created_at TEXT,
                UNIQUE(name, labels, timestamp)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS metric_stats (
                name TEXT PRIMARY KEY,
                min_value REAL,
                max_value REAL,
                avg_value REAL,
                p95_value REAL,
                count INTEGER,
                last_updated TEXT
            )
        """)

        conn.commit()
        conn.close()

    def create_dashboard(self, title: str, description: str = "", tags: List[str] = None,
                        refresh_interval: str = "30s", time_range: str = "1h") -> Dashboard:
        """Create a new dashboard"""
        import hashlib
        uid = hashlib.md5(title.encode()).hexdigest()[:8]
        dashboard_id = hashlib.md5(f"{title}{datetime.now().isoformat()}".encode()).hexdigest()[:8]

        dashboard = Dashboard(
            id=dashboard_id,
            uid=uid,
            title=title,
            description=description,
            tags=tags or [],
            refresh_interval=refresh_interval,
            time_range=time_range,
            created_at=datetime.now()
        )

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT INTO dashboards VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dashboard.id, dashboard.uid, dashboard.title, dashboard.description,
            json.dumps(dashboard.tags), json.dumps([]), json.dumps([]),
            dashboard.refresh_interval, dashboard.time_range,
            dashboard.created_at.isoformat()
        ))
        conn.commit()
        conn.close()
        return dashboard

    def add_panel(self, dashboard_id: str, title: str, panel_type: str,
                 query: str, datasource: str = "prometheus",
                 position: Optional[Position] = None, options: Dict = None) -> Panel:
        """Add a panel to a dashboard"""
        import hashlib
        panel_id = hashlib.md5(f"{dashboard_id}/{title}".encode()).hexdigest()[:8]
        pos = position or Position()

        panel = Panel(
            id=panel_id,
            title=title,
            type=panel_type,
            datasource=datasource,
            query=query,
            options=options or {},
            position=pos
        )

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("SELECT panels FROM dashboards WHERE id = ?", (dashboard_id,))
        result = c.fetchone()
        if result:
            panels = json.loads(result[0])
            panels.append(asdict(panel))
            c.execute("UPDATE dashboards SET panels = ? WHERE id = ?",
                     (json.dumps(panels), dashboard_id))
            conn.commit()
        conn.close()
        return panel

    def add_variable(self, dashboard_id: str, name: str, query: str,
                    var_type: str = "query") -> Variable:
        """Add a template variable to a dashboard"""
        variable = Variable(name=name, type=var_type, query=query)

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("SELECT variables FROM dashboards WHERE id = ?", (dashboard_id,))
        result = c.fetchone()
        if result:
            variables = json.loads(result[0])
            variables.append(asdict(variable))
            c.execute("UPDATE dashboards SET variables = ? WHERE id = ?",
                     (json.dumps(variables), dashboard_id))
            conn.commit()
        conn.close()
        return variable

    def push_metric(self, name: str, value: float, labels: Dict[str, str] = None) -> Metric:
        """Store a metric data point"""
        metric = Metric(
            name=name,
            labels=labels or {},
            value=value,
            timestamp=datetime.now()
        )

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        labels_json = json.dumps(labels or {})
        c.execute("""
            INSERT OR IGNORE INTO metrics (name, labels, value, timestamp, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (name, labels_json, value, metric.timestamp.isoformat(), datetime.now().isoformat()))

        conn.commit()
        conn.close()
        return metric

    def query_metrics(self, name: str, labels: Dict[str, str] = None,
                     from_ts: Optional[datetime] = None, to_ts: Optional[datetime] = None,
                     step_s: int = 60) -> List[Tuple[str, float]]:
        """Query metric time series data"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        labels_json = json.dumps(labels or {})

        if from_ts and to_ts:
            c.execute("""
                SELECT timestamp, value FROM metrics
                WHERE name = ? AND labels = ? AND timestamp BETWEEN ? AND ?
                ORDER BY timestamp ASC
            """, (name, labels_json, from_ts.isoformat(), to_ts.isoformat()))
        else:
            c.execute("""
                SELECT timestamp, value FROM metrics WHERE name = ? AND labels = ?
                ORDER BY timestamp ASC
            """, (name, labels_json))

        results = c.fetchall()
        conn.close()
        return [(r[0], r[1]) for r in results]

    def export_json(self, dashboard_id: str) -> str:
        """Export dashboard as Grafana-compatible JSON"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("SELECT * FROM dashboards WHERE id = ?", (dashboard_id,))
        row = c.fetchone()
        conn.close()

        if not row:
            return "{}"

        dashboard_json = {
            "id": row[0],
            "uid": row[1],
            "title": row[2],
            "description": row[3],
            "tags": json.loads(row[4]),
            "panels": json.loads(row[5]),
            "variables": json.loads(row[6]),
            "refresh": row[7],
            "time": {"from": "now-" + row[8], "to": "now"},
            "created_at": row[9]
        }
        return json.dumps(dashboard_json, indent=2)

    def import_json(self, json_str: str) -> Dashboard:
        """Import dashboard from JSON"""
        import hashlib
        data = json.loads(json_str)

        dashboard_id = hashlib.md5(data.get("title", "").encode()).hexdigest()[:8]
        dashboard = Dashboard(
            id=dashboard_id,
            uid=data.get("uid", dashboard_id),
            title=data.get("title", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            refresh_interval=data.get("refresh", "30s"),
            time_range=data.get("time", {}).get("from", "1h"),
            created_at=datetime.now()
        )

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO dashboards VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dashboard.id, dashboard.uid, dashboard.title, dashboard.description,
            json.dumps(dashboard.tags), json.dumps(data.get("panels", [])),
            json.dumps(data.get("variables", [])),
            dashboard.refresh_interval, dashboard.time_range,
            dashboard.created_at.isoformat()
        ))
        conn.commit()
        conn.close()
        return dashboard

    def get_current_value(self, name: str, labels: Dict[str, str] = None) -> Optional[float]:
        """Get the latest metric value"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        labels_json = json.dumps(labels or {})
        c.execute("""
            SELECT value FROM metrics
            WHERE name = ? AND labels = ?
            ORDER BY timestamp DESC LIMIT 1
        """, (name, labels_json))

        result = c.fetchone()
        conn.close()
        return result[0] if result else None

    def get_stats(self, name: str, labels: Dict[str, str] = None,
                 from_ts: Optional[datetime] = None) -> Dict:
        """Calculate statistics for a metric"""
        metrics = self.query_metrics(name, labels, from_ts)

        if not metrics:
            return {"error": "No data found"}

        values = [m[1] for m in metrics]
        sorted_values = sorted(values)

        p95_idx = int(len(sorted_values) * 0.95)

        stats = {
            "name": name,
            "labels": labels or {},
            "min": min(values),
            "max": max(values),
            "avg": statistics.mean(values),
            "p95": sorted_values[p95_idx] if p95_idx < len(sorted_values) else sorted_values[-1],
            "count": len(values)
        }

        return stats


if __name__ == "__main__":
    print("BlackRoad Dashboard Builder")
