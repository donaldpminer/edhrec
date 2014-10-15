import core
import datetime
import json



def tally(decks):
    types = {u'Creature' : 0, u'Enchantment' : 0, u'Sorcery' : 0, \
             u'Instant' : 0, u'Artifact' : 0, u'Planeswalker' : 0}
    curve = {'0':0, '1':0, '2':0, '3':0, '4':0, '5':0, '6':0, '7':0, '8+':0}
    colors= {u'Red' : 0, u'Blue' : 0, u'Green' : 0, u'White' : 0, u'Black' : 0}

    c = 0
    for deck in decks:
        c += 1
        for card in deck['cards']:
            cd = core.lookup_card(card)

            if cd is None:
                continue

            for t in cd['types']:
                if not t in  types.keys(): continue
                types[t] += 1
 
            if cd.has_key('cmc'):
                if cd['cmc'] >= 8: 
                    curve['8+'] += 1
                else:
                    curve[str(cd['cmc'])] += 1

            if cd.has_key('colors'):
                if u'Land' in cd['types']: continue
                for col in cd['colors']:
                    colors[col] += 1


    for key in types:
        types[key] /= c
    for key in curve:
        curve[key] /= c
    for key in colors:
        colors[key] /= c

    out = {}
    out['types'] = types
    out['curve'] = sorted(curve.items())
    out['colors'] = colors
    return out

def get_global_stats():
    out = tally(core.get_all_decks())
    return out

def get_commander_stats(commander):

    ds = []
    for deck in core.get_decks(core.color_identity(commander)):
        if deck['commander'] == core.sanitize_cardname(commander):
           ds.append(deck)

    out = tally(ds)
    out['commander'] = core.cap_cardname(commander)

    return out


#print get_commander_stats('omnath, locus of mana')
#print get_commander_stats('Mayael the Anima')
#print get_commander_stats('animar, soul of elements')



#r = core.get_redis()
#r.rename('STATS_GLOBAL', 'OLD_STATS_GLOBAL')
#r.set('STATS_GLOBAL', json.dumps(get_global_stats()))
