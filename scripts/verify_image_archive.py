"""Check a Docker-save archive without extracting its filesystem or executing it."""
import argparse
import json
import re
import tarfile


def verify(path, source_sha):
    if not re.fullmatch(r'[0-9a-f]{40}', source_sha):
        raise ValueError('Use a full Git source commit SHA')
    # crane push expects the uncompressed docker-save tar, not a .tar.gz.
    with tarfile.open(path, 'r:') as archive:
        manifest = json.load(archive.extractfile('manifest.json'))
        if not isinstance(manifest, list) or len(manifest) != 1:
            raise ValueError('Expected exactly one image')
        config_member = archive.getmember(manifest[0]['Config'])
        if not config_member.isfile() or config_member.size > 1_000_000:
            raise ValueError('Invalid image configuration')
        config = json.load(archive.extractfile(config_member))
    if config.get('config', {}).get('Labels', {}).get('org.opencontainers.image.revision') != source_sha:
        raise ValueError('Image source revision does not match the checkout')
    if config.get('os') != 'linux' or config.get('architecture') != 'amd64':
        raise ValueError('Expected the tested linux/amd64 image')
    return {'verified': True, 'source_revision': source_sha, 'platform': 'linux/amd64'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', required=True)
    parser.add_argument('--source-sha', required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.archive, args.source_sha)))
