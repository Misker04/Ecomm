# Distributed E-Commerce Marketplace (TCP-Based)

This project implements a distributed online marketplace system using a TCP-based architecture. It's composed of independent services that communicate through socket connections using JSON-formatted messages. The design follows a frontend–backend structure where frontend servers are stateless and backend database services maintain all application state.

---

## System Architecture

The system consists of the following components:

- **Customer Database Service**  
  Manages buyer and seller accounts, authentication, and session validation.

- **Product Database Service**  
  Stores item information including attributes, prices, and quantities.

- **Buyer Frontend Server**  
  Handles buyer API requests, validates sessions, and forwards operations to backend services.

- **Seller Frontend Server**  
  Handles seller operations such as item registration and product updates.

- **Buyer and Seller CLI Clients**  
  Provide a command-line interface for interacting with the system.

All components communicate strictly over TCP sockets. Although experiments were run on a single machine, the system does not assume colocation and can be deployed on separate machines without code changes.

---

## How to Run the System

Each service runs as a separate process.

### Start Backend Services
```bash
python -m src.customer_db.server --config config/local.yaml
python -m src.product_db.server --config config/local.yaml
```

### Start Frontend Servers
```bash
python -m src.frontend.buyer.server --config config/local.yaml
python -m src.frontend.seller.server --config config/local.yaml
```

### Start Clients
```bash
python -m src.clients.buyer_cli --config config/local.yaml
python -m src.clients.seller_cli --config config/local.yaml
```

---

## Running Performance Experiments

The benchmarking tool simulates concurrent buyers and sellers.

```bash
python -m src.clients.bench.runner --config config/local.yaml --scenario <1|2|3>
```

Scenarios:

- **1** → 1 buyer and 1 seller  
- **2** → 10 buyers and 10 sellers  
- **3** → 100 buyers and 100 sellers  

Each client performs **1000 API operations per run**, and results are averaged across multiple runs.

---

## Assumptions

- Data is stored in memory with optional JSON snapshots for local testing.
- TCP provides reliable communication.
- Each client repeatedly invokes API operations as required by the assignment.
- Advanced marketplace features such as long-term persistent storage are simplified.

---

## Current System State

The system currently supports:

- Account creation and login  
- Session validation  
- Item registration  
- Item search  
- Cart operations  
- Request forwarding between frontend and backend services  
- Performance benchmarking under concurrent load  

All components communicate correctly over TCP. The benchmarking framework is fully operational. 



