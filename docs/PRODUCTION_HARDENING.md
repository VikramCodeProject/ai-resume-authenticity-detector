# Production Hardening Guide

## Scope
This guide summarizes enterprise hardening added across backend, AI verification, blockchain, security controls, and testing.

## Backend Security Enhancements
- Secrets removed from runtime defaults for JWT and AES encryption managers.
- Environment variables required:
  - `JWT_SECRET`
  - `ENCRYPTION_KEY`
  - `ETH_RPC_URL`
  - `PRIVATE_KEY`
  - `SMART_CONTRACT_ADDRESS` (optional if you write to account address)
- Added HTTP security middleware:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Strict-Transport-Security`
  - `Content-Security-Policy`
  - `Referrer-Policy`
  - `Permissions-Policy`
- Added CSRF protection for cookie-session requests (`/api/csrf-token` + `X-CSRF-Token` header).
- Added SQL-injection guard checks for untrusted verification inputs.

## Auth, Refresh Tokens, and RBAC
- Access + refresh JWT flows are supported.
- Added `/api/auth/refresh` endpoint for refresh-token rotation.
- Added `/api/auth/me` endpoint for role-aware identity checks.
- User roles supported: `admin`, `recruiter`, `candidate`, `auditor`, `analyst`.

## API Response Contract
- Standard success shape for new/updated endpoints:
```json
{
  "success": true,
  "data": {}
}
```
- Standard error shape via global handlers:
```json
{
  "error": true,
  "message": "",
  "code": 400
}
```

## Multi-Source Verification
- GitHub verification now falls back to direct service execution when Celery is unavailable.
- OCR certificate verification now falls back to direct OCR pipeline when Celery is unavailable.
- Full verification route now combines GitHub and OCR results, computes aggregate trust, and attempts blockchain write.

## Blockchain Hardening
- Added deterministic SHA256 hash generation for resume content and claim payloads.
- Real signed transaction writes are used when Web3 + private key are configured.
- Added on-chain hash verification endpoint: `POST /api/verify/blockchain-hash`.
- Transaction hash and block number are returned from blockchain writes.

## ML Validation and Model Comparison
- Existing ML pipeline already supports:
  - Accuracy
  - Precision
  - Recall
  - F1-score
  - Confusion matrix
  - Model comparison table and plots
- Run full ML pipeline:
```bash
python ml_pipeline/main.py
```

## Testing Upgrades
- Added auth/security/API contract tests:
  - `tests/test_auth_security_contract.py`
- Existing rate-limit tests remain in:
  - `tests/test_verify_rate_limit.py`
- Added load-test profile aligned with current routes:
  - `backend/load_test_enterprise.py`

## Frontend Feedback Improvements
- Frontend now parses standardized backend error payloads (`message` and `detail`).
- Verification progress now displays processing stage and percentage when available.

## Next Steps Before Production
1. Store refresh token revocation data in Redis instead of memory.
2. Replace in-memory mock user/resume storage with PostgreSQL tables and migrations.
3. Run blockchain with production contract ABI methods and auditable events.
4. Add CI pipeline for test + lint + security scanning.
5. Enable centralized logging (ELK/OpenSearch/Grafana Loki) with trace IDs.
