from auri.ui import Menu, TextView
from auri.i18n import t


def Casa(sys):
    cfg = sys.config
    try:
        r = sys.hal.request('GET', cfg['bridge_url'] + '/v1/home', None, cfg.get('token'))
    except Exception as e:
        return TextView(sys, t('home'), t('bridge_down'))

    def toggle(eid, name):
        def run():
            try:
                res = sys.hal.request('POST', cfg['bridge_url'] + '/v1/home/toggle', {'id': eid}, cfg.get('token'))
                sys.push(TextView(sys, name[:14], res.get('message', t('done'))))
            except Exception as e:
                sys.push(TextView(sys, t('error'), t('bridge_err')))
        return run

    items = []
    for ent in r.get('entities', []):
        mark = '*' if ent.get('state') == 'on' else ' '
        items.append((mark + ent['name'], toggle(ent['id'], ent['name'])))
    if not items:
        return TextView(sys, t('home'), t('no_devices'))
    return Menu(sys, t('home'), items)
