# PROJECT TREE (git-tracked)

Generat automat din `git ls-files` ca să reflecte exact ce se deploy-ează pe VPS.

```text
├── .github
│   └── workflows
│       ├── deploy-production.yml
│       └── deploy-staging.yml
├── app
│   ├── deps
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── db.py
│   ├── middleware
│   │   └── security_headers.py
│   ├── routes
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── auth_login.py
│   │   ├── auth_logout.py
│   │   ├── auth_me.py
│   │   ├── auth_refresh.py
│   │   ├── auth_register.py
│   │   ├── auth_verify_email.py
│   │   ├── billing.py
│   │   ├── orders.py
│   │   ├── password_reset.py
│   │   ├── product_links.py
│   │   ├── settings.py
│   │   └── sms.py
│   ├── services
│   │   ├── auth
│   │   │   ├── create_email_verification_token.py
│   │   │   ├── enforce_rate_limit.py
│   │   │   ├── login_user.py
│   │   │   ├── normalize_email.py
│   │   │   ├── register_user.py
│   │   │   ├── revoke_refresh_token.py
│   │   │   ├── rotate_refresh_token.py
│   │   │   ├── send_verification_email.py
│   │   │   ├── validate_password.py
│   │   │   └── verify_email.py
│   │   ├── billing
│   │   │   ├── __init__.py
│   │   │   ├── billing.py
│   │   │   ├── create_checkout.py
│   │   │   └── stripe_customer.py
│   │   ├── password_reset
│   │   │   ├── __init__.py
│   │   │   ├── confirm_password_reset.py
│   │   │   └── request_password_reset.py
│   │   ├── __init__.py
│   │   ├── audit.py
│   │   ├── email_sender.py
│   │   ├── orders_import.py
│   │   ├── rate_limit.py
│   │   └── sms_service.py
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── excel_loader.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   └── security.py
├── docs
│   └── CHECKLIST.md
├── static
│   ├── app.js
│   ├── index.html
│   └── styles.css
├── .gitignore
└── requirements.txt
```
