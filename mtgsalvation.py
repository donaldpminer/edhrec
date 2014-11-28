

# a deck is made out of:
#   url   let's make this T/O specific
#   mtgsalvation    <-- this is the new URL
#   ip of the person who submitted it
#   scrapedate  2014-11-08 01:56:25.872182
#   commander   "taniwha"
#   cards     cleansed names
#   ref     mtgsalvation

import urllib2
import BeautifulSoup as bs
import json
import core
import datetime

def scrape_deck(url_str):
    content = urllib2.urlopen(url_str).read()
    parsed = bs.BeautifulSoup(content)
    tables = parsed.findAll('table')

    deck = []
    # find the deck
    for t in tables:
        attrs = dict(t.attrs)
        if attrs['class'] != u'deck':
            continue

        data = json.loads(attrs['data-card-list'])

        num_cards = 0
        for card in data['Deck']:
            num_cards += card['Qty']
            deck.append(core.sanitize_cardname(card['CardName']))

        if num_cards < 95 or num_cards > 102:
            raise ValueError("This deck has %d cards... that's bad." % num_cards)

        if not u'Legendary' in core.lookup_card(deck[0])[u'supertypes']:
            raise ValueError("The first card in this deck is not legendary.")

        break
    else:
        raise ValueError("I couldn't find a deck in this post")

    out = {}
    out['mtgsalvation'] = url_str
    out['scrapedate'] = str(datetime.datetime.now())
    out['commander'] = deck[0]
    out['cards'] = sorted(deck)
    out['ref'] = 'mtgsalvation'

    return out


