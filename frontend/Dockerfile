# Stage 1: Build the Angular app
# Changed from node:18 to node:22
FROM node:22-alpine AS build
WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source and build
COPY . .
RUN npm run build --configuration=production

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Use the path verified from your angular.json
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html

# Copy the internal nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]