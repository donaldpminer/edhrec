
# go through AllCards.json and print out a list of all of the legendary creatures

import json
import core

for card, conts in json.load(open('AllCards.json')).items():
    if not conts.has_key(u'types'): continue
    if not conts.has_key(u'supertypes'): continue

    if u'Legendary' in conts[u'supertypes'] and u'Creature' in conts[u'types']:
        print card.encode('utf-8')


