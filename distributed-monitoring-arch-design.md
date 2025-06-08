# Distributed Monitoring Architecture Design

## Introduction

This document outlines the architecture design for a distributed monitoring system capable of tracking connectivity and latency metrics across multiple geographically dispersed locations. The system is designed to provide real-time visibility into network performance and service availability from a global perspective, consolidating data from various monitoring agents into a centralized reporting platform. Overall, it's underlying architecture will much different than original single-node monitoring systems, as it needs to handle data from multiple sources, ensure secure transmission, and provide real-time insights across different regions.

For demonstration purposes, we will assume that this system will build on top of Azure and consider three regions: East-US (Virginia), UK West (Cardiff), and West US  (California). Each region will have its own monitoring agent that collects data from local sites and sends it to a central command for aggregation and analysis.

## Architecture Diagram

```mermaid
graph TB
    %% Regional Agents
    subgraph "Azure Regions"
        subgraph "East US (Virginia)"
            ACI1[Azure Container Instances<br/>Site Guard Agent]
            STOR1[Storage Account<br/>Agent Logs]
        end

        subgraph "West Europe (Netherlands)"
            ACI2[Azure Container Instances<br/>Site Guard Agent]
            STOR2[Storage Account<br/>Agent Logs]
        end

        subgraph "West US (California)"
            ACI3[Azure Container Instances<br/>Site Guard Agent]
            STOR3[Storage Account<br/>Agent Logs]
        end
    end

    %% Central Hub - Simplified
    subgraph "Central Hub - East US 2"
        subgraph "API & Processing"
            APIM[API Management<br/>Gateway & Security]
            FUNC[Azure Functions<br/>Data Processing & API]
        end

        subgraph "Data Storage"
            COSMOS[Cosmos DB<br/>Document Storage]
            ADX[Azure Data Explorer<br/>Time Series Analytics]
            BLOB[Blob Storage<br/>Log Archives]
        end

        subgraph "Real-time & Caching"
            REDIS[Azure Cache for Redis<br/>Real-time Status]
            SB[Service Bus<br/>Message Queue]
        end

        subgraph "Monitoring & Dashboards"
            AI[Application Insights<br/>APM & Telemetry]
            GRAFANA[Azure Managed Grafana<br/>Dashboards]
            LA[Log Analytics<br/>Centralized Logging]
        end

        subgraph "Alerting"
            ALERT[Logic Apps<br/>Alert Processing]
            TEAMS[Teams Connector<br/>Notifications]
            EMAIL[SendGrid<br/>Email Alerts]
        end
    end

    %% Security
    subgraph "Security & Identity"
        AAD[Azure Entra ID<br/>Authentication]
        KV[Key Vault<br/>Secrets & Certificates]
    end

    %% Data Flow - Simplified
    ACI1 -->|HTTPS + JWT| APIM
    ACI2 -->|HTTPS + JWT| APIM
    ACI3 -->|HTTPS + JWT| APIM

    APIM --> FUNC
    FUNC --> SB
    FUNC --> COSMOS
    FUNC --> ADX
    FUNC --> REDIS
    FUNC --> BLOB

    SB --> ALERT
    ALERT --> TEAMS
    ALERT --> EMAIL

    REDIS --> GRAFANA
    ADX --> GRAFANA
    FUNC --> AI
    AI --> LA

    %% Security Connections
    ACI1 -.-> AAD
    ACI2 -.-> AAD
    ACI3 -.-> AAD
    APIM -.-> KV
    FUNC -.-> KV

    %% Styling
    classDef agent fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef compute fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef data fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef security fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef alert fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px

    class ACI1,ACI2,ACI3 agent
    class APIM,FUNC compute
    class COSMOS,ADX,BLOB,REDIS,SB data
    class AAD,KV security
    class ALERT,TEAMS,EMAIL alert
```

## 🔄 Communication Flow Overview

