FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .

ARG VITE_AZURE_CLIENT_ID
ARG VITE_AZURE_TENANT_ID
ARG VITE_AZURE_REDIRECT_URI
ARG VITE_API_URL

ENV VITE_AZURE_CLIENT_ID=$VITE_AZURE_CLIENT_ID
ENV VITE_AZURE_TENANT_ID=$VITE_AZURE_TENANT_ID
ENV VITE_AZURE_REDIRECT_URI=$VITE_AZURE_REDIRECT_URI
ENV VITE_API_URL=$VITE_API_URL

RUN npm run gen-sounds && npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html

ARG NGINX_CONF=nginx.https.conf
COPY ${NGINX_CONF} /etc/nginx/conf.d/default.conf

# Certificados SSL embutidos na imagem
COPY certs/nginx.crt /etc/nginx/certs/nginx.crt
COPY certs/nginx.key /etc/nginx/certs/nginx.key

EXPOSE 80
EXPOSE 443
