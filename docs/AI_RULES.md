docs/AI_RULES.md

reguli de lucru (nu edităm cod pe server; doar prin git; server = doar infra + .env)

flow deploy staging/prod

permisiuni obligatorii (/opt/smssend = 751, /opt/smssend/static = 755)

“.env trebuie să fie valid pentru systemd și bash (fără text după valori)”

docs/ENV_TEMPLATE.md

listă completă de variabile pe STAGING vs PROD (fără valori reale)

infra/ folder în repo (doar template-uri, fără secrete)

infra/nginx/smssend.ro

infra/systemd/smssend-backend.service

infra/deploy/deploy_prod.sh (template, nu cel live)