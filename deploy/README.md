# Running AlgoLens on a server

Tested on an Azure VM (Ubuntu 24.04, 2 vCPU, 4 GB), but any Linux server with Docker works.
The server needs ports 22 (SSH), 80 and 443 open to the internet.

1. Once, on a fresh server: `sudo sh deploy/setup-server.sh`. It installs Docker, allows the
   unprivileged user namespaces the sandbox's nsjail needs, adds swap and turns on automatic
   security updates. Log out and back in afterwards (for the docker group).
2. `git clone https://github.com/Abhinavbilla/AlgoLens.git && cd AlgoLens`
3. Put a `.env` in the folder (copy it over SSH; never commit it). On top of the usual keys:

   ```
   SITE_ADDRESS=20-2-211-154.sslip.io          # your domain, or <ip-with-dashes>.sslip.io
   ALGOLENS_PUBLIC_URL=https://20-2-211-154.sslip.io
   ALGOLENS_EMAIL_DEV_LOG=false
   ```

4. `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`

Caddy (`deploy/Caddyfile`) gets an HTTPS certificate for `SITE_ADDRESS` by itself. The
database, API and web container stay bound to 127.0.0.1; only Caddy is public.

For Google sign-in, add `https://<SITE_ADDRESS>` as an authorized JavaScript origin and
`https://<SITE_ADDRESS>/api/auth/google/callback` as a redirect URI in Google Cloud Console.

Updating later: `git pull`, then the same `docker compose ... up -d --build`.
