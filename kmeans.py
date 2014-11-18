import numpy
import core
import sklearn.cluster
import deckstats
import random

def kmeans(cmdr, k=4):

    random.seed(52485)

    cmdr = core.sanitize_cardname(cmdr)

    card_to_idx = {}
    idx_to_card = {}
    dims = None

    decks = []

    i = 0
    for deck in core.get_all_decks():
        if deck['commander'] != cmdr:
            continue

        for card in deck['cards']:
            if card in ['island', 'swamp', 'mountain', 'forest', 'plains', cmdr]:
                continue

            lo = core.lookup_card(card)
            if lo is None or 'Land' in lo['types']: continue

            if card_to_idx.has_key(card): continue
           
            card_to_idx[card] = i
            idx_to_card[i] = card
            i += 1

        ll = numpy.zeros(i, dtype=int)

        idxs = []
        for card in deck['cards']:
            try:
                idxs.append(card_to_idx[card])
            except KeyError:
                continue

        for idx in idxs:
            ll[idx] = 1

        decks.append(ll)

    for idx, deck in enumerate(decks):
        decks[idx].resize(i, refcheck=False)

    decks = numpy.array(decks, dtype=int)

    kmc = sklearn.cluster.KMeans(n_clusters=k, init='k-means++', n_init=25, max_iter=300, tol=0.000001, precompute_distances=True, verbose=0, random_state=None, n_jobs=1)

    kmc.fit(decks)

    clusters = [ [] for i in range(k) ]

    out = []

    for idx, deck in enumerate(decks):
        clusters[kmc.labels_[idx]].append([idx_to_card[idx] for idx, v in enumerate(deck) if v == 1])

    for idx, cluster in enumerate(kmc.cluster_centers_):
        outc = {}

        sumdiff = sum([ cluster - other for other in kmc.cluster_centers_ ])
        defining = sorted( enumerate(sumdiff), key=lambda x: x[1], reverse=True)[:12]
        defining = [ {'score' : val, 'card_info' : {'name' : core.lookup_card(idx_to_card[jdx])['name'], \
                                                               'types' : core.lookup_card(idx_to_card[jdx])['types'], \
                                                               'colors' : core.lookup_card(idx_to_card[jdx]).get('colors', []), \
                                                               'cmc' : core.lookup_card(idx_to_card[jdx]).get('cmc', 0) } } for jdx, val in defining ]

        topc = sorted( [(val, idx_to_card[jdx] ) for jdx, val in enumerate(cluster)], reverse=True)[:125]
        topc = [ {'score' : val, 'card_info' : {'name' : core.lookup_card(card)['name'], \
                                                               'types' : core.lookup_card(card)['types'], \
                                                               'colors' : core.lookup_card(card).get('colors', []), \
                                                               'cmc' : core.lookup_card(card).get('cmc', 0) } } for val, card in topc ]

        outc['defining'] = defining
        outc['recs'] = topc

        outc['numdecks'] = len(clusters[idx])
        outc['percentdecks'] = int( len(clusters[idx]) / float(len(decks)) * 100 )
        outc['commander'] = cmdr
        outc['stats'] = deckstats.tally([ {'cards' : d } for d in clusters[idx] ])
        out.append(outc)

    return sorted(out, key=lambda x: x['percentdecks'], reverse=True)




