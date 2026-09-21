# Monitoring and Observability - Production Crawler Operations

## Overview

Effective monitoring and observability are essential for operating distributed web crawlers at scale. This guide covers metrics collection, distributed tracing, logging, alerting, and debugging strategies for production systems.

## Observability Architecture

```
┌──────────────────────────────────────────────────────┐
│             Distributed Crawler                      │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ Worker 1 │  │ Worker 2 │  │ Worker N │         │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘         │
└───────┼─────────────┼─────────────┼────────────────┘
        │             │             │
        │  Metrics    │  Traces     │  Logs
        │             │             │
        ▼             ▼             ▼
┌────────────────────────────────────────────────────┐
│            Observability Stack                     │
│                                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │Prometheus│  │  Jaeger  │  │   Loki       │   │
│  │(Metrics) │  │ (Traces) │  │   (Logs)     │   │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘   │
│       │             │                │            │
│       └─────────────┼────────────────┘            │
│                     ▼                              │
│            ┌──────────────┐                       │
│            │   Grafana    │                       │
│            │ (Dashboards) │                       │
│            └──────────────┘                       │
└────────────────────────────────────────────────────┘
```

## Metrics Collection with Prometheus

### 1. Core Metrics

```python
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    start_http_server
)
import time
from typing import Dict, Optional
from functools import wraps

class CrawlerMetrics:
    """
    Prometheus metrics for web crawler
    
    Tracks requests, errors, latency, and resource usage
    """
    
    def __init__(self, job_name: str = "web_crawler"):
        # Request metrics
        self.requests_total = Counter(
            'crawler_requests_total',
            'Total HTTP requests',
            ['domain', 'status', 'method']
        )
        
        self.requests_failed = Counter(
            'crawler_requests_failed_total',
            'Failed HTTP requests',
            ['domain', 'error_type']
        )
        
        # Latency metrics
        self.request_duration = Histogram(
            'crawler_request_duration_seconds',
            'HTTP request duration',
            ['domain'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
        )
        
        # Queue metrics
        self.queue_size = Gauge(
            'crawler_queue_size',
            'URLs in queue',
            ['priority']
        )
        
        self.queue_rate = Counter(
            'crawler_queue_operations_total',
            'Queue operations',
            ['operation']  # 'enqueue' or 'dequeue'
        )
        
        # Content metrics
        self.content_size = Histogram(
            'crawler_content_size_bytes',
            'Downloaded content size',
            ['domain', 'content_type'],
            buckets=[1024, 10240, 102400, 1024000, 10240000]
        )
        
        self.pages_crawled = Counter(
            'crawler_pages_crawled_total',
            'Pages successfully crawled',
            ['domain']
        )
        
        # Rate limiting metrics
        self.rate_limit_delays = Counter(
            'crawler_rate_limit_delays_total',
            'Rate limit delays',
            ['domain']
        )
        
        self.rate_limit_wait_time = Summary(
            'crawler_rate_limit_wait_seconds',
            'Time spent waiting for rate limits',
            ['domain']
        )
        
        # Resource metrics
        self.memory_usage = Gauge(
            'crawler_memory_bytes',
            'Memory usage'
        )
        
        self.cpu_usage = Gauge(
            'crawler_cpu_percent',
            'CPU usage percentage'
        )
        
        self.active_connections = Gauge(
            'crawler_active_connections',
            'Active HTTP connections',
            ['domain']
        )
        
        # Deduplication metrics
        self.duplicates_found = Counter(
            'crawler_duplicates_found_total',
            'Duplicate pages found',
            ['type']  # 'exact' or 'near'
        )
        
        # Storage metrics
        self.storage_operations = Counter(
            'crawler_storage_operations_total',
            'Storage operations',
            ['operation', 'status']  # 'write'/'read', 'success'/'failure'
        )
    
    def record_request(
        self,
        domain: str,
        status: int,
        duration: float,
        size: int,
        content_type: str = "text/html"
    ):
        """Record HTTP request metrics"""
        self.requests_total.labels(
            domain=domain,
            status=str(status),
            method='GET'
        ).inc()
        
        self.request_duration.labels(domain=domain).observe(duration)
        self.content_size.labels(
            domain=domain,
            content_type=content_type
        ).observe(size)
        
        if 200 <= status < 300:
            self.pages_crawled.labels(domain=domain).inc()
    
    def record_error(self, domain: str, error_type: str):
        """Record request failure"""
        self.requests_failed.labels(
            domain=domain,
            error_type=error_type
        ).inc()
    
    def record_rate_limit(self, domain: str, wait_time: float):
        """Record rate limiting event"""
        self.rate_limit_delays.labels(domain=domain).inc()
        self.rate_limit_wait_time.labels(domain=domain).observe(wait_time)
    
    def update_queue_size(self, priority: str, size: int):
        """Update queue size gauge"""
        self.queue_size.labels(priority=priority).set(size)
    
    def record_queue_operation(self, operation: str):
        """Record queue operation"""
        self.queue_rate.labels(operation=operation).inc()
    
    def update_resource_usage(self):
        """Update resource usage metrics"""
        import psutil
        
        process = psutil.Process()
        self.memory_usage.set(process.memory_info().rss)
        self.cpu_usage.set(process.cpu_percent())


# Decorator for automatic metric collection
def track_request(metrics: CrawlerMetrics):
    """Decorator to automatically track request metrics"""
    def decorator(func):
        @wraps(func)
        async def wrapper(url: str, *args, **kwargs):
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            
            start_time = time.time()
            try:
                response = await func(url, *args, **kwargs)
                duration = time.time() - start_time
                
                metrics.record_request(
                    domain=domain,
                    status=response.status,
                    duration=duration,
                    size=len(response.content),
                    content_type=response.headers.get('content-type', 'unknown')
                )
                
                return response
            except Exception as e:
                duration = time.time() - start_time
                metrics.record_error(domain, type(e).__name__)
                raise
        
        return wrapper
    return decorator


# Usage example
metrics = CrawlerMetrics()

# Start metrics server
start_http_server(8000)  # Metrics at http://localhost:8000/metrics

@track_request(metrics)
async def fetch_url(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response.content = await response.read()
            return response

# Manual metrics recording
metrics.update_queue_size('high', 1000)
metrics.record_rate_limit('example.com', 1.5)
metrics.update_resource_usage()
```

