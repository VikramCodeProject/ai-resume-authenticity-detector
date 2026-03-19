# Enterprise Architecture Addendum

```mermaid
flowchart LR
  A[React Frontend] --> B[FastAPI Gateway]
  B --> C[Auth and RBAC]
  B --> D[Verification Orchestrator]
  D --> E[GitHub Verification Service]
  D --> F[OCR Certificate Service]
  D --> G[ML Scoring Engine]
  D --> H[Blockchain Service]
  H --> I[(Polygon / Ethereum)]
  B --> J[(PostgreSQL)]
  B --> K[(Redis)]
  B --> L[Structured Logging]
  L --> M[(SIEM / Log Store)]
```

## Security Layers
- JWT access and refresh token model.
- Role-aware authorization for Admin, Recruiter, Candidate, Analyst, Auditor.
- CSRF checks for cookie-bound session flows.
- Security headers middleware and strict CORS host policy.
- AES-backed encryption manager for sensitive at-rest payloads.

## Reliability Layers
- Direct verification fallback path when Celery is unavailable.
- API-wide standardized error contract.
- Rate limiting across verification endpoints.
- Locust profile for realistic load simulation.

## Blockchain Data Contract
- Resume/claim data reduced to deterministic SHA256 hashes.
- Hash persisted as on-chain transaction data.
- Verification endpoint compares expected hash with on-chain transaction input.
