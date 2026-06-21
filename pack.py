"""Pack project into tar.gz, excluding dev files."""
import tarfile
import os

EXCLUDE_DIRS = {'.git', '__pycache__', 'promo', 'screenshots', 'docs'}
EXCLUDE_FILES = {'iching.db', '.github_token'}

with tarfile.open('D:/Project/python/iching-server.tar.gz', 'w:gz') as tar:
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS
                   and not d.startswith('.git')]
        for f in files:
            if f.endswith('.pyc') or f in EXCLUDE_FILES:
                continue
            full = os.path.join(root, f)
            arc = full.replace('\\', '/')
            if arc.startswith('./'):
                arc = arc[2:]
            tar.add(full, arcname=arc)

# verify
with tarfile.open('D:/Project/python/iching-server.tar.gz', 'r:gz') as tar:
    names = tar.getnames()
    c = tar.extractfile('deploy/setup.sh').read().decode()
    print(f'setup.sh alinux: {"YES" if "alinux" in c else "MISSING"}')
    print(f'Files: {len(names)}, Size: {os.path.getsize("D:/Project/python/iching-server.tar.gz")} bytes')
    # show key line
    for i, line in enumerate(c.split('\n'), 1):
        if 'alinux' in line:
            print(f'  L{i}: {line.strip()[:80]}')