```mermaid
sequenceDiagram
    participant Agent as Site Guard Agent<br/>(Regional ACI)
    participant AAD as Azure Entra ID
    participant APIM as API Management
    participant FUNC as Azure Functions
    participant SB as Service Bus
    participant KV as Key Vault

    Note over Agent: Agent starts up and authenticates
    Agent->>+AAD: Request access token<br/>(Client Credentials Flow)
    AAD-->>-Agent: JWT access token

    loop Every 30-60 seconds
        Note over Agent: Collect monitoring data
        Agent->>Agent: Check configured sites

        Note over Agent: Send batch to central hub
        Agent->>+APIM: POST /api/v1/monitoring/ingest<br/>Authorization: Bearer {JWT}<br/>X-Region-Code: eastus<br/>X-Agent-ID: agent-001

        APIM->>APIM: Validate JWT token
        APIM->>APIM: Apply rate limiting
        APIM->>APIM: Check subscription key

        APIM->>+FUNC: Forward request to ingestion function
        FUNC->>KV: Get processing secrets
        FUNC->>FUNC: Validate and enrich data
        FUNC->>SB: Queue for async processing
        FUNC-->>-APIM: 202 Accepted
        APIM-->>-Agent: Success response

        Note over SB: Async processing continues
        SB->>FUNC: Trigger processing function
        FUNC->>FUNC: Store in Cosmos DB, ADX, Redis
    end
```

## Regional Agents

Each monitoring application runs in a separate Azure Container Instance (ACI) within its respective region. The agents are responsible for:
Collecting connectivity and latency metrics from local websites and services.

## Central Hub - API & Processing Layer

Azure API Management (APIM) serves as the secure gateway for all incoming data from regional agents. It handles:

- Ingesting data from regional agents
- Rate limiting and throttling to prevent abuse
- Authentication and authorization using JWT tokens
Azure Functions provide serverless compute capabilities for:
- Processing incoming data from agents
- Validating and enriching data
- Storing processed data into various storage solutions

This layer transforms regional monitoring data into processed, validated information while ensuring secure, scalable, and reliable communication between distributed agents and the central data platform.

## Data Storage Layer

Data storage layer consists of multiple components to handle different types of data:

- **Cosmos DB**: Stores structured monitoring data in a document format, allowing for fast queries and global distribution.
- **Azure Data Explorer (ADX)**: Optimized for time-series analytics, it provides powerful querying capabilities for large volumes of telemetry data.
- **Blob Storage**: Used for long-term archival of raw logs and data, ensuring cost-effective storage for large datasets.

## Real-time & Caching Layer

The Real-time & Caching Layer provides performance optimization and asynchronous message handling for our distributed monitoring system:

- **Azure Cache for Redis**: Provides real-time caching of status and metrics, enabling fast access to frequently queried data.
- **Service Bus**: Acts as a message queue for decoupling data ingestion from processing, allowing for asynchronous handling of incoming data and ensuring reliability in message delivery.

## Monitoring & Dashboards Layer

This layer provides real-time monitoring, visualization, and alerting capabilities:

- **Application Insights**: Monitors application performance and provides telemetry data for diagnostics and troubleshooting.
- **Azure Managed Grafana**: Offers customizable dashboards for visualizing metrics and performance data from various sources, including Cosmos DB and ADX.
- **Log Analytics**: Centralized logging solution that aggregates logs from all components, enabling powerful querying and analysis of system behavior.
- **Azure Monitor**: Provides comprehensive monitoring capabilities across all Azure resources, including alerts and metrics.

## Alerting Layer

The Alerting Layer is responsible for processing alerts and notifications based on monitoring data:

- **Logic Apps**: Automates alert processing workflows, allowing for complex logic and integration with other services.
- **Teams Connector**: Sends real-time notifications to Microsoft Teams channels for immediate visibility into critical issues.
- **SendGrid**: Used for sending email alerts to stakeholders, ensuring that critical notifications reach the right people.

## Security & Identity Layer

Azure Entra ID: Centralized identity management for:

- Authentication of agents and services
- Role-based access control (RBAC)

Key Vault: Secure storage for:

- Secrets, keys, and certificates
- Secure access to sensitive information
- Integration with APIM and Functions for secure operations
