# Shared Database Config

- `init/`: SQL scripts executed automatically at PostgreSQL container initialization.
- `seed/`: reserved for deterministic seed data scripts used by backend bootstrap or CI.
- This folder is shared by backend and operational tooling in Docker offline deployment.
