import cherrypy
import json
import core
import tappedout
import datetime

class API(object):
    _cp_config = {'tools.staticdir.on' : True,
                  'tools.staticdir.dir' : '/home/ubuntu/edhrec-site',
                  'tools.staticdir.index' : 'index.html',
    }


    @cherrypy.expose
    def rec(self, to=None, ref=None):
        ip = cherrypy.request.remote.ip

        r = core.get_redis()

        #cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"

        #if r.exists('api' + str(ip)):
        #    return json.dumps('Too many API calls. Try again in a few seconds.')
 
        #r.set('api' + str(ip), '', ex=5)

	if tappedout is None:
            return json.dumps(None)



        deck = tappedout.get_deck(to)

        newrecs, outrecs = core.recommend(deck)

        newrecs = [ { 'cardname' : cn, 'score' : sc, 'card_info' : core.lookup_card(cn)} for cn, sc in newrecs if sc > .3 ]
        outrecs = [ { 'cardname' : cn, 'score' : sc, 'card_info' : core.lookup_card(cn)} for cn, sc in outrecs if sc > .5 ]

        deck['url'] = to

        if ref is not None:
            deck['ref'] = ref
        else:
            deck['ref'] = 'non-ref api call'

        deck['scrapedate'] = str(datetime.datetime.now())

        core.add_deck(deck)

        return json.dumps({'url' : to, 'recs' : newrecs, 'cuts' : outrecs})


cherrypy.config.update({'server.socket_host': '172.30.0.88',
                        'server.socket_port': 80,
                        'environment': 'production'                      
 })


cherrypy.tree.mount(API(), '/')
cherrypy.engine.start()

cherrypy.engine.block()

#cherrypy.quickstart(HelloWorld())



