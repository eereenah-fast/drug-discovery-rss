"""Maintain public metadata on radar-data without committing app code or credentials."""
import json
from pathlib import Path
import subprocess
import sys

BRANCH = 'radar-data'
FILE = Path('public/data/feed.json')

def git(*args, input=None, check=True):
    return subprocess.run(['git', *args], input=input, text=True, capture_output=True, check=check)

def remote_head():
    result = git('ls-remote', '--exit-code', '--heads', 'origin', BRANCH, check=False)
    if result.returncode == 2:
        return None
    if result.returncode:
        raise RuntimeError('Cannot inspect saved data branch; refusing to overwrite potentially newer records.')
    git('fetch', '--no-tags', 'origin', BRANCH)
    return git('rev-parse', 'FETCH_HEAD').stdout.strip()

def main(mode):
    head = remote_head()
    if mode == 'restore':
        if head:
            raw = git('show', f'{head}:feed.json').stdout
            data = json.loads(raw)
            if data.get('schema_version') != 1 or not isinstance(data.get('items'), list):
                raise ValueError('Saved feed schema is invalid')
            FILE.parent.mkdir(parents=True, exist_ok=True)
            FILE.write_text(raw)
            print(f'Restored {len(data["items"])} research records.')
        else:
            print('First run: starting from the supplied research snapshot.')
    elif mode == 'save':
        blob = git('hash-object', '-w', str(FILE)).stdout.strip()
        tree = git('mktree', input=f'100644 blob {blob}\tfeed.json\n').stdout.strip()
        if head and git('rev-parse', f'{head}^{{tree}}').stdout.strip() == tree:
            print('Research records are unchanged.')
            return
        parent = ['-p', head] if head else []
        commit = git('-c', 'user.name=Discovery Radar', '-c', 'user.email=radar@users.noreply.github.com',
                     'commit-tree', tree, *parent, '-m', 'Refresh public research metadata').stdout.strip()
        # Normal push only. A concurrent writer causes failure rather than data loss.
        git('push', 'origin', f'{commit}:refs/heads/{BRANCH}')
        print('Saved research records to radar-data.')
    else:
        raise ValueError('Use restore or save')

if __name__ == '__main__':
    main(sys.argv[1])
