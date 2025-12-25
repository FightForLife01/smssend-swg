# Implementări – Checklist (Staging / Prod)

Legendă: `[x]` done, `[ ]` todo  
Staging: `staging.smssend.ro` (VPS: 72.62.61.84)  
Prod: `smssend.ro` + `www.smssend.ro` (VPS: 145.223.81.39)

Deploy:
- Staging: auto-deploy la push pe `main` (GitHub Actions runner) + manual `/usr/local/bin/deploy_staging.sh`
- Prod: manual `/usr/local/bin/deploy_prod.sh` (backup + versionare) — fără auto-deploy pe `main`

---

## Checklist (fără omisiuni)

| Staging | Prod | ID | Modul | Livrabil (ce trebuie să existe) | Unde modifici / creezi (paths) | Note critice (staging/prod) |
|---|---|---|---|---|---|---|
| [x] | [x] | INF-01 | VPS | 2 VPS create (staging + prod) | (infra) | Hostinger: staging separat de prod |
| [ ] | [ ] | INF-02 | VPS | SSH hardening (keys only, no password) | `/etc/ssh/sshd_config` | Urmează: disable root + disable password |
| [x] | [x] | INF-03 | VPS | Firewall (UFW) + fail2ban | UFW + `/etc/fail2ban/jail.local` | Allow 22 (IP allowlist), 80/443 public |
| [x] | [x] | INF-04 | Deploy | Nginx reverse proxy + TLS Let’s Encrypt | `/etc/nginx/sites-available/*` + certbot | Domenii separate: staging vs prod |
| [x] | [x] | INF-05 | Deploy | Systemd service backend + Nginx proxy /api + /static | `/etc/systemd/system/smssend-backend.service` + nginx vhost | Backend doar pe 127.0.0.1 |
| [x] | [ ] | INF-06 | Deploy | CI/CD staging (auto) + strategie deploy fără API public | `.github/workflows/deploy-staging.yml` + runner | Prod: NU auto pe main (controlat) |
| [ ] | [ ] | INF-07 | Config | `.env` separat staging/prod (secrets) | `/opt/smssend/.env` pe fiecare VPS | staging=TEST Stripe, prod=LIVE Stripe (de verificat/curățat) |

| [ ] | [ ] | DB-01 | DB | Postgres instalat pe ambele VPS | (infra) | User+DB separate |
| [ ] | [ ] | DB-02 | DB | Migrații Alembic (nu create_all în prod) | `alembic/`, `alembic.ini` | `DB_AUTO_CREATE=false` prod |
| [ ] | [ ] | DB-03 | DB | Schema upgrade: users extins + billing + quota tables | `app/models.py` + migrații | Migrații backward-safe |

| [ ] | [ ] | BAK-01 | Backup | Backup DB production zilnic (Postgres) | `scripts/backup/pg_dump.sh` + cron | retenție + encrypt |
| [ ] | [x] | BAK-02A | Backup | Backup config + release log la fiecare deploy prod | `/usr/local/bin/deploy_prod.sh` + `/opt/backups/smssend/` | Implementat (backup înainte de deploy) |
| [ ] | [ ] | BAK-02 | Backup | Backup configurări critice (fără expunere) | `scripts/backup/config.sh` | urmează (dacă vrei în repo) |
| [ ] | [ ] | BAK-03 | DR | Procedură restore testată pe staging | `docs/RUNBOOK_RESTORE.md` | test lunar |

| [x] | [x] | API-01 | Backend | Endpoint `/health` stabil | `app/main.py` | OK pe ambele: JSON |
| [x] | [x] | SEC-01 | Backend | Error handling prod (fără leak) | `app/main.py` | debug only în staging |
| [ ] | [ ] | SEC-02 | Headers | Security headers middleware complet | `app/middleware/security_headers.py` | HSTS doar pe HTTPS |
| [ ] | [ ] | SEC-03 | CORS | CORS strict (domenii only) | `app/main.py` middleware | staging/prod diferit |
| [ ] | [ ] | SEC-04 | RateLimit | Rate-limit DB-backed (login/register/forgot/reset) | `app/services/rate_limit.py` + `app/models.py` | funcționează multi-worker |
| [ ] | [ ] | SEC-05 | Lockout | Lockout per user (fields + logic) | `app/models.py`, `app/routes/auth.py` | reset la login success |
| [ ] | [ ] | SEC-06 | Tokens | Access token scurt + refresh token cookie | `app/security.py`, `app/routes/auth.py` | HttpOnly Secure SameSite |
| [ ] | [ ] | SEC-07 | CSRF | CSRF protecție refresh/logout | `app/middleware/csrf.py` sau service | necesar cu cookies |
| [ ] | [ ] | SEC-08 | Audit | Audit extins: fiecare acțiune importantă logată | `app/services/audit.py` + routes | include user_id peste tot |
| [ ] | [ ] | SEC-09 | GDPR | Minim PII în logs + export/ștergere | `app/routes/admin.py` + servicii | faza 2 |

