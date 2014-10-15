import redis
import logging
import json
import time
import datetime
import itertools
import random
import urllib2
import HTMLParser
import hashlib
import re

# this keeps all the code that is shared amongst most of the mdoules and future modules
# it mostly contains redis storage and the recommendation engine stuff


# This is the redis configurations.
# Note: 6379 is the default Redis port, so if you have any other apps
#  hitting against redis, you might want to stand up your own.
REDIS_HOST = 'localhost'
REDIS_PORT = 6379

logging.getLogger().setLevel(logging.DEBUG)

# A global variable that pools a Redis connection.
_REDIS = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=2)

# this is what the scraper will post places
USER_AGENT = "reddit.com/r/edh recommender by /u/orangeoctopus v2.0"



############# UTILITY FUNCTIONS ###############

# Returns a redis instance. This checks to see if the connetion is open
#   and if not creates a new one. Using this function makes it so we don't
#   have to recreate the redis connection every time we want to use it.
def get_redis():
    '''Returns a redis instance using the defaults provided at the top of mr.py'''
    global _REDIS

    try:
        _REDIS.ping()
    except redis.ConnectionError as ce:
        _REDIS = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=2)

    return _REDIS


def hash_pyobj(python_obj):
    return hashlib.sha256(json.dumps(python_obj)).hexdigest()

# Nasty hack of a function that removes all the characters that annoy me in
#    magic cards.
def strip_accents(s):
    return s.replace(u'\xc3', 'ae').replace(u'\xe6', 'ae').replace(u'\xc6', 'ae').replace(u'\xe9', 'e').replace(u'\xf6', 'o') \
            .replace(u'\xfb', 'u').replace(u'\xe2', 'a').replace(u'\xe1', 'a').replace(u'\xe0', 'a') \
            .replace(u'\xae', 'r').replace(u'\xfa', 'u').replace(u'\xed', 'i')

# The official sanitization function. Any cardnames should be sent through this before
#    hitting the data store or whatever.
def sanitize_cardname(cn):
    return HTMLParser.HTMLParser().unescape(strip_accents(cn.strip().lower()))

def date_from_str(dstr):
    return datetime.datetime(*[ int(p) for p in re.split('[ \.:-]', dstr)[:-1]])

# Undoes most of what sanitize_cardname does. This is used for presentation purposes.
def cap_cardname(cn):
    return cn.strip().lower().title().replace("'S", "'s").replace(' The', ' the').replace(' Of', ' of')

# looks up the cardname cn in the redis data store. It turns a nice dictionary object that maps the json object.
def lookup_card(cn):
    try:
        card_obj = json.loads(get_redis().hget('CARDS_JSON', sanitize_cardname(cn)))
    except TypeError:
        logging.warn('I couldn\'t find this card: ' + cn)
        return None

    return card_obj

# figures out the color identitify for a particular card
def color_identity(cn):
    card = lookup_card(cn)

    if card is None:
        raise ValueError('Card doesnt exist ' + cn)

    colors = { '{W}' : 'WHITE' , '{B}' : 'BLACK' , '{U}' : 'BLUE', '{R}' : 'RED', '{G}' : 'GREEN' }
    oc = set()

    for colorsig in colors:
        if card.has_key('manaCost') and colorsig in card['manaCost'].replace('/', '}{'):
            oc.add(colors[colorsig])
        elif card.has_key('text') and colorsig in ' '.join(card['text'].replace(')', '(').split('(')[::2]).replace('/', '}{'):
            oc.add(colors[colorsig])

    return sorted(list(oc))

# returns true if the card is banned
def is_banned(cn):
    return get_redis().sismember('BANNED', sanitize_cardname(cn))

