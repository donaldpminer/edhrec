#!/usr/bin/env python

import cherrypy
import json
import core
import tappedout
import datetime
import logging
import deckstats
import random

COMMANDERS = sorted( core.sanitize_cardname(cn.decode('utf-8').strip().lower()) for cn in open('commanders.txt').readlines() )

def closest_commander(partial_name):
    pn = core.sanitize_cardname(partial_name)

    for cn in COMMANDERS:
        if pn == cn:
            return cn

    for cn in COMMANDERS:
        if cn.startswith(pn):
            return cn

    for cn in COMMANDERS:
        if pn in cn:
            return cn


class API(object):
    _cp_config = {'tools.staticdir.on' : True,
                  'tools.staticdir.dir' : '/home/ubuntu/edhrec-site',
                  'tools.staticdir.index' : 'index.html',
                  '/favicon.ico' : { 'tools.staticfile.on' : True, 'tools.staticfile.filename' : '/home/ubuntu/edhrec-site/favicon.ico' }
    }


    @cherrypy.expose
    def rec(self, to=None, ref=None):
        to = to[:500]

        if ref is None:
           ref = "No ref"

        ref = ref[:20]

        cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"

        if not 'tappedout.net/mtg-decks' in to:
            raise ValueError('invalid deck url %s . it should look like http://tappedout.net/mtg-decks/xxxx' % to)

        ip = cherrypy.request.remote.ip

        r = core.get_redis()


        if r.exists('api' + str(ip)):
            logging.warn('%s ip is overloading' % str(ip))
            return json.dumps('Too many API calls. Try again in a few seconds.')
 
        r.set('api' + str(ip), '', ex=1)

	if tappedout is None:
            return json.dumps(None)



        deck = tappedout.get_deck(to)

        if deck['commander'] == 'jedit ojanen':
            raise ValueError('You input a deck without a valid commander. Please go back and add it to the web interface.')


        core.add_recent(to, \
                    core.cap_cardname(deck['commander']))


        hashkey = 'CACHE_REC_' + core.hash_pyobj([deck['cards']] + [deck['commander']])
        
        if r.exists(hashkey):
            return r.get(hashkey)

        newrecs, outrecs, topk = core.recommend(deck, returnk=True)

        outnewrecs = []
        for cn, sc in newrecs:
            if sc < .3:
                continue
            try:
                cd = { 'score' : sc, 'card_info' : {'name': core.lookup_card(cn)['name'], 'types': core.lookup_card(cn)['types']} }
            except TypeError:
                logging.warn('The card %s failed to do lookup card.' % cn)
                continue
            outnewrecs.append(cd)

        outoutrecs = []
        for cn, sc in outrecs:
            if sc < .5:
                continue
            try:
                cd = { 'score' : sc, 'card_info' : {'name': core.lookup_card(cn)['name'], 'types': core.lookup_card(cn)['types']} }
            except TypeError:
                logging.warn('The card %s failed to do lookup card.' % cn)
                continue
            outoutrecs.append(cd)
 
        #newrecs = [ { 'score' : sc, 'card_info' : {'name': core.lookup_card(cn)['name'], 'types': core.lookup_card(cn)['types']} } for cn, sc in newrecs if sc > .3 ]
        #outrecs = [ { 'score' : sc, 'card_info' : {'name': core.lookup_card(cn)['name'], 'types': core.lookup_card(cn)['types']} } for cn, sc in outrecs if sc > .5 ]

        deck['url'] = to

        if ref is not None:
            deck['ref'] = ref
        else:
            deck['ref'] = 'non-ref api call'

        deck['ip'] = str(ip)
        try:
            deck['headref'] = cherrypy.request.headerMap['Referer']
        except AttributeError:
            pass

        deck['scrapedate'] = str(datetime.datetime.now())

        core.add_deck(deck)

        stats = deckstats.tally([deck])
        kstats = deckstats.tally(topk)
        cstats = deckstats.get_commander_stats(deck['commander'])

        output_json = json.dumps({'url' : to, 'recs' : outnewrecs, 'cuts' : outoutrecs, \
                                  'stats' : stats, 'kstats' : kstats, 'cstats' : cstats})

        r.set(hashkey, output_json, ex=60*60*24*3) # 3 days expiration

        ckey = 'CACHE_COMMANDER_' + deck['commander'].replace(' ', '_')
        r.delete(ckey)

        return output_json

    @cherrypy.expose
    def cmdr(self, commander):
        commander = commander[:50]

        cherrypy.response.headers['Access-Control-Allow-Origin'] = "*"

        r = core.get_redis()

        commander = core.sanitize_cardname(commander)

        commander = closest_commander(commander)

        r = core.get_redis()

        ckey = 'CACHE_COMMANDER_' + commander.replace(' ', '_')
        if r.exists(ckey):
            return r.get(ckey)

        colors = core.color_identity(commander)

        decks = [ deck for deck in core.get_decks(colors) if deck['commander'] == commander]

        out = {}
        out['numdecks'] = len(decks)

        cards = {}
        for deck in decks:
            for card in deck['cards']:

                try:
                    cards[card] = {'count' : 0, 'card_info' : {'name' : core.lookup_card(card)['name'], \
                                                               'types' : core.lookup_card(card)['types'], \
                                                               'colors' : core.lookup_card(card).get('colors', []), \
                                                               'cmc' : core.lookup_card(card).get('cmc', 0) \
                                       } }
                except TypeError:
                    logging.warn("for some reason card %s could not be looked up, ignoring." % card)
                    continue
 

        for deck in decks:
            for card in deck['cards']:
                if card == commander: continue
                if card in ['swamp', 'island', 'mountain', 'forest', 'plains']: continue

                try:
                    cards[card]['count'] += 1
                except KeyError:
                    continue

        #out['recs'] = [ pp for pp in sorted(cards.values(), key = (lambda x: -1 * x['count'])) if pp['count'] > 1 and pp['count'] > .1 * len(decks) ]
        out['recs'] = [ pp for pp in sorted(cards.values(), key = (lambda x: -1 * x['count'])) if pp['count'] > 1 ][:125]

        out['commander'] = core.cap_cardname(commander)

        out['stats'] = deckstats.get_commander_stats(commander)

        r.set(ckey, json.dumps(out), ex=60*60*24*2) # 2 day cache

        return json.dumps(out)

    @cherrypy.expose
    def cmdrdeck(self, commander):
        commander = commander[:50]
        cherrypy.response.headers['Access-Control-Allow-Origin'] = "*"
        cherrypy.response.headers['Content-Type'] = 'text/plain'

        try:
            cmdr_out = json.loads(self.cmdr(commander))
        except ZeroDivisionError:
            return "Unfortunately, there are not enough decks in my database for '%s', so I can't generate a list" % commander

        colors = [ clr for clr, cnt in cmdr_out['stats']['colors'].items() if cnt > 0 ]

        lands = cmdr_out['stats']['lands']
        nonlands = cmdr_out['stats']['nonlands']
        outdeck = []

        landmap = {'Red' : 'Mountain', 'Blue' : 'Island', 'Black' : 'Swamp', 'White' : 'Plains', 'Green' : 'Forest' }
        lands -= len(colors) 

        for rec_dict in cmdr_out['recs']:
             if 'Land' in rec_dict['card_info']['types'] and lands > 0:
                 outdeck.append(rec_dict)
                 lands -= 1
                 continue

             if (not 'Land' in rec_dict['card_info']['types']) and nonlands > 0:
                 outdeck.append(rec_dict)
                 nonlands -= 1
                 continue
             

        # fill out the lands
        total = sum( cnt for clr, cnt in cmdr_out['stats']['colors'].items() )
        old_lands = lands
        basics = dict(zip(colors, [0] * len(colors)))

        for color, count in cmdr_out['stats']['colors'].items():
            if count == 0 : continue
            num = int( float(count) / total * old_lands ) + 1
            lands -= num
            basics[color] += num

        # tack on a card if we are at 99
        if lands + nonlands > 2:
            logging.warn('deck built had less than 98 cards... thats weird... %d' % len(outdeck))

        while lands + nonlands > 0:
            basics[random.choice(colors)] += 1
            lands -= 1

        out = {}
        out['cards'] = outdeck
        out['basics'] = [ (landmap[color], count) for color, count in basics.items()] 
        out['commander'] = cmdr_out['commander']

        out['stats'] = deckstats.tally([ { 'cards' : [ core.sanitize_cardname(c['card_info']['name']) for c in out['cards'] ] }  ])

        return json.dumps(out)

    @cherrypy.expose
    def recent(self):
        cherrypy.response.headers['Access-Control-Allow-Origin'] = "*"

        return core.get_recent_json()

    @cherrypy.expose
    def stats(self):
        cherrypy.response.headers['Access-Control-Allow-Origin'] = "*"

        r = core.get_redis()

        ckey = 'CACHE_STATS'
        if r.exists(ckey):
            return r.get(ckey)


        out = {}
 
        w_counts = {}
        m_counts = {}
        for d in core.get_all_decks():
            if not d.has_key('scrapedate'): continue

            datedelta = (datetime.datetime.now() - core.date_from_str(d['scrapedate'])).days

            if datedelta <= 30:
                m_counts.setdefault(core.cap_cardname(d['commander']), 0)
                m_counts[core.cap_cardname(d['commander'])] += 1
            if datedelta <= 7:
                w_counts.setdefault(core.cap_cardname(d['commander']), 0)
                w_counts[core.cap_cardname(d['commander'])] += 1

        out['topweek'] = sorted(w_counts.items(), key= lambda x: x[1], reverse=True)[:25]
        out['topmonth'] = sorted(m_counts.items(), key= lambda x: x[1], reverse=True)[:25]

        alltime_counts = {}
        for d in core.get_all_decks():
            alltime_counts.setdefault(core.cap_cardname(d['commander']), 0)
 
            alltime_counts[core.cap_cardname(d['commander'])] += 1

        out['topalltime'] = sorted(alltime_counts.items(), key= lambda x: x[1], reverse=True)[:25]

        out['deckcount'] = len(core.get_all_decks())

        r.set(ckey, json.dumps(out), ex=60*60*3) # 3 hour cache
        return json.dumps(out)



if __name__ == "__main__":
    cherrypy.config.update({'server.socket_host': raw_input('your ip').strip(),
                        'server.socket_port': 80,
                        'environment': 'production'
 })


    logging.basicConfig(filename='api.log')

    cherrypy.tree.mount(API(), '/')
    cherrypy.engine.start()
    cherrypy.engine.block()






