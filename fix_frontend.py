import paramiko, io, sys, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HOST = '64.188.63.166'
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username='root', password='bTnqVPmR8_*N+1', timeout=10)

def run(cmd, timeout=60):
    _, out, err = client.exec_command(cmd, timeout=timeout)
    o = out.read().decode('utf-8', errors='replace').strip()
    e = err.read().decode('utf-8', errors='replace').strip()
    rc = out.channel.recv_exit_status()
    if o: print(o[-600:])
    if e and rc != 0: print('[ERR]', e[-300:])
    return rc

def write_remote(path, content):
    sftp = client.open_sftp()
    with sftp.open(path, 'w') as f:
        f.write(content)
    sftp.close()

# Check current env files
print('==> Current frontend env files:')
run('ls /opt/ClipsGold/frontend/.env* 2>/dev/null || echo "none found"')
run('cat /opt/ClipsGold/frontend/.env.local 2>/dev/null || echo "no .env.local"')
run('cat /opt/ClipsGold/frontend/.env 2>/dev/null || echo "no .env"')

# Write correct .env.local
print('\n==> Writing .env.local...')
write_remote('/opt/ClipsGold/frontend/.env.local', '''NEXT_PUBLIC_API_URL=http://64.188.63.166:8000
NEXT_PUBLIC_WS_URL=ws://64.188.63.166:8000
''')
run('cat /opt/ClipsGold/frontend/.env.local')

# Rebuild
print('\n==> npm run build (2-3 min)...')
rc = run('cd /opt/ClipsGold/frontend && npm run build 2>&1 | tail -15', timeout=300)
print(f'build exit: {rc}')

# Restart frontend
print('\n==> Restarting frontend...')
run('systemctl restart clipsgold-frontend', timeout=10)
time.sleep(5)
run('systemctl is-active clipsgold-frontend')
run('journalctl -u clipsgold-frontend -n 4 --no-pager 2>&1')

client.close()
