

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
import logging


def scrape_deck(url_str):
    logging.debug('scraping a deck for %s' url_str)

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
#            raise ValueError("This deck has %d cards... that's bad." % num_cards)
             pass

        if not core.lookup_card(deck[0]).has_key(u'supertypes') or not u'Legendary' in core.lookup_card(deck[0])[u'supertypes']:
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


def frontpage(pages=1):
    url = 'http://www.mtgsalvation.com/forums/the-game/commander-edh/multiplayer-commander-decklists?page=%d' % pages

    logging.debug('Looking at page %d of the multiplayer decklists' % pages)

    content = urllib2.urlopen(url).read()
    parsed = bs.BeautifulSoup(content)
    anchors = parsed.findAll('a')

    decklinks = []
    for a in anchors:
        attrs = dict(a.attrs)
        if not attrs.has_key('href'):
            continue

        href = attrs['href'].split('?',1)[0]

        if not '/forums/the-game/commander-edh/multiplayer-commander-decklists/' in href:
            continue

        if href in decklinks:
            continue

        decklinks.append(href)

    # recursively call the next page
    return ([] if pages == 1 else frontpage(pages - 1)) + decklinks

if __name__ == '__main__':

    for link in frontpage(pages=5):
        try:
            url = 'http://www.mtgsalvation.com' + link

            cachekey = 'CACHE_MTGSALVATION_%s' % url
            if not core.get_redis().get(cachekey) is None:
                continue

            core.get_redis().set(cachekey, str(datetime.datetime.now()), ex=60*60*24*3) # 3 day cache)

            deck = scrape_deck(url)
            core.add_deck(deck)
            core.add_recent(url, core.cap_cardname(deck['commander']))
 
        except Exception, e:
            logging.debug('for "%s" : %s' % (url, e))


