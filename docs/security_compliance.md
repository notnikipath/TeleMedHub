# Security and Compliance

## Regulatory mapping

- **152-ФЗ**:
  - role-limited access to personal data;
  - access audit logging;
  - storage of protected medical data in controlled services.
- **HIPAA principles**:
  - minimum necessary access;
  - traceability of data access events;
  - encryption for sensitive fields and tokenized authentication.

## Implemented controls

1. RBAC (`patient`, `doctor`, `admin`, `insurance_representative`).
2. Signed access tokens (`sign_token` / `verify_token` in shared security module).
3. Access check for EMR reads:
   - patient -> own records only,
   - doctor -> assigned patients only.
4. Encryption of diagnosis/recommendations in EMR storage.
5. Access audit trail (`/access-log`, `/audit`).
6. Session recording only with explicit consent flag.

## Data protection notes

- In production, replace demo HMAC token with full JWT + rotation keys.
- Move secrets to secret manager (Vault/KMS).
- Enable TLS everywhere (gateway, services, message queues).
- Apply at-rest encryption for PostgreSQL/MongoDB/object storage volumes.
