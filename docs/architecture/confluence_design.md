# simple-upgrade Orchestration Engine
## Architecture & Workflow Documentation

This document provides the structured architectural blueprints for both technical integrators and management stakeholders. The diagrams below are written in `mermaid.js` and can be pasted directly into Atlassian Confluence using the `/mermaid` macro.

---

## 1. High-Level Design (HLD)
**Target Audience**: Project Managers, Network Architects, Non-Technical Stakeholders.
**Purpose**: Illustrates the overarching business logic and fail-safes built into the automated pipeline.

### Executive Summary
The `simple-upgrade` engine is an idempotent, profile-driven automation pipeline designed to eliminate manual intervention during Cisco network hardware upgrades. It enforces a strict "Pre-Flight, Execution, Post-Flight" methodology to guarantee network stability and full auditability. 

### HLD Workflow Diagram
*To view this diagram in Confluence, type `/mermaid`, hit Enter, and paste the block below:*

```mermaid
graph TD
    %% Styling definitions
    classDef success fill:#d4edda,stroke:#28a745,stroke-width:2px;
    classDef danger fill:#f8d7da,stroke:#dc3545,stroke-width:2px;
    classDef process fill:#e2e3e5,stroke:#6c757d,stroke-width:2px;
    classDef primary fill:#cce5ff,stroke:#004085,stroke-width:2px;

    Start([Start Automated Upgrade]) --> A
    
    subgraph Phase 1: Pre-Flight
        A[Device Readiness Check]:::process
        B[Pre-Flight Diagnostic Snapshots]:::process
    end
    
    A --> |Evaluate| B
    B --> Eval{Are Checks Healthy?}
    
    subgraph Phase 2: Execution
        C[Distribute Firmware]:::primary
        D[Hardware Install & Activate]:::primary
        E[Wait for Device Reload & Stabilization]:::primary
    end

    Eval -- Yes --> C
    C --> D
    D --> E
    
    subgraph Phase 3: Post-Flight
        F[Post-Flight Diagnostic Snapshots]:::process
        G{Version Verified?}
    end

    E --> |Device Comes Online| F
    F --> G
    
    subgraph Phase 4: Reporting
        H[Generate Diffs & JSON Audit Logs]:::success
        Z[Abort Safely & Dump Logs]:::danger
    end

    Eval -- No --> Z
    G -- Yes --> H
    G -- No --> Z
```

---

## 2. Low-Level Design (LLD)
**Target Audience**: DevOps Engineers, Software Developers, Automation Specialists.
**Purpose**: Details the internal object states, programmatic dependencies, and API flow of the execution engine.

### Architectural Core Concepts
1. **`UpgradePackage` Orchestrator**: The master runtime controller that manages sequential stage invocation.
2. **Dynamic Profiling**: Discards hardcoded logic in favor of regex-matched JSON templates (`device_profiles/`) mapped to dynamic interfaces and stack matrices.
3. **`ExecutionContext` Backpack**: An immutable state manager (`ctx`) that securely transports target hardware metrics, SSH references, and success booleans seamlessly between isolated stages.
4. **`TaskRegistry` Router**: A decorator-driven system (`@register_stage`) that dynamically links manufacturer-agnostic commands to manufacturer-specific implementations (e.g. Cisco IOS-XE).

### LLD Sequence Execution Diagram
*To view this diagram in Confluence, type `/mermaid`, hit Enter, and paste the block below:*

```mermaid
sequenceDiagram
    autonumber
    
    box rgb(240, 248, 255) Pipeline Engine
        participant Client as Calling Script (CI/CD)
        participant UP as UpgradePackage
        participant Ctx as ExecutionContext
        participant Reg as TaskRegistry
    end
    
    box rgb(245, 245, 245) Network Layer
        participant Dev as Target Switch (IOS-XE)
    end

    %% Initialization
    Client->>UP: Initialize(host, golden_image, credentials)
    UP->>Ctx: Instantiate Context Backpack
    UP->>UP: Parse device_profiles/*.json
    
    %% Stage 1
    UP->>Reg: execute('sync', ctx)
    Reg->>Dev: SSH Connect (Scrapli/Netmiko)
    Dev-->>Reg: Return Hardware PID & Platform
    Reg->>Ctx: Cache regex-matched JSON profile
    
    %% Stage 2
    UP->>Reg: execute('readiness', ctx)
    Reg->>Dev: Assert Flash space, boot variables
    Dev-->>Reg: Return environmental status
    
    %% Stage 3
    UP->>Reg: execute('distribute', ctx)
    Reg->>Dev: Trigger copy operation via FTP/SCP
    Dev-->>Reg: Image copied and MD5 verified
    
    %% Stage 4
    UP->>Reg: execute('activate', ctx)
    Reg->>Dev: run 'install add/activate/commit'
    Dev--xReg: Connection Dropped (Reloading)
    
    %% Stage 5
    UP->>Reg: execute('post_activation_wait', ctx)
    loop TCP Polling Protocol
        Reg->>Dev: Socket Sweep Port 22
        Dev-->>Reg: Socket Open / SSH Ready
    end
    
    %% Stage 6
    UP->>Reg: execute('verification', ctx)
    Reg->>Dev: Query Version Information
    Reg->>Ctx: Assert actual version == target version
    
    %% Teardown
    UP-->>Client: Return aggregate execution_log.json
```

---

## 3. Supported Action Matrix
When explaining the scope to management, these are the natively supported execution capabilities verified in the architecture:

| Capability | Supported Specifications |
|---|---|
| **Target Manufacturers** | Cisco |
| **OS Platforms** | IOS-XE (`cisco_xe`) |
| **Tested Hardware Families** | Catalyst 9300 (`C9300-.*`), Catalyst 9300X (`C9300X-.*`), Catalyst 9300L (`C9300L-.*`), VIOS |
| **Image Transfer Protocols** | HTTP, HTTPS, TFTP, FTP, SCP |
| **Data Encoding & Validation** | Checksums (MD5, SHA-256), Pydantic Strict Typing |
| **Connection Backends** | Scrapli (`ssh2` accelerated), Genie/Unicon/pyATS (Interactive dialogs) |
