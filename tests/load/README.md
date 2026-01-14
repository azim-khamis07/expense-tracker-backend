# Load Testing

This directory contains load testing infrastructure for the Expense Tracker API using [Locust](https://locust.io/).

## Overview

The load tests simulate realistic user behavior including:
- User registration and authentication
- Transaction creation and listing
- Analytics queries (dashboard, category breakdown, trends)
- User profile access

## Prerequisites

1. **Locust installed**: Already included in `pyproject.toml` as a dev dependency
   ```bash
   poetry install
   ```

2. **API server running**: Start the FastAPI server
   ```bash
   poetry run uvicorn app.main:app --reload
   ```

3. **Database and Redis running**: Required for the API to function
   ```bash
   docker-compose up -d db redis
   ```

## Running Load Tests

### Quick Start (Using Script)

The easiest way to run load tests is using the provided script:

```bash
# Default settings (50 users, 5 spawn rate, 5 minutes)
./scripts/run_load_tests.sh

# Custom configuration
./scripts/run_load_tests.sh 100 10 10m
```

The script will:
- Check if the server is running
- Verify Locust is installed
- Run tests in headless mode
- Generate HTML and CSV reports

### Manual Execution

#### Interactive Mode (Web UI)

Best for exploring and monitoring tests in real-time:

```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

Then open http://localhost:8089 in your browser to:
- Configure number of users and spawn rate
- Start/stop tests
- Monitor real-time statistics
- View charts and graphs

#### Headless Mode (Automated)

Best for CI/CD and automated testing:

```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
  --users 100 --spawn-rate 10 --run-time 5m --headless
```

#### With HTML Report

Generate a detailed HTML report for analysis:

```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
  --users 50 --spawn-rate 5 --run-time 2m --headless \
  --html=tests/load/report.html
```

#### With CSV Export

Export statistics to CSV for further analysis:

```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
  --users 50 --spawn-rate 5 --run-time 5m --headless \
  --html=tests/load/report.html \
  --csv=tests/load/stats
```

This generates:
- `stats_stats.csv` - Request statistics
- `stats_failures.csv` - Failure details
- `stats_exceptions.csv` - Exception details

## Test Configuration

### Task Weights

The load test uses weighted tasks to simulate realistic user behavior:

| Task | Weight | Description |
|------|--------|-------------|
| `list_transactions` | 5 | Most common operation |
| `create_transaction` | 3 | Frequent user action |
| `get_dashboard` | 2 | Common analytics query |
| `get_category_breakdown` | 1 | Periodic analytics query |
| `get_trends` | 1 | Periodic analytics query |
| `get_profile` | 1 | Occasional user action |

### Wait Time

Users wait between 1-3 seconds between tasks to simulate realistic human behavior.

### User Lifecycle

Each simulated user:
1. Registers a new account
2. Logs in and stores authentication token
3. Creates default categories
4. Fetches available categories
5. Performs weighted random tasks

## Performance Benchmarks

### Recommended Test Scenarios

**Light Load** (Development/Staging):
- Users: 20
- Spawn Rate: 2/second
- Duration: 2 minutes

**Medium Load** (Pre-production):
- Users: 50
- Spawn Rate: 5/second
- Duration: 5 minutes

**Heavy Load** (Production capacity):
- Users: 100-200
- Spawn Rate: 10/second
- Duration: 10 minutes

**Stress Test** (Breaking point):
- Users: 500+
- Spawn Rate: 20/second
- Duration: 15 minutes

## Interpreting Results

### Key Metrics

1. **Response Times**
   - Median (50th percentile): Typical response time
   - 95th percentile: 95% of requests complete within this time
   - 99th percentile: Worst-case performance (excluding outliers)

2. **Requests Per Second (RPS)**
   - Total throughput of the API
   - Should increase with user count (up to server limits)

3. **Failure Rate**
   - Percentage of failed requests
   - Should be < 1% for healthy systems

4. **Error Types**
   - Check `stats_failures.csv` for error patterns
   - Common issues: timeout, 500 errors, connection errors

### Performance Targets

For a production-ready API:
- Median response time: < 200ms
- 95th percentile: < 500ms
- 99th percentile: < 1000ms
- Failure rate: < 0.1%

## Troubleshooting

### Server Not Running

```
❌ Server not running at http://localhost:8000
```

**Solution**: Start the API server
```bash
poetry run uvicorn app.main:app --reload
```

### Locust Not Found

```
❌ Locust is not installed
```

**Solution**: Install dependencies
```bash
poetry install
# or
poetry add --group dev locust
```

### High Failure Rate

If you see many failures:
1. Check server logs for errors
2. Verify database connection
3. Check Redis availability
4. Monitor server resources (CPU, memory)
5. Review failure types in `stats_failures.csv`

### Slow Response Times

If response times are high:
1. Check database query performance
2. Verify Redis cache is working
3. Monitor database connection pool
4. Check for N+1 query issues
5. Review server resource usage

## Reports

Reports are generated in the `tests/load/` directory:

- `report.html` - Visual HTML report with charts
- `stats_stats.csv` - Detailed request statistics
- `stats_failures.csv` - Failed request details
- `stats_exceptions.csv` - Exception details (if any)

Open the HTML report in a browser for visual analysis.

## Continuous Integration

To integrate load testing into CI/CD:

```yaml
# Example GitHub Actions
- name: Run Load Tests
  run: |
    poetry run uvicorn app.main:app &
    sleep 5
    poetry run locust -f tests/load/locustfile.py \
      --host=http://localhost:8000 \
      --users 20 --spawn-rate 2 --run-time 1m --headless \
      --html=tests/load/ci_report.html
```

## Further Reading

- [Locust Documentation](https://docs.locust.io/)
- [Performance Testing Best Practices](https://docs.locust.io/en/stable/writing-a-locustfile.html)
- [Load Testing Strategies](https://docs.locust.io/en/stable/configuration.html)
