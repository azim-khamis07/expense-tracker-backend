# How to Run Load Test After Fixes

## Prerequisites

1. **Install Locust** (if not already installed):
   ```bash
   poetry install
   # OR
   pip install locust
   ```

2. **Start API Server**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Enable Test Mode in .env**:
   ```bash
   TEST_MODE=true
   DISABLE_RATE_LIMITS_IN_TEST=true
   # OR multiply limits:
   # RATE_LIMIT_MULTIPLIER=100.0
   ```

4. **Ensure Services are Running**:
   ```bash
   docker-compose up -d db redis
   ```

## Run Load Test

```bash
locust -f tests/load/locustfile.py \
  --host=http://localhost:8000 \
  --users 100 \
  --spawn-rate 10 \
  --headless \
  --run-time 60s \
  --html tests/load/locust_report_after_fixes.html
```

## Expected Results After Fixes

### Before Fixes (from previous test):
- **Failure Rate**: 51.18% (261/510 requests)
- **Rate Limiting**: 95% failure on login, 90% on register
- **Analytics 500 Errors**: 100% failure on dashboard
- **Overall Status**: ❌ CRITICAL ISSUES

### After Fixes (Expected):
- **Failure Rate**: < 1% (target)
- **Rate Limiting**: 0% 429 errors (test mode enabled)
- **Analytics 500 Errors**: 0% (error handling added)
- **Overall Status**: ✅ IMPROVED

## Metrics to Evaluate

1. **Failure Rate**: Should be < 1%
2. **Rate Limiting (429)**: Should be 0% with TEST_MODE enabled
3. **Analytics 500 Errors**: Should be 0% with error handling
4. **Response Times**:
   - Average: < 500ms
   - 95th percentile: < 1s
5. **Requests/Second**: Should be > 10 RPS

## Analysis Commands

After running the test, analyze the results:

```bash
# View HTML report
open tests/load/locust_report_after_fixes.html

# Or analyze text output
python3 -c "
import re
with open('locust_output.txt', 'r') as f:
    content = f.read()
# Parse and analyze...
"
```

## Next Steps

After reviewing results:
1. If failure rate is still > 1%, investigate specific endpoints
2. If analytics still have 500 errors, check error logs
3. If rate limiting still occurs, verify TEST_MODE is enabled
4. Proceed to Priority 3 (Error Monitoring) for better visibility
