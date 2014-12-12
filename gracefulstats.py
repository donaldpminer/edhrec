import re
import json
import urllib2
import core

URL_PATTERN = re.compile('.*(https?://(?:www\.)?(?:beta\.)?gracefulstats\.com/deck/view/([0-9]+)).*')

name = "gracefulstats"


# Given a gracefulstats deck ID, get me the tuple:
#    (commander, deck contents (cards), color identity, the date the deck was updated)
def get_deck(id):
    id = str(id)

    url = 'http://api.gracefulstats.com/1.0/deck/view?id=' + id + '&cards=true'
    try:
        con = core.urlopen(url)
    except urllib2.HTTPError as e:
        logging.warning('Someone posted a bad URL: ' + url + ' (%s) ' % str(e))
        return None

    deck = set()

    deckObject = json.loads(con)

    colorIdentity = deckObject['deck']['color_identity']
    name = deckObject['deck']['name']

    deckFormat = deckObject['deck']['format']['name']

    if (deckFormat != 'Commander'):
        raise ValueError("This isn't a commander deck, try to change the type to commander")

    commander = deckObject['deck']['commander']['name']

    for card in deckObject['deck']['cards']:
        deck.add(core.sanitize_cardname(card['name']))

    out_deck = {
        'commander': core.sanitize_cardname(commander),
        'cards': sorted(list(deck)),
        'date': deckObject['deck']['created'],
        'ref': 'gracefulstats'
    }

    return out_deck

def scrapedeck(url_str):
   m = URL_PATTERN.match(url_str)

   if m is None:
       raise ValueError("This doesn't seem to be a valid gracefulstats url")

   return get_deck(m.group(2)) 


#print scrapedeck('http://www.gracefulstats.com/deck/view/9349')