### 2. Custom Metrics for Crawl Quality

```python
class CrawlQualityMetrics:
    """
    Metrics for crawl quality and health
    
    Tracks success rates, data quality, and coverage
    """
    
    def __init__(self):
        # Success rate
        self.crawl_success_rate = Gauge(
            'crawler_success_rate',
            'Crawl success rate (0-1)',
            ['domain', 'time_window']
        )
        
        # Data quality
        self.extraction_success = Counter(
            'crawler_extraction_success_total',
            'Successful data extractions',
            ['domain', 'data_type']
        )
        
        self.extraction_failures = Counter(
            'crawler_extraction_failures_total',
            'Failed data extractions',
            ['domain', 'data_type', 'reason']
        )
        
        # Coverage
        self.unique_domains = Gauge(
            'crawler_unique_domains',
            'Number of unique domains crawled'
        )
        
        self.coverage_percentage = Gauge(
            'crawler_coverage_percentage',
            'Percentage of target URLs crawled',
            ['domain']
        )
        
        # Freshness
        self.page_age = Histogram(
            'crawler_page_age_hours',
            'Time since last crawl',
            ['domain'],
            buckets=[1, 6, 12, 24, 72, 168]
        )
    
    def calculate_success_rate(
        self,
        domain: str,
        window_hours: int = 1
    ) -> float:
        """Calculate success rate for domain"""
        # Query Prometheus for success/failure counts
        # This is simplified - in practice, use PromQL
        total = 100  # From Prometheus
        success = 95  # From Prometheus
        
        rate = success / total if total > 0 else 0
        
        self.crawl_success_rate.labels(
            domain=domain,
            time_window=f'{window_hours}h'
        ).set(rate)
        
        return rate
    
    def record_extraction(
        self,
        domain: str,
        data_type: str,
        success: bool,
        reason: Optional[str] = None
    ):
        """Record data extraction attempt"""
        if success:
            self.extraction_success.labels(
                domain=domain,
                data_type=data_type
            ).inc()
        else:
            self.extraction_failures.labels(
                domain=domain,
                data_type=data_type,
                reason=reason or 'unknown'
            ).inc()
    
    def update_coverage(self, domain: str, crawled: int, total: int):
        """Update coverage percentage"""
        percentage = (crawled / total * 100) if total > 0 else 0
        self.coverage_percentage.labels(domain=domain).set(percentage)
```

