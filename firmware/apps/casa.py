from auri.ui import Menu, TextView


def Casa(sys):
    cfg = sys.config
    try:
        r = sys.hal.request('GET', cfg['bridge_url'] + '/v1/home', None, cfg.get('token'))
    except Exception as e:
        return TextView(sys, 'Casa', 'Bridge non raggiungibile.\n' + str(e)[:60])

    def toggle(eid, name):
        def run():
            try:
                res = sys.hal.request('POST', cfg['bridge_url'] + '/v1/home/toggle', {'id': eid}, cfg.get('token'))
                sys.push(TextView(sys, name[:14], res.get('message', 'Fatto')))
            except Exception as e:
                sys.push(TextView(sys, 'Errore', str(e)[:60]))
        return run

    items = []
    for ent in r.get('entities', []):
        mark = '*' if ent.get('state') == 'on' else ' '
        items.append((mark + ent['name'], toggle(ent['id'], ent['name'])))
    if not items:
        return TextView(sys, 'Casa', 'Nessun dispositivo configurato nel bridge.')
    return Menu(sys, 'Casa', items)
