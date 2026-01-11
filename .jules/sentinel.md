## 2024-05-23 - Hardened CSP and Fixed Recharts Types
**Vulnerability:** The default Vite `index.html` often includes `unsafe-inline` for scripts, which weakens XSS protection.
**Learning:** Recharts type definitions are strict and require explicit handling of `undefined` in formatter functions, which can block builds if not handled. This is not strictly a security issue but blocks security deployments.
**Prevention:** Always check build logs before attempting security verifications. Remove `unsafe-inline` from CSP for production builds where scripts are bundled.
