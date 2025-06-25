FROM node:lts-alpine
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install

COPY src ./src

CMD ["node", "src/index.js"]