
# MaltaShop — Microservices Architecture

A containerised e-commerce order management prototype developed to demonstrate Service-Oriented Architecture (SOA), microservices, asynchronous communication, fault tolerance, and Continuous Integration (CI).

The application uses two independent Flask microservices, RabbitMQ for event-driven messaging, SQLite databases for service-specific data storage, and Docker Compose for local deployment.

## 1. System Architecture

The prototype consists of the following components:

| Component | Responsibility |
|-----------|----------------|
| Frontend | Web interface for creating orders and viewing notifications |
| Order Service | Validates and stores customer orders |
| Outbox Worker | Publishes stored order events to RabbitMQ |
| RabbitMQ | Message broker for asynchronous communication |
| Notification Service | Provides access to stored notifications |
| Notification Worker | Consumes order events and creates notifications |

Each microservice maintains its own database. Services do not directly access each other's database.

### Event Flow

1. A customer submits an order through the frontend.
2. The Order Service validates the request.
3. The order and an `OrderPlaced` event are stored in the Order Service database within one transaction.
4. The Outbox Worker retrieves unpublished events.
5. The event is published to RabbitMQ.
6. The Notification Worker consumes the event.
7. A notification is stored in the Notification Service database.
8. The frontend can retrieve the notification through the Notification API.

The system uses correlation IDs to associate related operations across services.

## 2. Technology Stack

| Technology | Purpose |
|------------|---------|
| Python 3.10 | Backend programming language |
| Flask | REST API development |
| Flask-SQLAlchemy | Database integration |
| SQLite | Independent service databases |
| RabbitMQ | Asynchronous event messaging |
| Pika | RabbitMQ Python client |
| Docker | Application containerisation |
| Docker Compose | Multi-container orchestration |
| Nginx | Frontend hosting and reverse proxy |
| HTML, CSS, JavaScript | Web frontend |
| pytest | Automated testing |
| GitHub Actions | Continuous Integration |

## 3. Project Structure

```text
maltashop-microservices/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── frontend/
│   ├── Dockerfile
│   ├── index.html
│   ├── nginx.conf
│   ├── script.js
│   └── style.css
│
├── order-service/
│   ├── Dockerfile
│   ├── app.py
│   ├── models.py
│   ├── outbox_worker.py
│   ├── publisher.py
│   └── requirements.txt
│
├── notification-service/
│   ├── Dockerfile
│   ├── app.py
│   ├── models.py
│   ├── worker.py
│   └── requirements.txt
│
├── tests/
│   ├── test_order_service.py
│   └── test_notification_service.py
│
├── .gitignore
├── compose.yaml
└── README.md
```

## 4. Prerequisites

Before running the application, install:

- Docker Desktop with Docker Compose support
- Git (for cloning the repository)

Python 3.10 is required only when running the tests locally outside Docker.

## 5. Installation and Execution

### Clone the Repository

```bash
git clone https://github.com/sylmisehrin-hub/maltashop-microservices.git
cd maltashop-microservices
```

### Start the Application

Ensure Docker Desktop is running, then execute:

```bash
docker compose up --build
```

Docker Compose builds the application images and starts the required containers.

To run the application in the background:

```bash
docker compose up --build -d
```

### Access the Application

| Component | URL |
|-----------|-----|
| Web Frontend | http://localhost:8080 |
| Order Service | http://localhost:5001 |
| Notification Service | http://localhost:5002 |
| RabbitMQ Management | http://localhost:15672 |

RabbitMQ uses its default local-development credentials:

- Username: `guest`
- Password: `guest`

These credentials are intended for local demonstration only and should be replaced in a production deployment.

### Check Container Status

```bash
docker compose ps
```

### Stop the Application

```bash
docker compose down
```

This stops and removes the application containers and network while retaining named volumes containing database and broker data.

## 6. REST API Documentation

### Order Service

Base URL:

```text
http://localhost:5001
```

#### Health Check

```http
GET /health
```

Example response:

```json
{
  "status": "healthy"
}
```

#### Create Order

```http
POST /orders
Content-Type: application/json
```

Example request:

```json
{
  "customer_id": 101,
  "product_id": 205,
  "quantity": 2
}
```

Example response:

```json
{
  "order_id": 1,
  "status": "PLACED",
  "correlation_id": "generated-uuid",
  "message": "Order created successfully"
}
```

A successful request returns HTTP `201 Created`.

All three request fields must contain positive integers. Invalid requests return HTTP `400 Bad Request`.

#### Retrieve Order

```http
GET /orders/1
```

Example response:

```json
{
  "order_id": 1,
  "customer_id": 101,
  "product_id": 205,
  "quantity": 2,
  "status": "PLACED"
}
```

If the order does not exist, the service returns HTTP `404 Not Found`.

### Notification Service

Base URL:

```text
http://localhost:5002
```

#### Health Check

```http
GET /health
```

#### Retrieve Notifications

```http
GET /notifications
```

Example response:

```json
[
  {
    "id": 1,
    "order_id": 1,
    "customer_id": 101,
    "correlation_id": "generated-uuid",
    "message": "Order 1 placed successfully"
  }
]
```

