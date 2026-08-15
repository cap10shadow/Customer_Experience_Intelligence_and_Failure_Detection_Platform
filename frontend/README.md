# Frontend

React 19 + TypeScript + Vite. The client for the Customer Experience Intelligence & Failure Detection Platform's Gateway API. See the [repository root README](../README.md) for the platform overview, architecture, and full quick-start instructions.

## Structure

```text
src/
├── auth/         # Login page, session context (AuthContext), route guard (RequireAuth)
├── workspaces/   # dashboard, investigations, recommendations, analytics, administration
├── copilot/      # Copilot panel, API client, context
├── shared/       # Cross-workspace components, the Gateway API client
└── tests/        # Vitest test suite (337 tests across 48 files)
```

## Development

```bash
npm install
npm run dev
```

Serves on `http://localhost:3000` and proxies `/api` to `gateway_service` same-origin (`vite.config.ts`) — no CORS configuration needed in development. Requires the backend stack running (`docker compose up postgres gateway_service ...` from the repository root, or the full stack).

## Commands

| Command | Purpose |
|---|---|
| `npm run dev` | Start the Vite dev server with hot reload |
| `npm run build` | Type-check (`tsc -b`) then produce a production build |
| `npm run lint` | ESLint |
| `npm test` | Run the Vitest suite once |
| `npm run test:watch` | Vitest in watch mode |
| `npm run typecheck` | `tsc -b --noEmit` only |

## Production build

The production-like Docker configuration (`docker-compose.prod.yml`, repository root) builds this app via a multi-stage Dockerfile and serves the static output through nginx — no Vite dev server, no source bind mount. See the root README's [Docker: Development vs. Production-Like](../README.md#13-docker-development-vs-production-like) section.
