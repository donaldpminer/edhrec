import core
import json
import logging

def load_cards_from_json(file_path):
    r = core.get_redis()

    writecount = 0

    # Go through each card in the set...
    for card, conts in json.load(open(file_path)).items():
        # If it has names, it's a split card or fuse card or something
        if conts.has_key('names'):
            cardname = core.sanitize_cardname('/'.join(conts['names'])).lower()

            for name in conts['names']:
                r.hset('CARDS_JSON', core.sanitize_cardname(name), json.dumps(conts))

            r.hset('CARDS_JSON', core.sanitize_cardname(cardname), json.dumps(conts)) 
            r.hset('CARDS_JSON', core.sanitize_cardname(cardname.replace('/', ' // ')), json.dumps(conts)) 
            r.hset('CARDS_JSON', core.sanitize_cardname(cardname.replace('/', ' / ')), json.dumps(conts)) 

        else:
            cardname = core.sanitize_cardname(conts['name']).lower()

            r.hset('CARDS_JSON', core.sanitize_cardname(cardname), json.dumps(conts))      

        writecount += 1

    logging.debug('We just wrote ' + str(writecount) + ' card entries into Redis.')

load_cards_from_json('AllCards.json')

#for deck in open('decks_sample.json').readlines():
#    core.add_deck(json.loads(deck))

#for cc in [ core.sanitize_cardname(c) for c in open('banlist.txt').read().strip().split('\n') ]:
#    core.get_redis().sadd('BANNED', cc)