# adds a deck to the redis data store
def add_deck(deck_dict):
    try:
        # prepare the name of the key in redis (it's DECKS_ followed by sorted colors in the color identity, all caps)
        color_str = 'DECKS_' + '_'.join(color_identity(deck_dict['commander']))
    except ValueError:
        logging.warn("This commander doesn't exist, not adding it to my corpus: " + deck_dict['commander'])
        return

    logging.debug('Adding the deck with the commander ' + deck_dict['commander'])

    if deck_dict['commander'] == 'jedit ojanen':
        logging.warn('jedit ojanen means someone submitted a deck without a commander. Im not going to add it')
        return

    # check to see if this exact deck exists already:
    for deck in get_decks(color_identity(deck_dict['commander'])):
        if deck['cards'] == deck_dict['cards']:
            logging.debug('this deck is an exact dup. I\'m not going to add it at all.')
            break
    else:
        # add it to the beginning of the list
        get_redis().lpush(color_str, json.dumps(deck_dict))

# Returns all of the decks for a particular color. Turn dedup on if you want to remove dups
def get_decks(colors, dedup=False):
    if type(colors) is str:
        color_str = colors
    else:
        color_str = 'DECKS_' + '_'.join(sorted(c.upper() for c in colors))

    logging.debug('Retrieving all decks from ' + color_str)

    out =[ json.loads(d) for d in get_redis().lrange(color_str, 0, -1) ]

    if dedup:
        out = dedup_decks(out)

    return out

def get_all_decks(dedup=False):
    deck_strs = get_redis().keys('DECKS_*')

    logging.debug('Retrieving ALLLL decks')

    out = []
    for ds in deck_strs:
        decks = [ json.loads(d) for d in get_redis().lrange(ds, 0, -1) ]
        if dedup:
            decks = dedup_decks(decks)
        out.extend(decks)
       
    return out


# This function wraps a URL get request with a cache.
def urlopen(url):
    # The cache is stored in Redis
    r = get_redis()

    # TODO: I liked how I did caching before. Here I keep everything
    #  in one key, URL_CACHE. Unfortunately, I can't set expirations per
    #  key in a hash, I can only expire top-level keys. This makes it so
    #  you have to flush the cache manually

    if r.hexists('URL_CACHE', url):
        logging.debug("Cache hit on " + url)
        return r.hget('URL_CACHE', url)

    logging.debug("Cache miss on " + url)

    req = urllib2.Request(url, headers={'User-Agent' : USER_AGENT}) 
    con = urllib2.urlopen(req).read()

    r.hset('URL_CACHE', url, con)

    return con

# flushes the entire cache
def flush_cache():
    get_redis().delete('URL_CACHE')


def add_recent(url_ref, commander, reddit_ref = None):
    r = get_redis()

    out = {'url' : url_ref.strip('/'), 'commander' : commander}

    if reddit_ref is not None:
        out['reddit'] = reddit_ref

    s = json.dumps(out)

    r.lrem('RECENT', s, 0)

    r.lpush('RECENT', s) 

    r.ltrim('RECENT', 0, 99)

def get_recent_json():
    return json.dumps(get_redis().lrange('RECENT', 0, -1))



################# RECOMMENDATION ENGINE ######################


# This is one of the most important functions.
# It says how close two decks are. The higher the number,
#   the more close deck1 and deck2 are. The recommendation
#   engine use this closeness score to compute nearest
#   neighbor.
def rec_deck_closeness(deck1, deck2):
    r = get_redis()

    # Find how many non-land cards they have in common
    lenint = 0
    for c in set(deck1['cards']).intersection(set(deck2['cards'])):
        if 'Land' in lookup_card(c)['types']:
            continue
        lenint += 1.0

    # If they share the same commander, give the score a bit of a boost
    # The rationale is that we want decks with the same commander first,
    #   with perhaps some help from other similar commanders if we can't
    #   find enough.
    if deck1['commander'] == deck2['commander']:
        same_cmdr_bonus = 1.2
    else:
        same_cmdr_bonus = 1.0

    # Give a bit of a bonus if the decks are similar in age. If they are
    #  within 90 days of each other (roughly a new set is release every 90 days),
    #  it just gets a 1.0. Otherwise, it slowly degrades. 
    # The rationale here is that we don't want to be basing recommendations
    #  on decks that are 3 years old because they aren't up to date.
    if deck1['date'] - deck2['date'] < 90:
        newness_bonus = 1.0
    else:
        newness_bonus = .99 ** ((deck1['date'] - deck2['date']) / 366.)

    # Compute the final score and return it!
    return lenint * same_cmdr_bonus * newness_bonus