## Distributed Tracing with OpenTelemetry

### 1. Trace Configuration

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from typing import Optional
import asyncio

class TracingSetup:
    """
    OpenTelemetry tracing setup for distributed crawler
    
    Traces requests across multiple workers and services
    """
    
    def __init__(
        self,
        service_name: str,
        jaeger_host: str = "localhost",
        jaeger_port: int = 6831
    ):
        # Create resource identifying this service
        resource = Resource.create({
            "service.name": service_name,
            "service.version": "1.0.0",
            "deployment.environment": "production"
        })
        
        # Create tracer provider
        provider = TracerProvider(resource=resource)
        
        # Configure Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name=jaeger_host,
            agent_port=jaeger_port,
        )
        
        # Add span processor
        provider.add_span_processor(
            BatchSpanProcessor(jaeger_exporter)
        )
        
        # Set as global tracer provider
        trace.set_tracer_provider(provider)
        
        # Instrument aiohttp automatically
        AioHttpClientInstrumentor().instrument()
        
        self.tracer = trace.get_tracer(__name__)
    
    def get_tracer(self):
        """Get tracer instance"""
        return self.tracer


class TracedCrawler:
    """
    Crawler with distributed tracing
    
    Tracks request flow through entire system
    """
    
    def __init__(self, tracing: TracingSetup):
        self.tracer = tracing.get_tracer()
    
    async def crawl_url(self, url: str) -> Dict:
        """Crawl URL with tracing"""
        # Create span for entire crawl operation
        with self.tracer.start_as_current_span(
            "crawl_url",
            attributes={
                "url": url,
                "crawler.version": "1.0.0"
            }
        ) as span:
            try:
                # Fetch URL (automatically traced by instrumentation)
                content = await self._fetch(url)
                span.set_attribute("response.size", len(content))
                
                # Parse content
                with self.tracer.start_as_current_span("parse_html"):
                    data = await self._parse(content)
                    span.set_attribute("links.found", len(data.get('links', [])))
                
                # Extract data
                with self.tracer.start_as_current_span("extract_data"):
                    extracted = await self._extract(data)
                    span.set_attribute("data.fields", len(extracted))
                
                # Store data
                with self.tracer.start_as_current_span("store_data"):
                    await self._store(url, extracted)
                
                span.set_attribute("status", "success")
                return extracted
                
            except Exception as e:
                span.set_attribute("status", "error")
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                span.record_exception(e)
                raise
    
    async def _fetch(self, url: str) -> str:
        """Fetch URL (traced automatically)"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.text()
    
    async def _parse(self, content: str) -> Dict:
        """Parse HTML"""
        # Parsing logic...
        await asyncio.sleep(0.1)  # Simulate work
        return {'links': ['http://example.com/1', 'http://example.com/2']}
    
    async def _extract(self, data: Dict) -> Dict:
        """Extract structured data"""
        # Extraction logic...
        await asyncio.sleep(0.05)  # Simulate work
        return {'title': 'Example', 'content': '...'}
    
    async def _store(self, url: str, data: Dict):
        """Store data"""
        # Storage logic...
        await asyncio.sleep(0.02)  # Simulate work


# Usage example
tracing = TracingSetup(
    service_name="web-crawler-worker-1",
    jaeger_host="localhost",
    jaeger_port=6831
)

crawler = TracedCrawler(tracing)
await crawler.crawl_url("http://example.com")
```

### 2. Context Propagation

```python
from opentelemetry import trace
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from typing import Dict

class DistributedCrawlCoordinator:
    """
    Coordinates distributed crawling with trace context
    
    Propagates trace context across workers
    """
    
    def __init__(self, tracing: TracingSetup):
        self.tracer = tracing.get_tracer()
        self.propagator = TraceContextTextMapPropagator()
    
    async def schedule_crawl(self, url: str) -> Dict[str, str]:
        """
        Schedule crawl and return trace context
        
        Context can be sent to worker for correlation
        """
        with self.tracer.start_as_current_span("schedule_crawl") as span:
            # Add URL to queue
            span.set_attribute("url", url)
            
            # Extract trace context
            context = {}
            self.propagator.inject(context)
            
            # Send to message queue with context
            message = {
                'url': url,
                'trace_context': context
            }
            
            return message
    
    async def process_crawl(self, message: Dict):
        """
        Process crawl with injected trace context
        
        Continues trace from coordinator
        """
        # Extract trace context
        context = message.get('trace_context', {})
        ctx = self.propagator.extract(context)
        
        # Start span with parent context
        with self.tracer.start_as_current_span(
            "process_crawl",
            context=ctx
        ) as span:
            url = message['url']
            span.set_attribute("url", url)
            
            # Process crawl...
            result = await self._do_crawl(url)
            
            return result
    
    async def _do_crawl(self, url: str):
        """Actual crawl implementation"""
        # Implementation...
        pass
```

## Log Aggregation with Loki

### 1. Structured Logging

```python
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
import sys

class StructuredLogger:
    """
    Structured logger for crawler
    
    Outputs JSON logs compatible with Loki/ELK
    """
    
    def __init__(
        self,
        name: str,
        level: int = logging.INFO,
        extra_fields: Optional[Dict] = None
    ):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # JSON formatter
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(self.JSONFormatter(extra_fields))
        self.logger.addHandler(handler)
        
        self.extra_fields = extra_fields or {}
    
    class JSONFormatter(logging.Formatter):
        """Format logs as JSON"""
        
        def __init__(self, extra_fields: Optional[Dict] = None):
            super().__init__()
            self.extra_fields = extra_fields or {}
        
        def format(self, record: logging.LogRecord) -> str:
            log_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno,
                **self.extra_fields
            }
            
            # Add exception info if present
            if record.exc_info:
                log_data['exception'] = self.formatException(record.exc_info)
            
            # Add extra fields from log record
            if hasattr(record, 'extra_data'):
                log_data.update(record.extra_data)
            
            return json.dumps(log_data)
    
    def log_request(
        self,
        url: str,
        status: int,
        duration: float,
        size: int,
        extra: Optional[Dict] = None
    ):
        """Log HTTP request"""
        self.logger.info(
            "HTTP request completed",
            extra={
                'extra_data': {
                    'event_type': 'http_request',
                    'url': url,
                    'status': status,
                    'duration': duration,
                    'size': size,
                    **(extra or {})
                }
            }
        )
    
    def log_error(
        self,
        message: str,
        error: Exception,
        context: Optional[Dict] = None
    ):
        """Log error with context"""
        self.logger.error(
            message,
            exc_info=error,
            extra={
                'extra_data': {
                    'event_type': 'error',
                    'error_type': type(error).__name__,
                    'error_message': str(error),
                    **(context or {})
                }
            }
        )
    
    def log_crawl_start(self, url: str, metadata: Dict):
        """Log crawl start"""
        self.logger.info(
            "Starting crawl",
            extra={
                'extra_data': {
                    'event_type': 'crawl_start',
                    'url': url,
                    **metadata
                }
            }
        )
    
    def log_crawl_complete(
        self,
        url: str,
        duration: float,
        pages_crawled: int,
        errors: int
    ):
        """Log crawl completion"""
        self.logger.info(
            "Crawl completed",
            extra={
                'extra_data': {
                    'event_type': 'crawl_complete',
                    'url': url,
                    'duration': duration,
                    'pages_crawled': pages_crawled,
                    'errors': errors
                }
            }
        )


# Usage example
logger = StructuredLogger(
    name="crawler",
    level=logging.INFO,
    extra_fields={
        'service': 'web-crawler',
        'instance': 'worker-1',
        'version': '1.0.0'
    }
)

logger.log_request(
    url='http://example.com',
    status=200,
    duration=0.523,
    size=15234,
    extra={'domain': 'example.com'}
)

logger.log_crawl_start(
    url='http://example.com',
    metadata={'priority': 'high', 'depth': 0}
)
```

### 2. Log Correlation

```python
import uuid
from contextvars import ContextVar
from typing import Optional

# Context variable for request ID
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)

class CorrelatedLogger(StructuredLogger):
    """
    Logger with request correlation
    
    Correlates logs across async operations
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def _add_correlation(self, extra_data: Dict) -> Dict:
        """Add correlation ID to log data"""
        request_id = request_id_var.get()
        if request_id:
            extra_data['request_id'] = request_id
        
        # Get trace context if available
        span = trace.get_current_span()
        if span.is_recording():
            ctx = span.get_span_context()
            extra_data['trace_id'] = format(ctx.trace_id, '032x')
            extra_data['span_id'] = format(ctx.span_id, '016x')
        
        return extra_data
    
    def log_request(self, *args, extra: Optional[Dict] = None, **kwargs):
        """Log request with correlation"""
        extra = extra or {}
        extra = self._add_correlation(extra)
        super().log_request(*args, extra=extra, **kwargs)


