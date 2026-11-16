"""Build a native CLI from an exact module version with a packaging-owned default."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

CLI_MODULE = 'github.com/tianacloud/cli'


def resolve_source(version, local_source=None):
    if local_source is not None:
        return Path(local_source).resolve(), {
            'Path': CLI_MODULE, 'Version': f'v{version}', 'local_source': True,
        }
    with tempfile.TemporaryDirectory(prefix='tiana-cli-source-') as temporary:
        downloaded = json.loads(subprocess.check_output(
            ['go', 'mod', 'download', '-json', f'{CLI_MODULE}@v{version}'],
            cwd=temporary, text=True, env={**os.environ, 'GOWORK': 'off'}))
    return Path(downloaded['Dir']), {
        key: downloaded[key] for key in ['Path', 'Version', 'Sum', 'GoModSum', 'Origin']
        if key in downloaded
    }


def build_binary(source, version, acquisition_source, goos, goarch, command='tiana'):
    with tempfile.TemporaryDirectory(prefix='tiana-channel-build-') as temporary:
        target = Path(temporary) / 'binary'
        subprocess.run([
            'go', 'build', '-mod=readonly', '-buildvcs=false', '-trimpath',
            '-ldflags', f'-s -w -X main.version={version} -X {CLI_MODULE}/internal/buildconfig.DefaultAcquisitionSource={acquisition_source}',
            '-o', str(target), f'./cmd/{command}',
        ], cwd=source, check=True, env={
            **os.environ, 'GOWORK': 'off', 'GOFLAGS': '',
            'GOOS': goos, 'GOARCH': goarch, 'CGO_ENABLED': '0',
        })
        return target.read_bytes()
