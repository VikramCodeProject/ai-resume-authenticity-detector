# Enterprise API Addendum

## Auth and Security
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `GET /api/auth/me`
- `GET /api/csrf-token`

## Verification
- `POST /api/verify/resume`
- `POST /api/verify/github`
- `POST /api/verify/certificate`
- `POST /api/verify/full`
- `POST /api/verify/blockchain-hash`
- `GET /api/task-status/{task_id}`

## Response Contract
Success:
```json
{
  "success": true,
  "data": {}
}
```

Error:
```json
{
  "error": true,
  "message": "",
  "code": 400
}
```

## Security Header Expectations
All API responses include:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security`
- `Content-Security-Policy`
- `Referrer-Policy`
- `Permissions-Policy`
