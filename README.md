# Rock Paper Scissors — Flask + SQL + AWS EC2

A beginner-friendly class project built with **Python, Flask, SQLite (SQL database), HTML/CSS, and AWS EC2**.

## Features
- Play Rock, Paper, Scissors against the computer.
- Saves every round to a SQL database.
- Shows total games, wins, losses, draws, and recent history.
- Clear saved game history.
- Health endpoint at `/health`.
- Responsive dark UI.

## Project structure

```text
rock_paper_scissors_flask_aws/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── templates/
│   └── index.html
└── static/
    └── style.css
```

The SQLite database (`game.db`) is created automatically the first time the app starts. It is intentionally excluded from the ZIP because it is generated at runtime.

## Run locally (Windows / macOS / Linux)

1. Install Python 3.10 or newer.
2. Extract the ZIP and open a terminal in the project folder.
3. Create and activate a virtual environment.

**Windows PowerShell**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

4. Install dependencies:
```bash
python -m pip install -r requirements.txt
```

5. Start the development server:
```bash
python app.py
```

6. Open `http://127.0.0.1:5000` in your browser. Play a few rounds and confirm the history is saved.

For a deployed environment, set a strong `SECRET_KEY`. Do not use Flask's development server or `debug=True` for production.

---

# Deploy on AWS EC2 (Ubuntu)

This guide uses one EC2 instance and SQLite to keep the class project simple. For a larger production app, use Amazon RDS for the SQL database.

## 1. Launch an EC2 instance
1. Open the AWS Management Console and go to **EC2 → Instances → Launch instances**.
2. Choose **Ubuntu Server 24.04 LTS** (or a currently supported Ubuntu LTS image).
3. Choose a small instance suitable for a demo, such as `t3.micro`, if available in your account/region.
4. Create or select a key pair and download the `.pem` file. Keep it private.
5. In the security group, add:
   - **SSH**, TCP port `22`, source **My IP** only.
   - **HTTP**, TCP port `80`, source `0.0.0.0/0`.
   Do not expose port 5000 publicly; Nginx will proxy requests to Gunicorn on localhost.
6. Launch the instance and note its public IPv4 address.

AWS pricing and free-tier eligibility depend on region, account, and current AWS terms. Stop or terminate resources when you are finished to avoid unexpected charges.

## 2. Connect to the instance

On macOS/Linux:
```bash
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

On Windows, use PowerShell with OpenSSH (adjust the path):
```powershell
ssh -i "C:\path\to\your-key.pem" ubuntu@YOUR_EC2_PUBLIC_IP
```

Replace `YOUR_EC2_PUBLIC_IP` with the address shown in EC2. If SSH fails, check the instance's security-group rule and key-pair path.

## 3. Install system packages

Run on the EC2 instance:
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx unzip
```

## 4. Copy the project to EC2

**Option A — SCP from your own computer** (run this on your computer, not inside SSH):
```bash
scp -i your-key.pem rock_paper_scissors_flask_aws.zip ubuntu@YOUR_EC2_PUBLIC_IP:/home/ubuntu/
```

Then on EC2:
```bash
cd /home/ubuntu
unzip rock_paper_scissors_flask_aws.zip
cd rock_paper_scissors_flask_aws
```

**Option B — Upload to a private Git repository** and clone it on EC2:
```bash
git clone YOUR_PRIVATE_REPOSITORY_URL
cd YOUR_REPOSITORY_FOLDER
```
Do not put private keys, passwords, or `.env` secrets in a public repository.

## 5. Install Python dependencies and set a secret

```bash
cd /home/ubuntu/rock_paper_scissors_flask_aws
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Create a strong secret:
```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

Copy the output, then create an environment file:
```bash
sudo nano /etc/rock-paper-scissors.env
```

Add these lines, replacing the example value:
```text
SECRET_KEY=PASTE_YOUR_RANDOM_SECRET_HERE
DATABASE_PATH=/var/lib/rock-paper-scissors/game.db
```

