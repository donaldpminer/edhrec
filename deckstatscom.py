import urllib2
import core
import logging
import datetime
import random
import re


EXPORT_APPEND = '?export_dec=1'

URL_PATTERN = re.compile('.*(https?://w?w?w?.?deckstats.net/decks/[0-9]+/[0-9]+-.*?/).*')
URL_PATTERN2 = re.compile('.*(https?://w?w?w?.?deckstats.net/deck-[0-9]+-[0-9a-f]+.html).*')


def guess_commander(cards, text=''):
    text = text.lower().strip().replace('and', '').replace('or', '').replace('of', '').replace('the', '')
    text = ''.join( c for c in text if c.isalpha() or c == ' ' )

    candidates = []
    colors = set()

    for cardname in cards:
        card = core.lookup_card(cardname)

        if card is None:
            logging.warn('ignoring this card %s because i couldnt find it' % cardname)
            continue

        try:
            if 'Legendary' in card['supertypes'] and 'Creature' in card['types']:
                candidates.append(cardname)

                colors = colors.union(set(core.color_identity(cardname)))
        except KeyError:
            continue

    colors = sorted(colors)

    candidates = [ cardname for cardname in candidates if core.color_identity(cardname) == colors ]

    if len(candidates) == 0:
        raise ValueError("There is no good commander option for this pool of cards")

    if len(candidates) == 1:
        return candidates[0]

    wordmatch = []
    for cardname in candidates:
        ncardname = ''.join( c for c in cardname if c.isalpha() or c == ' ' )
        tokens = [ k.rstrip('s') for k in ncardname.split() ]
        texttokens = [ k.rstrip('s') for k in text.split() ]
        logging.debug(str(tokens) + ' vs. ' + str(texttokens) + ' (word match)')
        c = len( [t for t in tokens if t.rstrip('s') in texttokens] )
        wordmatch.append((c, cardname))

    wordmatch.sort(reverse=True)

    logging.debug("There are multiple candidates, these are the scores: %s" % str(wordmatch))

    return wordmatch[0][1]

def scrapedeck(url_str):
    logging.debug('attempting to scrape the deckstats url: %s ' % url_str)

    url_fetch = url_str + EXPORT_APPEND

    logging.debug("going to go fetch '%s'" %url_fetch)

    try:
        content = urllib2.urlopen(url_fetch).readlines()
    except:
        raise ValueError("Invalid URL '%s'" % url_str)

    text = content[0][len('//NAME: '):-len('from DeckStats.net') - 2]
    logging.debug('The name of this deck is: %s' % text)

    cards = set()
    sideboard = set()
    for line in content:
        line = line.split('//')[0]
        line = line.split('#')[0]
        line = line.strip()

        if len(line) == 0:
            continue

        if line.startswith('SB:'):
            sideboard.add(core.sanitize_cardname(line.split(' ', 2)[2]))
            line = line[4:]

        if not line[0] in '0123456789':
            raise ValueError("This isn't a valid line of the form '# Card Name': %s " % line)

        cardname = core.sanitize_cardname(line.split(' ', 1)[1])
        

        cards.add(cardname)

    commander = None
    if len(sideboard) == 1:
        cardname = list(sideboard)[0]
        card = core.lookup_card(cardname)

        if card.has_key('supertypes') and 'Legendary' in card['supertypes']:
            commander = list(sideboard)[0]

    if commander is None:
        commander = guess_commander(cards, text)

    out = {}

    out['url'] = url_str
    out['scrapedate'] = str(datetime.datetime.now())
    out['commander'] = commander
    out['cards'] = sorted( cards )
    out['ref'] = 'deckstats'


    return out

#print scrapedeck('http://deckstats.net/decks/11763/98275-athreos-god-of-passage/en')
#print scrapedeck('http://deckstats.net/decks/20915/121652-mayael-lords-and-ladies/en')
