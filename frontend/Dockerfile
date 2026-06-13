FROM node:22-slim

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY frontend ./frontend

CMD ["npm", "run", "dev"]
