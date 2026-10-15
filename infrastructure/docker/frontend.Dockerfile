FROM node:22-alpine AS build
WORKDIR /app
COPY code/frontend/package*.json ./
RUN npm install
COPY code/frontend/ .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html

