# npm / Docker build issues on restricted networks

## `UNABLE_TO_VERIFY_LEAF_SIGNATURE`

Corporate SSL inspection. See previous notes — use `docker-compose.fast.yml` + local `npm run dev`.

## `403 Forbidden` from registry.npmjs.org

Your network **blocks npm inside Docker** entirely. SSL workarounds will not help.

### Solution (default now)

The main `Dockerfile` **does not run npm**. It copies pre-built files from `frontend/dist/`.

```powershell
cd "c:\Users\Anirudh Babbar\Desktop\project"
docker compose build --no-cache
docker compose up
```

Open http://localhost:8000

### Rebuild the UI after changing React source

On a machine with working npm (home network, mobile hotspot):

```powershell
cd frontend
npm install
npm run build
```

That overwrites `frontend/dist/` from Vite. Commit the updated `dist/` if needed.

### Develop with hot reload (no Docker for UI)

```powershell
docker compose -f docker-compose.fast.yml up --build
cd frontend
npm run dev
```

http://localhost:5173 → API on :8000
