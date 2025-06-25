FROM node:lts-alpine
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install

COPY src ./src

EXPOSE 5000
CMD ["node", "src/index.js"]