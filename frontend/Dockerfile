# ---- Frontend Dockerfile (static site served by nginx) ----
FROM nginx:1.27-alpine

# Static site files
COPY index.html /usr/share/nginx/html/index.html
COPY style.css  /usr/share/nginx/html/style.css
COPY script.js  /usr/share/nginx/html/script.js

# Reverse proxy config -> talks to "backend" service (Compose or k8s Service name)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
