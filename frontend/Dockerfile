FROM node:22-alpine

WORKDIR /app

COPY frontend/package.json /app/package.json
RUN npm install

COPY frontend /app

ENV VITE_API_GATEWAY_URL=http://api-gateway:8100

CMD ["npm", "run", "dev"]
