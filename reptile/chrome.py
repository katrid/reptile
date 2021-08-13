import base64
import json
import requests
import websockets


mm = 0.0393701


async def aprint_to_pdf(frame_id, url, html, report_footer=None):
    async with websockets.connect(url, max_size=1024 * 1024 * 1024) as ws:
        await ws.send(json.dumps({
            'id': 1,
            'method': 'Page.stopLoading',
        }))
        res = await ws.recv()
        print(res)
        await ws.send(json.dumps({
            'id': 2,
            'method': 'Page.enable',
        }))
        res = await ws.recv()
        print(res)
        await ws.send(json.dumps({
            'id': 3,
            'method': 'Page.navigate',
            'params': {
                'url': html,
            }
        }))
        while True:
            res = json.loads(await ws.recv())
            print(res)
            if res.get('method') == 'Page.frameStoppedLoading':
                break
        await ws.send(json.dumps({
            'id': 4,
            'method': 'Page.printToPDF',
            'params': {
                'printBackground': True,
                'marginTop': 0,
                'marginBottom': 0,
                'marginRight': 0,
                'marginLeft': 0,
                'preferCSSPageSize': True,
                'displayHeaderFooter': True,
                'headerTemplate': '<div class="title">teste</div><span class="pageNumber"></span>',
                'footerTemplate': report_footer,
            }
        }))
        while True:
            res = json.loads(await ws.recv())
            if 'id' in res and res['id'] == 4:
                res = res['result']
                break
        return base64.decodebytes(res['data'].encode('utf-8'))


def print_to_pdf(loop, html, report_footer=None, host='localhost'):
    res = requests.get(f'http://{host}:9222/json/new?')
    data = res.json()
    url = data['webSocketDebuggerUrl']
    return loop.run_until_complete(aprint_to_pdf(data['id'], url, html, report_footer=report_footer))