Notifications are returned in descending order of notification ID.

## 7. Asynchronous Communication

The application uses RabbitMQ to communicate between the Order Service and Notification Worker.

### OrderPlaced Event

Example event payload:

```json
{
  "event_id": "generated-event-uuid",
  "event_type": "OrderPlaced",
  "order_id": 1,
  "customer_id": 101,
  "product_id": 205,
  "quantity": 2,
  "correlation_id": "generated-correlation-uuid"
}
```

The event is published to the durable `order_events` queue.

Persistent message delivery is requested when publishing events.

The Notification Worker processes events asynchronously, allowing order creation to remain independent of notification processing.

## 8. Reliability and Fault Tolerance

### Transactional Outbox Pattern

The Order Service stores the order and corresponding outbox event within the same database transaction.

A separate worker periodically checks for unpublished events and attempts to publish them to RabbitMQ.

This reduces the risk of losing events when RabbitMQ is temporarily unavailable.

**Verified scenario:** An order was successfully created while RabbitMQ was stopped. After RabbitMQ restarted, the corresponding notification was delivered.

### Idempotent Event Processing

The Notification Service stores a unique `event_id` for every processed event.

If RabbitMQ delivers the same event more than once, the database uniqueness constraint prevents duplicate notification records.

The Notification Worker handles the resulting integrity error and acknowledges the duplicate event.

**Verified scenario:** The same `OrderPlaced` event was published twice. Only one notification was stored, and the worker logged that the duplicate was ignored.

### Dead Letter Queue

Messages that cannot be processed successfully are rejected and routed to a Dead Letter Queue.

RabbitMQ configuration:

| Resource | Name |
|----------|------|
| Main queue | `order_events` |
| Dead-letter exchange | `order_dead_letters` |
| Dead-letter queue | `order_events_dlq` |
| Dead-letter routing key | `failed_order_event` |

**Verified scenario:** An invalid event missing `order_id` was rejected and retained in `order_events_dlq`.

The DLQ supports inspection of failed messages. Automatic retry and replay are not implemented in this prototype.

### Correlation IDs

Each created order is assigned a correlation ID.

The same ID is included in the published event and stored notification, supporting tracing across service boundaries.

## 9. Automated Testing

The project uses pytest to validate API behaviour, database operations, and duplicate-event protection.

The current test suite contains 11 tests covering:

- Order Service health endpoint
- Order creation
- Invalid order validation
- Order retrieval
- Missing-order handling
- Transactional outbox record creation
- Notification Service health endpoint
- Empty notification retrieval
- Notification retrieval
- Notification ordering
- Duplicate event ID rejection

### Run Tests Locally

Create and activate a Python 3.10 virtual environment, then install dependencies:

```bash
python -m pip install -r order-service/requirements.txt
python -m pip install -r notification-service/requirements.txt
python -m pip install pytest
```

Run the test suite:

```bash
python -m pytest tests/ -v
```

At the time of documentation, all 11 tests passed locally.

Additional manual integration tests were performed using Docker and RabbitMQ.

## 10. Continuous Integration

The project uses GitHub Actions for Continuous Integration.

The workflow is defined in:

```text
.github/workflows/ci.yml
```

The pipeline runs on pushes and pull requests.

It contains two jobs:

1. **Python Tests:** Installs dependencies and executes the pytest suite.
2. **Docker Build:** Builds the Docker images using Docker Compose.

The pipeline helps detect test failures and container build problems before further development.

It does not currently deploy the application to a production environment.

## 11. Future Architecture: Order–Payment–Inventory Saga

The current prototype implements Order and Notification services.

For a larger e-commerce platform, the architecture could be extended with Payment and Inventory services.

A proposed saga would follow these stages:

1. Order Service creates a pending order.
2. Payment Service attempts payment authorisation.
3. Inventory Service attempts stock reservation.
4. The order is confirmed when all required operations succeed.
5. If a later operation fails, compensating actions reverse earlier completed operations where possible.

Examples of compensating actions include releasing reserved inventory or refunding an authorised payment.

This saga is a proposed extension and is not implemented in the current prototype.

## 12. Limitations and Future Improvements

The application is an educational prototype rather than a production-ready e-commerce platform.

Potential improvements include:

- Payment and Inventory microservices
- Saga orchestration and compensation handling
- PostgreSQL or another production-oriented database
- API authentication and authorisation
- Centralised logging and distributed tracing
- Prometheus metrics and Grafana dashboards
- Kubernetes deployment and autoscaling
- Automated integration tests for RabbitMQ consumers
- Controlled retries and dead-letter message replay
- Production-grade RabbitMQ credentials and secrets management

## 13. Repository

GitHub:

https://github.com/sylmisehrin-hub/maltashop-microservices

## 14. Project Context

Developed as an academic prototype for the assignment **Service-Oriented Architecture and Microservices Fundamentals**, demonstrating practical microservices design, asynchronous messaging, containerisation, testing, and fault tolerance.
