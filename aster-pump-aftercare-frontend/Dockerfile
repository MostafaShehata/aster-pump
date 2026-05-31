FROM nginx:1.27-alpine

# Nginx serves the already-built React files and proxies /api to FastAPI.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# The React app is built outside Docker by build-app.ps1/build-app.sh.
COPY dist /usr/share/nginx/html

EXPOSE 80
