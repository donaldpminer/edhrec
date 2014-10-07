import core
import tappedout
import praw
import logging
import time
import traceback
import datetime

TESTING = False

PRAW = praw.Reddit(user_agent=core.USER_AGENT)
PRAW.login(*open('login.txt').read().strip().split())

BOT_NOTICE = """
\n\nI'm a bot - visit me in /r/edhrec or [edhrec.com](http://edhrec.com)"""



# The universal easy sleep command
def sleep(t=5.0, x=1.0):
    time.sleep(t * x)

# Given a submission, try to find the tappedout.net URL.
# If there is one, return it. Otherwise, return None.
def find_tappedout_url(submission):
    op_text = submission.selftext.lower().replace('\n', ' ').strip()

    url = tappedout.URL_PATTERN.match(op_text)

    if url is None:
        url = tappedout.URL_PATTERN.match(submission.url)

    if url is None:
        return None
    else:
        return str(url.group(1))

def linkify(cn):
    return '[%s](http://gatherer.wizards.com/Handlers/Image.ashx?name=%s&type=card&.jpg)' % (core.cap_cardname(cn), cn)

# Go through recent submissions and try to find something I haven't seen before.
# If there is something, post the recommendations. This is the default behavior
#    that edhrec does to respond to posts.
def seek_submissions(sublimit=200):
    logging.debug('STARTING SUBMISSION SEEK AT ' + str(datetime.datetime.now()))

    # Scan edh and edhrec
    subreddit = PRAW.get_subreddit('edhrec+edh').get_new(limit=sublimit)

    rds = core.get_redis()

    # For each submission in newness order...
    for submission in subreddit:
        # Check to see if I've scanned this already. If so, pass on it.
        if not TESTING:
            if rds.sismember('SEEN', submission.id):
                continue
        logging.debug("Scanning " + str(submission.id) + " - " + str(submission.title.encode('utf-8')))
 
        # Fetch the tappedout url
        url = find_tappedout_url(submission)

        # If there was no tappedout URL, then let's pass over this one.
        if url is None:
            rds.sadd('SEEN', submission.id)
            continue

        ## At this point, we have a deck we'e never seen before that has been posted!
        #
        #       ~*~ GET EXCITED ~*~

        logging.debug("I found a URL to scrape: " + str(url))

        # Scrape it
        deck = tappedout.get_deck(url)

        if deck is None:
            logging.warning('Skipping this URL because something went wrong. (' + submission.title.encode('utf-8') +')')
            rds.sadd('SEEN', submission.id)
            continue            

        # Go get the recommendations
        newrecs, outrecs = core.recommend(deck)

        lands = []
        creatures =[]
        noncreatures = []

        for card, score in newrecs:
            # filter out basic lands from being recommendations
            if card in ['swamp', 'island', 'plains', 'mountain', 'forest']:
                continue # there is an annoying thing that happens when people use snow-covered basics
                     # where edhrec will post basic lands as a recommendation. this prevents that

            if score < .3:
                continue

            score = int(score * 100) # make score easier to read

            try:
                types = core.lookup_card(card)['types']
            except:
                logging.warn('something went wong with the card %s, ignoring it' % card)
                continue

 
            if 'Creature' in types:
                creatures.append((card, score))
            elif 'Land' in types:
                lands.append((card, score))
            else:
                noncreatures.append((card, score))

        # build the output string
        if str(submission.subreddit).lower() in ['edhrec', 'edh']:
            out_str = ['Other decks like yours use:\n\nCreatures | Non-creatures | Lands | Unique in your deck\n:--------|:---------|:---------|:--------']

            for i in range(16):
                try:
                    c = '[%d] %s ' % (creatures[i][1], linkify(creatures[i][0]))
                except IndexError:
                    c = ' '

                try:
                    n = '[%d] %s ' % (noncreatures[i][1], linkify(noncreatures[i][0]))
                except IndexError:
                    n = ' '

                try:
                    l = '[%d] %s ' % (lands[i][1], linkify(lands[i][0]))
                except IndexError:
                    l = ' '

                try:
                    u = '%s ' % linkify(outrecs[i][0])
                except IndexError:
                    u = ' '

                if len(c + n + l) == 3:
                    break

                out_str.append('%s | %s | %s | %s' % (c, n , l, u))

            out_str.append('\n\n[This deck on edhrec.com](http://edhrec.com/#/recommendations?q=' + url + ')')

            out_str.append(BOT_NOTICE)

        elif str(submission.subreddit).lower() == 'edh':
            pass

        elif str(submission.subreddit).lower() == 'competetiveedh':
            pass

        # Post the comment!
        if not TESTING:
            submission.add_comment('\n'.join(out_str))

        logging.debug('comment i think I posted:\n' + '\n'.join(out_str))

        logging.debug("I posted a comment with recommendations!")

        deck['ref'] = 'reddit bot'
        deck['url'] = url
        deck['scrapedate'] = str(datetime.datetime.now())

        # Keep track of the fact that I've now processed this deck.
        # It is important that this is last in case the scraping fails and
        #   the problem is later fixed.
        if not TESTING:
            rds.sadd('SEEN', submission.id)
            core.add_deck(deck)

        sleep()

    logging.debug('DONE WITH SUBMISSION SEEK AT ' + str(datetime.datetime.now()))


if __name__ == '__main__':
    while True:
        try:
            # Go find submissions
            seek_submissions()
        except Exception as e:
            logging.warning("Got an unhandled exception! " + str(e))
            logging.warning("traceback:" + str(traceback.format_exc()))

        core.flush_cache()

        # Sleep for a minute. A minute is because your requests/minute seem
        #   to reset every minute for Reddit.
        # edh and edhrec subreddits don't have that much traffic, so no big deal
        #   if someone has to wait at most a minute to get a response.
        sleep(t=30.0)
