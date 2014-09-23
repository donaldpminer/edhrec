import logging
import core
import urllib2
import datetime
import re
import HTMLParser

# This file contains the scraper code for tappedout.net
# Note that there is no official api for tappedout and this is straight up scraping HTML...
#           it may get ugly. hold on.

# Hypothetically if we want to add another source than tappedout, all that is used by reddit.py
#  is URL_PATTERN and get_deck. So, future scraper modules should expose these methods and then
#  we'll add them to some sort of list in reddit.py.

URL_PATTERN = re.compile('.*(http://tappedout.net/mtg-decks/[a-z0-9-]+).*')

# Given a tappedout URL, get me the tuple:
#    (commander, deck contents (cards), color identity, the date the deck was updated)
def get_deck(url):
    try:
        # I tack on /?fmt=txt because it gives th list of cards in a somewhat nice
        #   text format. If only there was an API...
        con = core.urlopen(url.rstrip('/') + '/?fmt=txt')
    except urllib2.HTTPError as e:
        # This will happen on 404 or any other error.
        logging.warning("Someone posted a bad URL: " + url + " (%s)" % str(e))
        return None

    deck = set()

    # For each line in the content of the web page....
    for line in con.splitlines():
        line = line.strip()
        if len(line) == 0:
            continue

        if not line[0] in '0123456789':
            continue

        # At this point, the line is not empty and the line starts with a number
        # This, we know, is a card

        # The line is tab delimited like this: "1\tAustere Command\n"
        card = line.split('\t')[1]

        try:
            deck.add(core.sanitize_cardname(card))
        except KeyError:
            pass
        except  ValueError as e:
            logging.warning("Ignored this card because of some sort of bad value")
        

    # Call out to get_tappedout_info to grab the deck info
    cmdr, colors, date = get_tappedout_info(url)

    # if they didn't post the commander, i'm going to try to figure out who it is
    if cmdr is None:
        for card in deck:
            cd = core.lookup_card(card)

            if not cd.has_key('supertypes'):
                continue

            if 'Legendary' in cd['supertypes'] and sorted(list(core.color_identity(card))) == sorted(list(colors)):
                # ok, we've got a legenadry with the colors i think the deck should be. i'll just stop here. 
                cmdr = card
                break
        else:
            logging.warn("there was no legendary creature here.... and none was specified... something f'd up is going on")
            cmdr = 'jedit ojanen'    

    deck.add(cmdr)

    out_deck = { 'commander' : cmdr, 'cards' : sorted(list(deck)), 'date' : date }

    return out_deck

def get_tappedout_info(url, assume_now = True):

    con = core.urlopen(url).splitlines()

    # GET COMMANDER
    cmdr = None
    for line in con:
        # First, we need to find the commander we're talking about here.
        if line.strip().startswith('<a href="/mtg-card/'):
            cmdr_url = 'http://tappedout.net' + line.split('"')[1]

            # Unfortunately, it's not easy to grab the name from the commander immage
            # We have to go deeper... (the commander's specific page)
            ccon = core.urlopen(cmdr_url).splitlines()

            # Look for the title because that contains the commander name
            for cline in ccon:
                if "<title>" in cline:
                    cmdr = core.sanitize_cardname(cline.split('>')[1].split('(')[0])
                    break

            break
    
    # GET COLORS
    # GET COLORS from the pie on the right
    colors = set([])         
    for line in con:
        if line.strip().startswith('buildColorChart'):
            if 'Green' in line: colors.add('GREEN')
            if 'Red'   in line: colors.add('RED')
            if 'Blue'  in line: colors.add('BLUE')
            if 'Black' in line: colors.add('BLACK')
            if 'White' in line: colors.add('WHITE')

            break

    colors = sorted(list(colors))

    # override pie colors if we have a good commander
    if cmdr is not None:
        try:
            colors = core.color_identity(cmdr)
        except ValueError:
            logging.warn('I have a commander that I don\'t think should exist')
            cmdr = None
            # this will happen if the commander is one that tappedout sees but is not in allcards.json (i.e. if it is new)
            pass

    # GET DATE
    if assume_now: 
        date = datetime.datetime.now().toordinal()  # Note: we use ordinal dates to represent the day.
    else:
        # Go fetch the time. Tappedout makes it hard because they say "3 days ago" or "2 years ago"
        #  and it's got so many options. So, this scraping is pretty fickle but seems to work fine.
        for line in con:
            line = line.lower()
            if '<td>' in line and len(line) < 21 and ('day' in line or 'hour' in line or 'month' in line or 'year' in line):
                num, unit = line.strip()[4:].split('<')[0].split()
                num = int(num)
                unit = unit.strip('s')

                now = datetime.datetime.now().toordinal()

                if unit == 'hour':
                    date = now
                elif unit == 'day':
                    date = now - num
                elif unit == 'month':
                    date = int(now - num * (365. / 12.))
                elif unit == 'year':
                    date = now - num * 365

                break
        else:
            date = now
    
    return cmdr, colors, date
