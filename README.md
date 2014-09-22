EDHREC is a reddit bot that provides recommendations for edh decks.
It is built using Python. It uses PRAW to interact with Reddit.
It stores data in Redis.
It uses an approach called Collaborative Filtering to get the recommendations.

DISCLAIMER: THIS CODE WILL POST TO REDDIT LIVE. PLEASE DON'T SPAM PEOPLE UNLESS YOU KNOW WHAT YOU ARE DOING.

Original author: /u/orangeoctopus


Installation instructions
=========================

Check out the edhrec repository or download the source from https://github.com/donaldpminer/edhrec.git
You should see files like reddit.py, tappedout.py



Install the following dependencies used by the edhrec python program:

PRAW is the reddit API module
$ pip install praw   

The redis module... talks to redis
$ pip install redis



Get the latest stable release of redis, build it, then start it:
http://redis.io/download
Redis is an in-memory data store that edhrec uses
... or on some distributions you should be able to install the "redis-server" and "redis-cli" packages



Download AllCards.json from http://mtgjson.com/
$ curl http://mtgjson.com/json/AllCards.json > AllCards.json
Make sure you get AllCards.json not AllSets.json
Put this file in the same directory as reddit.py, core.py, etc.



If you are running for the first time, you'll need to run initialize.py
$ python initialize.py
DO NOT continue if you get any errors. Things to check if this doesn't work:
   - is redis running?
   - is banlist.txt there?
   - is AllCards.json good to go?




Notice there is a file called "decks_sample.json".
This is to show you how a deck is formatted by example. It's up to you go find deck data yourself...




Create your login information for a reddit account in a file called login.txt.
Put this on a single line, separated by a space. Username on the left, password on the right.
For example:
login.txt:
BotAccount524 hunter2



Make sure TESTING = True at the top of reddit.py or you are about to spam a bunch of people.
The TESTING flag makes it so edhrec runs in a mock manner and doesn't actually do anything,
but it will show you what he's doing in the logs.



Run the bot and hope for the best:
$ python reddit.py



Testing
======================================

Please please please please please do not run this bot in /r/edh unless everyone is cool with it.
We don't want a ton of bots spamming the subreddit. I'm always sensitive about this.

Go wild in /r/edhrec
You can change which subreddit your bot scans by changing this line
subreddit = PRAW.get_subreddit('edhrec+edh').get_new(limit=sublimit)