Save in nano with `Ctrl+O`, Enter, then `Ctrl+X`. Protect the file:
```bash
sudo chmod 600 /etc/rock-paper-scissors.env
sudo mkdir -p /var/lib/rock-paper-scissors
sudo chown ubuntu:ubuntu /var/lib/rock-paper-scissors
```

## 6. Test Gunicorn

From the project directory with the virtual environment activated:
```bash
set -a
source /etc/rock-paper-scissors.env
set +a
gunicorn --workers 2 --bind 127.0.0.1:8000 app:app
```

In a second SSH session, test:
```bash
curl http://127.0.0.1:8000/health
```
Expected response:
```json
{"status":"ok"}
```
Stop the test server with `Ctrl+C`.

## 7. Run the app as a systemd service

Create a service file:
```bash
sudo nano /etc/systemd/system/rock-paper-scissors.service
```

Paste:
```ini
[Unit]
Description=Rock Paper Scissors Flask Game
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/rock_paper_scissors_flask_aws
EnvironmentFile=/etc/rock-paper-scissors.env
ExecStart=/home/ubuntu/rock_paper_scissors_flask_aws/.venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8000 app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Save and enable the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now rock-paper-scissors
sudo systemctl status rock-paper-scissors
```

If it fails, inspect logs:
```bash
sudo journalctl -u rock-paper-scissors -n 80 --no-pager
```

## 8. Configure Nginx

Create a site config:
```bash
sudo nano /etc/nginx/sites-available/rock-paper-scissors
```

Paste:
```nginx
server {
    listen 80;
    server_name _;

    location /static/ {
        alias /home/ubuntu/rock_paper_scissors_flask_aws/static/;
        expires 7d;
        add_header Cache-Control "public";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable it and reload Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/rock-paper-scissors /etc/nginx/sites-enabled/rock-paper-scissors
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

If the symlink already exists, do not create it again; proceed to `sudo nginx -t`.

## 9. Open your game
Visit:
```text
http://YOUR_EC2_PUBLIC_IP
```
You should see the game. Play several rounds and verify the history and statistics update.

## 10. Troubleshooting
- **502 Bad Gateway:** run `sudo systemctl status rock-paper-scissors` and `sudo journalctl -u rock-paper-scissors -n 80 --no-pager`.
- **Nginx config error:** run `sudo nginx -t`.
- **Page not reachable:** check EC2 is running and security group allows inbound HTTP on port 80.
- **SSH timeout:** check inbound TCP 22 is restricted to your current public IP and the instance has a reachable public IP.
- **Database write error:** check the directory is writable: `sudo chown -R ubuntu:ubuntu /var/lib/rock-paper-scissors`.
- **After changing code:** run `sudo systemctl restart rock-paper-scissors`.
- **Public IP changed after stop/start:** use the current public IPv4 address in the browser, or configure an Elastic IP if appropriate.

## SQL schema

```sql
CREATE TABLE game_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_choice TEXT NOT NULL,
    computer_choice TEXT NOT NULL,
    result TEXT NOT NULL,
    played_at TEXT NOT NULL
);
```

## How to explain this in your viva
- **Python:** handles game logic and randomly selects the computer's move.
- **Flask:** maps URLs to Python functions and renders the HTML page.
- **SQL / SQLite:** stores every game round and calculates the score summary with SQL aggregate queries.
- **HTML/CSS:** provides the interactive game interface.
- **Gunicorn:** production WSGI server that runs the Flask application.
- **Nginx:** accepts public HTTP traffic and forwards it to Gunicorn.
- **AWS EC2:** hosts the application on a cloud virtual machine.
- **Parameterized SQL:** `?` placeholders help keep user-provided values separate from SQL commands.

## Important notes
- This is a learning/demo project, not a hardened production service.
- The game history is shared by everyone visiting this instance.
- SQLite is suitable for a small class demo; use Amazon RDS (such as PostgreSQL or MySQL) for a multi-user production deployment.
- Add HTTPS with a domain and a TLS certificate before collecting any sensitive information.
