import core
import json

r=core.get_redis()

strs = r.keys('DECKS_*')


for s in strs:
    ds = core.get_decks(s, dedup=True)
    dds = core.dedup_decks(ds)

    r.delete('DDD_' + s)
    for deck in dds:
        r.rpush('DDD_' + s, json.dumps(deck))

    r.delete('OLD_' + s)
    r.rename(s, 'OLD_' + s)
    r.rename('DDD_' + s, s)


    print 'Removed %d decks (%d - %d)' % (r.llen('OLD_' + s) - r.llen(s), r.llen('OLD_' + s), r.llen(s))