async def crawl_with_correlation(url: str):
    """Crawl with correlated logs"""
    # Set request ID for this operation
    request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    
    logger = CorrelatedLogger(name="crawler")
    
    logger.log_crawl_start(url, {'request_id': request_id})
    
    # All logs in this context will have same request_id
    # ...
    
    logger.log_crawl_complete(url, 1.5, 10, 0)
```

## Alerting

### 1. Alert Rules (Prometheus)

```yaml
# prometheus_alerts.yml
groups:
  - name: crawler_alerts
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          rate(crawler_requests_failed_total[5m])
          / rate(crawler_requests_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} for {{ $labels.domain }}"
      
      # Slow requests
      - alert: SlowRequests
        expr: |
          histogram_quantile(0.95,
            rate(crawler_request_duration_seconds_bucket[5m])
          ) > 5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Slow requests detected"
          description: "95th percentile latency is {{ $value }}s for {{ $labels.domain }}"
      
      # Queue backlog
      - alert: QueueBacklog
        expr: crawler_queue_size{priority="high"} > 10000
        for: 15m
        labels:
          severity: critical
        annotations:
          summary: "Large queue backlog"
          description: "High priority queue has {{ $value }} items"
      
      # Crawler down
      - alert: CrawlerDown
        expr: up{job="web_crawler"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Crawler instance down"
          description: "Crawler {{ $labels.instance }} is down"
      
      # Low success rate
      - alert: LowSuccessRate
        expr: crawler_success_rate < 0.9
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low crawl success rate"
          description: "Success rate is {{ $value | humanizePercentage }} for {{ $labels.domain }}"
      
      # Memory usage
      - alert: HighMemoryUsage
        expr: crawler_memory_bytes > 8e9  # 8GB
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value | humanize1024 }}"
```

### 2. Alert Manager (Python)

```python
import aiohttp
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Alert:
    """Alert data structure"""
    name: str
    severity: str
    message: str
    labels: Dict[str, str]
    timestamp: datetime
    value: Optional[float] = None

