from functools import partial
from flask import Flask, request, Response, render_template, jsonify
from legiscal.cal import gen_ical, fetch_bodies

app = Flask(__name__)
BASEURL = 'https://webapi.legistar.com/v1/'
known_namespaces = {
    'San Jose': 'sanjose',
    'Sunnyvale': 'sunnyvaleca',
    'Santa Clara': 'santaclara',
    'Mountain View': 'mountainview',
    'Cupertino': 'cupertino',
    'BART': 'bart',
}


@app.route('/test')
def test():
    options = ('text/calendar', 'text/html')
    return request.accept_mimetypes.best_match(options)


@app.route('/')
def root():
    return render_template(
        'index.html',
        known_namespaces=known_namespaces
    )


@app.route('/b/<namespace>')
def bodies(namespace):
    bodies = fetch_bodies(namespace)
    renderers = {
        'application/json': jsonify,
        'text/html': lambda b: render_template(
            'bodies.html', namespace=namespace, bodies=b
        )
    }
    renderer = request.accept_mimetypes.best_match(
        ('application/json', 'text/html')
    )
    return renderer(bodies)


@app.route('/c/<namespace>')
async def cal(namespace):
    body_list = request.args.getlist('b')
    nscal = await gen_ical(namespace, bodies=body_list)
    calbin = nscal.to_ical()
    resp = Response(calbin, mimetype='text/calendar')
    return resp