| [x] | [x] | AUTH-00 | Auth | Login/Register basic funcțional | `app/routes/auth.py`, `app/schemas.py` | existent |
| [ ] | [ ] | AUTH-01 | Register | User model extins (nume, firmă, CUI, adresă…) | `app/models.py` + migrație | DB constraints |
| [ ] | [ ] | AUTH-02 | Register | Validări: firmă=>CUI obligatoriu | `app/schemas.py` | server-side |
| [ ] | [ ] | AUTH-03 | Register | Email normalize + unicitate DB | `users.email_normalized` + index | evită dubluri |
| [ ] | [ ] | AUTH-04 | Register | Confirm password + policy version | `app/schemas.py`, `app/routes/auth.py` | audit REGISTER |
| [ ] | [ ] | AUTH-05 | VerifyEmail | Token hashed + TTL | `app/models.py`, `app/routes/auth_verify.py` | blocare până verificat |
| [ ] | [ ] | AUTH-06 | ResetPassword | Forgot/reset cu cod + TTL + rate-limit | `app/routes/password_reset.py` + services | one-time use |
| [ ] | [ ] | AUTH-07 | Login | Rate-limit login + lockout + audit | `app/routes/auth.py` | brute-force |
| [ ] | [ ] | AUTH-08 | Sessions | Logout + refresh rotation + revoke | `app/routes/auth_sessions.py` | baseline |

| [x] | [x] | ORD-00 | Orders | Import excel + listare comenzi | `app/services/orders_import.py`, `app/routes/orders.py` | existent |
| [ ] | [ ] | ORD-01 | Orders | Import fără “delete all” (opțional) | `app/services/orders_import.py` | reduce risc |
| [ ] | [ ] | ORD-02 | Orders | Normalizare phone / pnk la import | `orders_import.py` | consistent |

| [x] | [x] | PL-00 | ProductLinks | CRUD PNK→URL (validări) | `app/routes/product_links.py` | existent |
| [ ] | [ ] | PL-01 | ProductLinks | Audit upsert/delete | `app/routes/product_links.py` | log acțiuni |

| [x] | [x] | SMS-00 | SMS | Trimitere SMS + anti-duplicat phone+PNK | `app/routes/sms.py` | existent |
| [ ] | [ ] | SMS-01 | Quota | Hard limit “SMS succes/lună” | `app/services/billing/quota_reserve.py` + `app/routes/sms.py` | fără race |
| [ ] | [ ] | SMS-02 | Quota | Tabel rezervări + expirare | model + migrație | concurență safe |
| [ ] | [ ] | SMS-03 | Audit | Audit CLICK/ATTEMPT separat | `app/routes/sms.py` | KPI real |

| [ ] | [ ] | CALL-01 | UI | Buton “Sună” (`tel:`) | `static/app.js` | gest explicit |

| [x] | [x] | UI-01 | UI | Tema alb/negru mat | `static/styles.css` | ok |
| [ ] | [ ] | UI-02 | UI | Meniu navigare | `static/index.html` | mobile-first |
| [ ] | [ ] | UI-03 | UI | Ecran Abonament (plan/status/usage) | `static/index.html`, `static/app.js` | X/Y |
| [ ] | [ ] | UI-04 | UI | Upgrade flow (checkout + portal) | `static/app.js` | folosește billing API |
| [ ] | [ ] | UI-05 | UI | Tratare 402 quota + CTA upgrade | `static/app.js` | mesaj clar |

| [x] | [ ] | BILL-01 | Stripe | Price objects TEST (99/249/499) | Stripe Dashboard | Live separat |
| [x] | [ ] | BILL-02 | Stripe | Customer Portal TEST configurat | Stripe Dashboard | Live separat |
| [ ] | [ ] | BILL-03 | Billing API | `/api/billing/me` status+usage | `app/routes/billing.py` | UI îl consumă |
| [ ] | [ ] | BILL-04 | Billing API | `/api/billing/checkout` create session | `app/services/billing/create_checkout.py` | metadata user_id |
| [ ] | [ ] | BILL-05 | Billing API | `/api/billing/portal` create portal | `app/services/billing/create_portal.py` | return url |
| [ ] | [ ] | BILL-06 | Stripe Webhook | `/api/billing/webhook` + signature verify | `app/services/billing/webhooks/*` | dedup obligatoriu |
| [ ] | [ ] | BILL-07 | Subscriptions | Persist subscription state | model + handler | truth=webhook |
| [ ] | [ ] | BILL-08 | Dedup | `stripe_webhook_events` | model + migrație | idempotency |

| [ ] | [ ] | INV-01 | Oblio | Factură la `invoice.paid` | `app/services/invoicing/oblio.py` | după webhook |

| [ ] | [ ] | ADM-01 | Admin | Rol admin | `users.is_admin`/roles | securizat |
| [ ] | [ ] | ADM-02 | Admin | Admin routes | `app/routes/admin.py` | audit admin |
| [ ] | [ ] | ADM-03 | Admin UI | Dashboard admin | `static/admin/*` | restrict |

| [ ] | [ ] | OBS-01 | Observability | Log structurat + correlation id | middleware/logging | prod debug |
| [ ] | [ ] | OBS-02 | Observability | Sentry | `app/main.py` + env | staging/prod |
| [ ] | [ ] | OBS-03 | Observability | Uptime monitor | extern | monitor /health |

| [ ] | [ ] | TST-01 | Testing | Flow staging end-to-end | `tests/*` | obligatoriu |
| [ ] | [ ] | TST-02 | Testing | Test quota + upgrade | staging | confirm hard limit |

| [ ] | [ ] | REL-01 | Release | Runbook deploy + rollback | `docs/RUNBOOK_DEPLOY.md` | “DB intact” |
| [ ] | [ ] | REL-02 | Release | Script deploy prod în repo | `scripts/deploy/deploy_prod.sh` | încă nu e în repo |
| [x] | [x] | REL-02A | Release | Script deploy PROD cu backup+versionare (server) | `/usr/local/bin/deploy_prod.sh` + `/opt/backups/smssend/` | implementat |
