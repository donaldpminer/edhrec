import cherrypy
import json
import core
import tappedout
import datetime

class API(object):
    _cp_config = {'tools.staticdir.on' : True,
                  'tools.staticdir.dir' : '/home/ubuntu/edhrec-site',
                  'tools.staticdir.index' : 'index.html',
                  '/favicon.ico' : { 'tools.staticfile.on' : True, 'tools.staticfile.filename' : '/home/ubuntu/edhrec-site/favicon.ico' }
    }


    @cherrypy.expose
    def rec(self, to=None, ref=None):
        ip = cherrypy.request.remote.ip

        r = core.get_redis()

        cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"

        if r.exists('api' + str(ip)):
            return json.dumps('Too many API calls. Try again in a few seconds.')
 
        r.set('api' + str(ip), '', ex=1)

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

    @cherrypy.expose
    def cmdr(self, commander):
        cherrypy.response.headers['Access-Control-Allow-Origin'] = "*"

        r = core.get_redis()

        ckey = 'CACHE_COMMANDER_' + commander.replace(' ', '_')
        if r.exists(ckey):
            return r.get(ckey)

        commander = core.sanitize_cardname(commander)

        colors = core.color_identity(commander)

        decks = [ deck for deck in core.get_decks(colors) if deck['commander'] == commander]

        out = {}
        out['numdecks'] = len(decks)

        cards = {}
        for deck in decks:
            for card in deck['cards']:

                cards[card] = {'count' : 0, 'cardname' : card, 'card_info' : core.lookup_card(card)}

        for deck in decks:
            for card in deck['cards']:
                if card == commander: continue
                if card in ['swamp', 'island', 'mountain', 'forest', 'plains']: continue

                cards[card]['count'] += 1

        out['recs'] = [ pp for pp in sorted(cards.values(), key = (lambda x: -1 * x['count'])) if pp['count'] > 1 and pp['count'] > .1 * len(decks) ]

        out['commander'] = commander

        r.set(ckey, json.dumps(out), ex=60*60*24*7) # 7 day cache

        return json.dumps(out)


cherrypy.config.update({'server.socket_host': '172.30.0.88',
                        'server.socket_port': 80,
                        'environment': 'production'                      
 })


cherrypy.tree.mount(API(), '/')
cherrypy.engine.start()

cherrypy.engine.block()

#cherrypy.quickstart(HelloWorld())