class AlertManager:
    """
    Alert manager for crawler
    
    Sends alerts to various channels (Slack, PagerDuty, etc.)
    """
    
    def __init__(
        self,
        slack_webhook: Optional[str] = None,
        pagerduty_key: Optional[str] = None,
        email_config: Optional[Dict] = None
    ):
        self.slack_webhook = slack_webhook
        self.pagerduty_key = pagerduty_key
        self.email_config = email_config
        
        # Alert state tracking
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_counts: Dict[str, int] = {}
    
    async def send_alert(self, alert: Alert):
        """Send alert to all configured channels"""
        # Check if this is a duplicate
        alert_key = f"{alert.name}:{alert.labels.get('domain', 'all')}"
        
        if alert_key in self.active_alerts:
            # Already alerting, increment count
            self.alert_counts[alert_key] = self.alert_counts.get(alert_key, 0) + 1
            return
        
        # Store alert
        self.active_alerts[alert_key] = alert
        
        # Send to channels
        tasks = []
        
        if self.slack_webhook:
            tasks.append(self._send_slack(alert))
        
        if self.pagerduty_key and alert.severity == 'critical':
            tasks.append(self._send_pagerduty(alert))
        
        if self.email_config:
            tasks.append(self._send_email(alert))
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def resolve_alert(self, alert_name: str, labels: Dict):
        """Mark alert as resolved"""
        alert_key = f"{alert_name}:{labels.get('domain', 'all')}"
        
        if alert_key in self.active_alerts:
            alert = self.active_alerts[alert_key]
            await self._send_resolution(alert)
            del self.active_alerts[alert_key]
            if alert_key in self.alert_counts:
                del self.alert_counts[alert_key]
    
    async def _send_slack(self, alert: Alert):
        """Send alert to Slack"""
        color = {
            'critical': '#ff0000',
            'warning': '#ffa500',
            'info': '#00ff00'
        }.get(alert.severity, '#cccccc')
        
        payload = {
            'attachments': [
                {
                    'color': color,
                    'title': f'🚨 {alert.name}',
                    'text': alert.message,
                    'fields': [
                        {
                            'title': 'Severity',
                            'value': alert.severity,
                            'short': True
                        },
                        {
                            'title': 'Timestamp',
                            'value': alert.timestamp.isoformat(),
                            'short': True
                        },
                        *[
                            {
                                'title': k,
                                'value': v,
                                'short': True
                            }
                            for k, v in alert.labels.items()
                        ]
                    ]
                }
            ]
        }
        
        if alert.value is not None:
            payload['attachments'][0]['fields'].append({
                'title': 'Value',
                'value': str(alert.value),
                'short': True
            })
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.slack_webhook, json=payload) as response:
                if response.status != 200:
                    print(f"Failed to send Slack alert: {response.status}")
    
    async def _send_pagerduty(self, alert: Alert):
        """Send alert to PagerDuty"""
        payload = {
            'routing_key': self.pagerduty_key,
            'event_action': 'trigger',
            'dedup_key': f"{alert.name}:{alert.labels.get('domain', 'all')}",
            'payload': {
                'summary': alert.message,
                'severity': alert.severity,
                'source': 'web-crawler',
                'timestamp': alert.timestamp.isoformat(),
                'custom_details': alert.labels
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://events.pagerduty.com/v2/enqueue',
                json=payload
            ) as response:
                if response.status != 202:
                    print(f"Failed to send PagerDuty alert: {response.status}")
    
    async def _send_resolution(self, alert: Alert):
        """Send alert resolution"""
        if self.slack_webhook:
            payload = {
                'text': f'✅ Resolved: {alert.name}',
                'attachments': [
                    {
                        'color': '#00ff00',
                        'text': f'Alert resolved for {alert.labels}'
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                await session.post(self.slack_webhook, json=payload)


# Usage example
alert_mgr = AlertManager(
    slack_webhook='https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
)

# Send alert
alert = Alert(
    name='HighErrorRate',
    severity='warning',
    message='Error rate is 15% for example.com',
    labels={'domain': 'example.com'},
    timestamp=datetime.utcnow(),
    value=0.15
)

await alert_mgr.send_alert(alert)

# Later, resolve
await alert_mgr.resolve_alert('HighErrorRate', {'domain': 'example.com'})
```

## Dashboard Design (Grafana)

### 1. Overview Dashboard

```python
# Generate Grafana dashboard JSON
dashboard_json = {
    "dashboard": {
        "title": "Web Crawler Overview",
        "panels": [
            {
                "title": "Request Rate",
                "targets": [
                    {
                        "expr": "rate(crawler_requests_total[5m])",
                        "legendFormat": "{{domain}}"
                    }
                ],
                "type": "graph"
            },
            {
                "title": "Error Rate",
                "targets": [
                    {
                        "expr": "rate(crawler_requests_failed_total[5m]) / rate(crawler_requests_total[5m])",
                        "legendFormat": "{{domain}}"
                    }
                ],
                "type": "graph"
            },
            {
                "title": "P95 Latency",
                "targets": [
                    {
                        "expr": "histogram_quantile(0.95, rate(crawler_request_duration_seconds_bucket[5m]))",
                        "legendFormat": "{{domain}}"
                    }
                ],
                "type": "graph"
            },
            {
                "title": "Queue Size",
                "targets": [
                    {
                        "expr": "crawler_queue_size",
                        "legendFormat": "{{priority}}"
                    }
                ],
                "type": "graph"
            },
            {
                "title": "Active Connections",
                "targets": [
                    {
                        "expr": "crawler_active_connections",
                        "legendFormat": "{{domain}}"
                    }
                ],
                "type": "graph"
            },
            {
                "title": "Memory Usage",
                "targets": [
                    {
                        "expr": "crawler_memory_bytes",
                        "legendFormat": "{{instance}}"
                    }
                ],
                "type": "graph"
            }
        ]
    }
}
```

### 2. Per-Domain Dashboard

```json
{
  "dashboard": {
    "title": "Crawler: {{domain}}",
    "templating": {
      "list": [
        {
          "name": "domain",
          "type": "query",
          "query": "label_values(crawler_requests_total, domain)"
        }
      ]
    },
    "panels": [
      {
        "title": "Request Volume",
        "targets": [
          {
            "expr": "rate(crawler_requests_total{domain=\"$domain\"}[5m])"
          }
        ]
      },
      {
        "title": "Status Codes",
        "targets": [
          {
            "expr": "sum by (status) (rate(crawler_requests_total{domain=\"$domain\"}[5m]))"
          }
        ],
        "type": "piechart"
      },
      {
        "title": "Response Time Distribution",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(crawler_request_duration_seconds_bucket{domain=\"$domain\"}[5m]))",
            "legendFormat": "p50"
          },
          {
            "expr": "histogram_quantile(0.95, rate(crawler_request_duration_seconds_bucket{domain=\"$domain\"}[5m]))",
            "legendFormat": "p95"
          },
          {
            "expr": "histogram_quantile(0.99, rate(crawler_request_duration_seconds_bucket{domain=\"$domain\"}[5m]))",
            "legendFormat": "p99"
          }
        ]
      }
    ]
  }
}
```

## Debugging Strategies

### 1. Request Replay

```python
class RequestRecorder:
    """
    Record requests for debugging
    
    Allows replaying failed requests for investigation
    """
    
    def __init__(self, storage_path: str = "/tmp/request_records"):
        self.storage_path = storage_path
        import os
        os.makedirs(storage_path, exist_ok=True)
    
    async def record_request(
        self,
        url: str,
        method: str,
        headers: Dict,
        response_status: int,
        response_headers: Dict,
        response_body: str,
        error: Optional[Exception] = None
    ):
        """Record request details"""
        import hashlib
        import json
        from datetime import datetime
        
        # Generate unique ID
        request_id = hashlib.md5(
            f"{url}{datetime.utcnow()}".encode()
        ).hexdigest()[:16]
        
        record = {
            'id': request_id,
            'timestamp': datetime.utcnow().isoformat(),
            'url': url,
            'method': method,
            'request_headers': headers,
            'response_status': response_status,
            'response_headers': response_headers,
            'response_body': response_body[:10000],  # Limit size
            'error': str(error) if error else None,
            'error_type': type(error).__name__ if error else None
        }
        
        # Save to file
        filename = f"{self.storage_path}/{request_id}.json"
        with open(filename, 'w') as f:
            json.dump(record, f, indent=2)
        
        return request_id
    
    async def replay_request(self, request_id: str):
        """Replay recorded request"""
        import json
        
        filename = f"{self.storage_path}/{request_id}.json"
        with open(filename, 'r') as f:
            record = json.load(f)
        
        print(f"Replaying request: {record['url']}")
        print(f"Original status: {record['response_status']}")
        print(f"Original error: {record['error']}")
        
        # Replay request
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=record['method'],
                url=record['url'],
                headers=record['request_headers']
            ) as response:
                print(f"Replay status: {response.status}")
                body = await response.text()
                
                # Compare responses
                if body != record['response_body'][:len(body)]:
                    print("⚠️  Response body changed")
                else:
                    print("✓ Response body matches")
        
        return record


# Usage
recorder = RequestRecorder()

# Record failed request
try:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            body = await response.text()
            
            if response.status >= 400:
                request_id = await recorder.record_request(
                    url=url,
                    method='GET',
                    headers=dict(response.request_info.headers),
                    response_status=response.status,
                    response_headers=dict(response.headers),
                    response_body=body,
                    error=None
                )
                print(f"Recorded request: {request_id}")
except Exception as e:
    request_id = await recorder.record_request(
        url=url,
        method='GET',
        headers={},
        response_status=0,
        response_headers={},
        response_body='',
        error=e
    )

# Later, replay for debugging
await recorder.replay_request(request_id)
```

### 2. Live Debugging

```python
import asyncio
from typing import Callable, List

class DebugHooks:
    """
    Debug hooks for live debugging
    
    Allows injecting breakpoints and logging at runtime
    """
    
    def __init__(self):
        self.hooks: Dict[str, List[Callable]] = {}
        self.enabled = True
    
    def register_hook(self, event: str, callback: Callable):
        """Register debug hook"""
        if event not in self.hooks:
            self.hooks[event] = []
        self.hooks[event].append(callback)
    
    async def trigger(self, event: str, **kwargs):
        """Trigger debug hooks"""
        if not self.enabled:
            return
        
        if event in self.hooks:
            for hook in self.hooks[event]:
                try:
                    if asyncio.iscoroutinefunction(hook):
                        await hook(**kwargs)
                    else:
                        hook(**kwargs)
                except Exception as e:
                    print(f"Hook error: {e}")


# Global debug hooks
debug = DebugHooks()

# Register hooks
debug.register_hook('request_start', lambda url: print(f"→ {url}"))
debug.register_hook('request_complete', lambda url, status: print(f"← {url} {status}"))
debug.register_hook('error', lambda url, error: print(f"✗ {url} {error}"))

# Use in crawler
async def fetch_with_debug(url: str):
    await debug.trigger('request_start', url=url)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                await debug.trigger('request_complete', url=url, status=response.status)
                return await response.text()
    except Exception as e:
        await debug.trigger('error', url=url, error=e)
        raise
```

## Performance Profiling

```python
import cProfile
import pstats
import io
from functools import wraps
import time

class PerformanceProfiler:
    """
    Performance profiler for crawler
    
    Identifies bottlenecks and optimization opportunities
    """
    
    def __init__(self):
        self.profiler = cProfile.Profile()
        self.timings: Dict[str, List[float]] = {}
    
    def profile_function(self, func):
        """Decorator to profile function"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            
            self.profiler.enable()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                self.profiler.disable()
                elapsed = time.time() - start
                
                func_name = f"{func.__module__}.{func.__name__}"
                if func_name not in self.timings:
                    self.timings[func_name] = []
                self.timings[func_name].append(elapsed)
        
        return wrapper
    
    def get_stats(self) -> str:
        """Get profiling statistics"""
        s = io.StringIO()
        ps = pstats.Stats(self.profiler, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats(20)  # Top 20 functions
        return s.getvalue()
    
    def get_timing_summary(self) -> Dict:
        """Get timing summary"""
        summary = {}
        for func_name, times in self.timings.items():
            summary[func_name] = {
                'count': len(times),
                'total': sum(times),
                'avg': sum(times) / len(times),
                'min': min(times),
                'max': max(times)
            }
        return summary


# Usage
profiler = PerformanceProfiler()

@profiler.profile_function
async def fetch_url(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()

# After crawling
print(profiler.get_stats())
print(profiler.get_timing_summary())
```

## Best Practices

1. **Metrics**: Collect metrics for every significant operation
2. **Tracing**: Use distributed tracing for multi-service debugging
3. **Logging**: Use structured logs with correlation IDs
4. **Alerting**: Set up alerts for critical issues
5. **Dashboards**: Create role-specific dashboards
6. **Testing**: Test monitoring in staging before production
7. **Documentation**: Document alert runbooks

## References

- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Grafana Dashboard Design](https://grafana.com/docs/grafana/latest/best-practices/)
- [The RED Method](https://www.weave.works/blog/the-red-method-key-metrics-for-microservices-architecture/)
- [USE Method](http://www.brendangregg.com/usemethod.html)