# Determines if two decks are duplicates
# You can adjust it to be more aggressive by making threshold higher.
# Threshold is the number of cards the two decks have in common. 
def decks_are_dups(deck1, deck2, threshold = .7):
    if deck1['commander'] != deck2['commander']:
        return False

    try:
        if deck1['url'] == deck2['url']:
            return True
    except KeyError:
        pass

    # Find out if the difference in number of cards is < threshold. If it is, it's a dup.
    avg_size = (len(deck1['cards']) + len(deck2['cards'])) / 2.0

    in_common = len(set(deck1['cards']).intersection(set(deck2['cards'])))

    if in_common / avg_size > threshold:
        #print avg_size, in_common
        return True
    else:
        return False

# For a list of decks, deduplicate ones that are near duplicates of others in the list
def dedup_decks(decks, threshold = .7):
    sdecks = sorted( decks, key= lambda x: int(x['date']), reverse=True )

    badlist = []
    for (i1, d1), (i2, d2) in itertools.combinations(enumerate(sdecks), 2):
        if d1 in badlist or d2 in badlist:
            continue

        if decks_are_dups(d1, d2, threshold = threshold):
            badlist.append(i2)
            continue

    #for k in badlist: print k, '!!!'

    return [ d for i, d in enumerate(sdecks) if i not in badlist ]


# This function generates the recommendatins for a deck.
# The optional parameter k tells you how far out to cast your net
#    for similar decks. Smaller numbers will have more variance and bias,
#    but larger numbers will degenrate into "goodstuff.dec" for those particular colors.
# See "Collaborative Filtering" on the Google. This approach is based on that.
def recommend(deck, k=15, returnk=False):
    nn = datetime.datetime.now()
    logging.debug("Finding recommendations for deck with general " + str(deck['commander']))

    # Go calculate all of the closeness scores for this deck to all of the other decks in the corpus.
    scores = []
    for deck2 in get_decks(color_identity(deck['commander'])):
        if decks_are_dups(deck, deck2):
            logging.debug("The deck submitted here is a duplicate of another deck in my corpus...")
            continue

        d = rec_deck_closeness(deck, deck2) ** 2  # notice that I square the score.
                # squaring the score makes closer decks weighted higher. I found empirically this gives better results.

        # Keep the score around but also keep the cards that were different.
        scores.append((d, deck2, set(deck2['cards']) - set(deck['cards']), set(deck['cards']) - set(deck2['cards'])))

    # Pull off the top K highest scores. Break ties randomly.
    topk = sorted(scores, key=lambda x: (x[0], random.random()), reverse=True)[:k]

    for dd in topk:
        logging.debug("Deck similar to this one: " + str(strip_accents(dd[1]['commander'])) + ' score: %.2f' % dd[0] )

    total_score = float(sum(ee[0] for ee in topk))

    card_counts = {}
    uniq_counts = {}

    # go through each deck in the top k and tally some cards
    for dist, deck2, newcards, uniqcards in topk:
        for nc in newcards:
            if is_banned(nc):
                continue

            if not nc in card_counts:
                card_counts[nc] = 0.0

            card_counts[nc] += ( dist / total_score )  # dist / total score is what gives weight. 

        for uc in uniqcards:
            if uc == deck['commander']:
                continue

            if not uc in uniq_counts:
                uniq_counts[uc] = 0.0

            uniq_counts[uc] += ( dist / total_score )

    # Get ordered lists of card counts
    newrecs = sorted(card_counts.items(), key=lambda x:x[1], reverse=True)
    outrecs = sorted(uniq_counts.items(), key=lambda x:x[1], reverse=True)

    logging.debug("Done finding recommendations for deck with general " + str(deck['commander']) + " (took %s time)" % str(datetime.datetime.now() - nn))

    if returnk:
        return newrecs, outrecs, [ deck for _, deck, _, _ in topk ]
    else:
        return newrecs, outrecs

