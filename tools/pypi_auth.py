"""Enter a PyPI token privately in your own terminal, inside this checkout."""
import getpass
import os
from pathlib import Path


def main():
    root=Path(__file__).resolve().parents[1]
    token=getpass.getpass('PyPI API token (hidden): ').strip()
    if not token.startswith('pypi-') or any(c.isspace() for c in token):
        raise SystemExit('Expected a PyPI API token beginning with pypi-. Nothing saved.')
    path=root/'.pypi-token'
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|getattr(os,'O_NOFOLLOW',0),0o600)
    with os.fdopen(fd,'w') as file:
        os.fchmod(file.fileno(),0o600)
        file.write(token+'\n')
    print('Authentication saved inside pmon/.pypi-token (Git-ignored, mode 600).')
    print('Tell the assistant authentication is ready. Do not share the token in chat.')


if __name__=='__main__': main()
