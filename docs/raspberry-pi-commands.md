# Raspberry Pi: useful commands

Hosting the app on a Raspberry Pi (64-bit OS) with Docker, reached privately through Tailscale.

- Tailscale address: `https://thumbness.tail5cc92f.ts.net`
- Spotify callback: `https://thumbness.tail5cc92f.ts.net/callback`

## 1. One-time Pi setup

### Update and check the architecture
```bash
sudo apt update && sudo apt full-upgrade -y
uname -m                      # should print aarch64
sudo apt install -y git curl ca-certificates
```

### Install Docker Engine and the compose plugin
```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```
Log out and back in over SSH, then check:
```bash
docker --version
docker compose version
docker run --rm hello-world
```

### Install Tailscale
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up             # open the printed URL to sign in
```
In the Tailscale admin console, enable MagicDNS and HTTPS certificates.

### Get the code
```bash
git clone <your-repo-url>
cd local-100
git checkout feature/containerise
```
Python and ffmpeg are not needed on the Pi; the Docker image bundles both.

## 2. First-time app setup

### Create `.env`
Fill in the two Spotify values. `SECRET_KEY` is generated for you.
```bash
cat > .env <<EOF
CLIENT_ID=your-spotify-client-id
CLIENT_SECRET=your-spotify-client-secret
SECRET_KEY=$(openssl rand -hex 32)
REDIRECT_URI=https://thumbness.tail5cc92f.ts.net/callback
SESSION_COOKIE_SECURE=1
TRUSTED_PROXY_HOPS=1
EOF
chmod 600 .env
```
Register the same callback URL as a Redirect URI in the Spotify developer dashboard. It must match exactly.

If the library search flow needs its own callback, add this line to `.env` and register it too:
```
LIBRARY_REDIRECT_URI=https://thumbness.tail5cc92f.ts.net/library/callback
```

### Prepare the data folder
The container runs as uid 1000, so that user must be able to write to it.
```bash
mkdir -p data
sudo chown -R 1000:1000 data
```
Videos are large. Put `data` on a USB SSD if you can, because they wear out an SD card.

### Create the admin user
Asks for a password of at least 10 characters.
```bash
docker compose run --rm app python -m src.cli.users add YOUR-NAME --admin
```

### Start the app and expose it on the tailnet
```bash
docker compose up -d --build
docker compose ps                         # should show "healthy"
curl http://127.0.0.1:8888/healthz        # should print "ok"
sudo tailscale serve --bg 8888
tailscale serve status
```
Then open `https://thumbness.tail5cc92f.ts.net` from any device signed into your tailnet.

## 3. Day-to-day

```bash
docker compose logs -f app                       # watch the logs
docker compose ps                                # container status and health
docker compose restart app                       # restart
docker compose down                              # stop
docker compose up -d                             # start again, or apply .env changes
git pull && docker compose up -d --build         # update to the latest code
docker stats --no-stream                         # CPU and memory use
```

### Manage users
```bash
docker compose run --rm app python -m src.cli.users list
docker compose run --rm app python -m src.cli.users add a-friend            # member
docker compose run --rm app python -m src.cli.users add another --admin     # admin
docker compose run --rm app python -m src.cli.users remove a-friend
```
Changes apply immediately, with no restart. Users are stored in `data/auth/users.json`.

## 4. Tailscale

```bash
tailscale status                                 # devices on your tailnet
tailscale status --json | grep -m1 '"DNSName"'   # the Pi's full .ts.net name
tailscale serve status                           # what is being served
sudo tailscale serve reset                       # stop serving
```
The Pi must be powered on and online. After a reboot, run `tailscale serve status` once to confirm the serve setting persisted.

### Tailscale Funnel (public internet): not enabled
Funnel lets anyone on the internet open the site, with only the app's login protecting it.
```bash
sudo tailscale funnel --bg 8888                  # turn on (public)
sudo tailscale funnel reset                      # turn off
```
Before using it, check that the real visitor address reaches the app, so the 5-attempt lockout works, and consider a general rate limit. Staying on `tailscale serve` keeps it private.

## 5. Troubleshooting

### The build looks stuck
The `pip install` step downloads a 60 MB package (`nodejs_wheel_binaries`, needed by `pytubefix`), which is slow on weak Wi-Fi or an SD card. Check from a second SSH session:
```bash
docker stats --no-stream
top
ip -s link show wlan0        # run twice; the RX bytes should grow
```
If it has truly stalled, press `Ctrl+C` and rebuild. Cached steps are reused, and the plain log is easier to read:
```bash
docker compose build --progress=plain
```

### Spotify login says "redirect URI mismatch"
`REDIRECT_URI` in `.env` and the Redirect URI in the Spotify dashboard must match character for character. After editing `.env`, run `docker compose up -d` to recreate the container.

### Permission errors writing to `data`
```bash
sudo chown -R 1000:1000 data
```

### Container is not healthy
```bash
docker compose logs --tail=100 app
```

### `tailscale serve` says HTTPS is not enabled
Enable MagicDNS and HTTPS certificates in the Tailscale admin console under DNS, then run `sudo tailscale serve --bg 8888` again.

## 6. Notes

- `requirements.txt` includes `requests_oauthlib` and `waitress`, which the repo's code does not import. They are harmless; removing them is optional.
- The app listens only on `127.0.0.1:8888` on the Pi. Tailscale is the only way in.
- Sessions last 7 days. Keeping `SECRET_KEY` unchanged keeps people signed in across restarts.
