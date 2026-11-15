# FitStats client

The user interface of FitStats: a React single-page app that is also packaged as a desktop app with Tauri. It reads the data produced by the Python backend in `../server`. See the [main README](../README.md) for what the project does, how to install it and how to run the full stack.

## Stack

- React 19 and TypeScript, built with Vite
- Redux Toolkit for state, Recharts for charts, TanStack Table for the data grid
- Tailwind CSS with Radix UI primitives
- Tauri v2 for the desktop shell (`src-tauri`)

## Scripts

Run them from this folder with `pnpm`:

| Script | What it does |
| --- | --- |
| `pnpm run dev` | Starts the Vite dev server |
| `pnpm run build` | Type-checks (`tsc -b`) and builds the production bundle into `dist/` |
| `pnpm run lint` | Runs ESLint on the whole client |

## Folder layout

```text
client/
├── public/        Static files (favicon)
├── src/
│   ├── components/  dashboard views and charts, onboarding, theme, shared UI
│   ├── features/    Redux slice with the dashboard state
│   ├── hooks/       React hooks
│   ├── lib/         API client, analytics and statistics helpers
│   ├── store/       Redux store and theme slice
│   └── types/       TypeScript types
├── src-tauri/     Rust code, configuration and icons of the desktop app
├── Dockerfile     Image that serves the built client with Nginx
└── nginx.conf     Nginx configuration used by that image
```
