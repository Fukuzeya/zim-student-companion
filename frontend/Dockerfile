# Stage 1: Build the Angular app
FROM node:18-alpine AS build
WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source and build
COPY . .
RUN npm run build --configuration=production

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Note the path: dist/frontend/browser 
# The application builder adds 'browser' to your defined outputPath
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html

# Copy the local nginx config we created above
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]