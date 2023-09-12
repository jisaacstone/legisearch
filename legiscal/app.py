import json
import urllib
from flask import Flask, request, Response, render_template
from legiscal.cal import gen_ical, fetch_bodies

app = Flask(__name__)
BASEURL = 'https://webapi.legistar.com/v1/'
known_namespaces = {
    'San Jose': 'sanjose',
    'Sunnyvale': 'sunnyvaleca',
    'Santa Clara': 'santaclara',
    'Mountain View': 'mountainview',
    'Cupertino': 'cupertino',
}


@app.route('/')
def root():
    return render_template(
        'index.html',
        known_namespaces=known_namespaces
    )


@app.route('/b/<namespace>')
def bodies(namespace):
    return render_template(
        'bodies.html',
        namespace=namespace,
        bodies=fetch_bodies(namespace)
    )


@app.route('/c/<namespace>')
async def cal(namespace):
    body_list = request.args.getlist('b')
    nscal = await gen_ical(namespace, bodies=body_list)
    calbin = nscal.to_ical()
    resp = Response(calbin, mimetype='text/calendar')
    return resp
