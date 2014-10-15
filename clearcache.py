

import core


r = core.get_redis()

c = 0
for k in r.keys('CACHE_*'):
    print 'DEL %s' % k
    c += 1
    r.delete(k)

print 'deleted', c, 'keys.'

