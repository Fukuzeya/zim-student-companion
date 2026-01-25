# Stage 1: Build Angular
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build --configuration=production

# Stage 2: Serve with Nginx
FROM nginx:alpine
# Check your angular.json for the exact output path (dist/project-name)
COPY --from=build /app/dist/frontend-app-name /usr/share/nginx/html
# Add a custom internal nginx config to handle Angular routing
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80