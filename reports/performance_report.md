# Performance Report (PA1)

## Experiment Setup
- Machine(s):
- OS:
- Python version:
- Deployment:
  - CustomerDB: host:port
  - ProductDB: host:port
  - BuyerFrontend: host:port
  - SellerFrontend: host:port
- Note: all communication uses TCP sockets with length-prefixed JSON messages.

## Metrics Definitions
- Response time: time from client invocation to response received.
- Throughput: number of client operations completed at server per second.
- Averaging: each metric averaged over 10 runs; each run uses 1000 API calls per client.

## Search Semantics
Category must match and item quantity > 0. Score is number of exact (case-insensitive) keyword matches between query keywords and item keywords. Results sorted by score desc, net feedback desc, price asc, item_id asc. If no keywords given, returns all items in category.

## Scenario 1 (1 buyer + 1 seller)
- Avg response time:
- Avg throughput:
- Explanation:

## Scenario 2 (10 buyers + 10 sellers)
- Avg response time:
- Avg throughput:
- Explanation:

## Scenario 3 (100 buyers + 100 sellers)
- Avg response time:
- Avg throughput:
- Explanation:

## Insights / Differences Across Scenarios
Discuss bottlenecks: thread scheduling, lock contention in DB services, TCP overhead, CPU limits, etc.
