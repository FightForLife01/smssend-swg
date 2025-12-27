# Project Rules (source of truth)

## Workflow
- Dezvoltare doar din VSCode -> GitHub.
- Push pe `main` => auto-deploy pe STAGING.
- PROD se face doar manual: GitHub Actions -> Deploy Production (workflow_dispatch).
- DB-ul de staging NU se copiază în prod.

## Server editing policy
- NU edităm codul aplicației direct pe server (/opt/smssend) decât prin deploy.
- Pe server edităm doar: Nginx, systemd, scripturi deploy, .env.

## Mandatory permissions (static must work)
- /opt/smssend trebuie să fie 751 (nginx trebuie să traverseze folderul).
- /opt/smssend/static trebuie să fie 755
- fișierele din static: 644

## ENV rules
- /opt/smssend/.env trebuie să fie valid pentru `bash source`:
  - fără text după valori
  - comentarii doar cu # pe linie separată
- PROD: DEBUG=false, SMTP obligatoriu.
- Stripe: STAGING = TEST, PROD = LIVE.
