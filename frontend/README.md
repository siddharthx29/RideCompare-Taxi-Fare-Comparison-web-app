# Frontend

The frontend is a React, TypeScript, and Vite app with Leaflet maps and a platform analytics view.

## Development

```powershell
npm ci
npm run dev
```

The Vite server proxies `/api` and `/health` to `http://127.0.0.1:5000`. `VITE_API_URL` can be set for a separately hosted API; leave it empty to use same-origin routing.

## Production

```powershell
npm run build
npm run preview
```

The Docker image serves the static build with Nginx and proxies API requests to the Compose backend. Local `.env` files are excluded from the Docker build context.

## Quality Checks

```powershell
npm audit
npm run build
npm run lint
```