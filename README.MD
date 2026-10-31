1. Paulblade gives raw json
2. Place Paulblade's raw json in the data/results directory
3. Update AppConfig RAW path to point to the new file
4. Auto setup and check:
```bash
./setup.sh
```
5. Otherwise run:
```bash
python -m venv venv
source venv/bin/activate #Mac/Linux 
source venv\Scripts\activate #Windows
pip install -r requirements.txt
python -m src.cli.setup
```
5. wait for setup to parse and store curated results.json and download videos to the data/videos directory
6. Any failures -> run `python -m src.cli.setup` again to retry failed downloads (skip already downloaded videos)
7. Run the app
```bash
./run.sh
```
- or
```bash
python -m src.web.app
```
8. Terminal will show the URL to open in your browser
```bash
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:8888
 * Running on http://100.106.234.129:8888
 ```
The port follows `REDIRECT_URI` in `.env` (8888 by default).

## Running in Docker

1. Put your settings in `.env`: `CLIENT_ID`, `CLIENT_SECRET`, `SECRET_KEY` and `REDIRECT_URI=http://127.0.0.1:8888/callback`.
2. Create an admin user (see "Signing in" below):
```bash
docker compose run --rm app python -m src.cli.users add YOUR-NAME --admin
```
3. Start the app:
```bash
docker compose up -d --build
```
4. Open http://127.0.0.1:8888

Videos, the countdown results and the users file live in `./data` on the host, so they survive rebuilds.
To update later: `git pull && docker compose up -d --build`.

The app is published on this machine only. To let other people in, put a reverse proxy or a tunnel with HTTPS
in front of it, then set `SESSION_COOKIE_SECURE=1` and `TRUSTED_PROXY_HOPS=1` (see below) and register the
`https://your-address/callback` URL as a Redirect URI in your Spotify app.

## Signing in

The whole app is behind a login. Create the first user before you start it:

```bash
python -m src.cli.users add YOUR-NAME --admin     # asks for a password (10+ characters)
python -m src.cli.users add a-friend              # a member: everything except the upload page
python -m src.cli.users list
python -m src.cli.users remove a-friend
```

In Docker: `docker compose run --rm app python -m src.cli.users add YOUR-NAME --admin`
(the container runs as user 1000, so `data/` on the host must be writable by that user).

- Users live in `data/auth/users.json` as salted password hashes. It is git-ignored; keep it that way.
- Changes apply immediately, with no restart. Removing a user or removing admin rights takes effect on their next click.
- Only admins can see or use the upload page. Everyone signed in can use the countdown and the Spotify search.
- After 5 wrong passwords from one address, that address is locked out for 15 minutes.
- Sessions last 7 days. Setting `SECRET_KEY` keeps people signed in across restarts.

Settings for running behind HTTPS and a reverse proxy (Caddy, a load balancer):

| Variable | Set it to | Why |
|---|---|---|
| `SESSION_COOKIE_SECURE` | `1` | Only send the login cookie over HTTPS |
| `TRUSTED_PROXY_HOPS` | `1` (number of proxies in front) | Count lockouts per real visitor, not per proxy. Leave unset when nothing is in front, or anyone could fake their address |

`/healthz` is public (it answers `ok`) for health checks. Everything else needs a sign-in.
