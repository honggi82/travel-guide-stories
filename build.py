"""Validate source-linked stories and build byte-exact regional packs."""
from pathlib import Path
import hashlib
import json
import re
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
BASE = 'https://raw.githubusercontent.com/honggi82/travel-guide-stories/main/'


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def validate_place(place):
    assert re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}', place['id'])
    assert place['name']['ko'].strip() and place['city']
    assert -90 <= place['lat'] <= 90 and -180 <= place['lon'] <= 180
    text = place['scripts']['ko']
    assert 200 <= len(text) <= 6000
    assert not re.search(r'\?{3,}|\ufffd|\u3000', text)
    assert len(set(text.split('\n\n'))) == len(text.split('\n\n'))
    assert place['sources'] and any('wikipedia.org/wiki/' in s['url'] for s in place['sources'])
    assert all(s['url'].startswith('https://') and s['title'] for s in place['sources'])
    assert re.fullmatch(r'\d{4}-\d{2}-\d{2}', place['researchedAt'])


def build():
    if (ROOT / 'index.json').exists():
        raise RuntimeError('Initial builder requires an empty output catalog; published packs must be updated with version increments.')
    groups = {}
    for story in json.loads((ROOT / 'stories.json').read_text(encoding='utf-8')):
        place = {k: story[k] for k in ['id', 'name', 'aliases', 'city', 'lat', 'lon']}
        place.update(scripts={'ko': story['text']}, researchedAt='2026-11-15', author='Codex',
                     sources=[{'title': 'Wikipedia: ' + story['wiki'].replace('_', ' '),
                               'url': 'https://en.wikipedia.org/wiki/' + quote(story['wiki'])}],
                     mapsUrl='https://www.google.com/maps/search/?api=1&query=' + quote(story['name']['en'] + ' ' + story['city'][0]),
                     mapsVerification='pending', coordinatePrecision='reference', license='CC-BY-SA-4.0')
        validate_place(place)
        groups.setdefault(story['region'], []).append(place)
    directory = ROOT / 'packs'
    directory.mkdir(exist_ok=True)
    regions = []
    seen = set()
    for region, places in sorted(groups.items()):
        assert len({p['id'] for p in places}) == len(places)
        for p in places:
            assert (region, p['id']) not in seen
            seen.add((region, p['id']))
        pack = dict(schemaVersion=2, id=region, version=1, name={'ko': places[0]['city'][-1]},
                    languages=['ko'], attribution='Original Korean narration by Codex, based on linked Wikipedia facts. CC BY-SA 4.0. No Google reviews or images copied.', places=places)
        payload = encoded(pack)
        (directory / (region + '.json')).write_bytes(payload)
        regions.append(dict(id=region, name=pack['name'], version=1, placeCount=len(places),
                            sizeBytes=len(payload), sha256=hashlib.sha256(payload).hexdigest(),
                            url=BASE + 'packs/' + region + '.json',
                            places=[{k:p[k] for k in ['id','name','aliases','city','lat','lon']} for p in places]))
    index = dict(schemaVersion=2, updatedAt='2026-11-15', regions=regions)
    (ROOT / 'index.json').write_bytes(encoded(index))
    return index


if __name__ == '__main__':
    value = build()
    print(json.dumps({'regions': len(value['regions']), 'places': sum(r['placeCount'] for r in value['regions'])}))
