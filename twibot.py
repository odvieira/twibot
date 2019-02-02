#!/usr/bin/env python3
from selenium import webdriver as wd
from bs4 import BeautifulSoup as bs
import time, os, errno

class Tweet(object):
    def __init__(self, id, text=None, username=None, user_screen_name=None, date=0, retweets=0, likes=0, replies=0):
        self.id = int(id)
        self.text = text
        self.username = username
        self.user_screen_name = user_screen_name
        self.date = int(date)
        self.retweets = int(retweets)
        self.likes = int(likes)
        self.replies = int(replies)
        return

class Source_Adress(object):
    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path
        return

class Twibot(wd.Chrome):
    def __init__(self, username, password):
        super().__init__()
        self.implicitly_wait(1)

        self.username = username
        self.password = password

        # open the web page in the browser:
        self.get("https://twitter.com/login")

        # find the boxes for username and password
        username_field = self.find_element_by_class_name("js-username-field")
        password_field = self.find_element_by_class_name("js-password-field")

        # enter your username:
        username_field.send_keys(username)

        # enter your password:
        password_field.send_keys(password)

        # click the "Log In" button:
        self.find_element_by_class_name("EdgeButtom--medium").click()
        return
            
    def close(self):
        super().close()
        return

    def parse_tweets(self):
        page = bs(self.page_source, 'lxml')
        tweets = list()
        
        for li in page.find_all("li", class_='js-stream-item'):

            # If our li doesn't have a tweet-id, we skip it as it's not going to be a tweet.
            if 'data-item-id' not in li.attrs:
                continue
            else:
                tweet_id = li['data-item-id']
                text = None
                user_screen_name = None 
                username = None
                created_at = 0
                retweets = 0
                likes = 0
                replies = 0

                # Tweet Text
                text_p = li.find("p", class_="tweet-text")
                if text_p is not None:
                    text = text_p.get_text()
                    
                # Tweet User ID, User Screen Name, User Name
                user_details_div = li.find("div", class_="tweet")
                if user_details_div is not None:
                    user_screen_name = user_details_div['data-screen-name']
                    username = user_details_div['data-name']

                # Tweet date
                date_span = li.find("span", class_="_timestamp")
                if date_span is not None:
                    created_at = int(date_span['data-time-ms'])

                # Tweet Retweets
                retweet_span = li.select(
                    "span.ProfileTweet-action--retweet > span.ProfileTweet-actionCount")
                if retweet_span is not None and len(retweet_span) > 0:
                    retweets = int(retweet_span[0]['data-tweet-stat-count'])

                # Tweet Likes
                like_span = li.select(
                    "span.ProfileTweet-action--favorite > span.ProfileTweet-actionCount")
                if like_span is not None and len(like_span) > 0:
                    likes = int(like_span[0]['data-tweet-stat-count'])

                # Tweet Replies
                reply_span = li.select(
                    "span.ProfileTweet-action--reply > span.ProfileTweet-actionCount")
                if reply_span is not None and len(reply_span) > 0:
                    replies = int(reply_span[0]['data-tweet-stat-count'])

                tweets.append(Tweet(id=tweet_id, text=text, username=username, user_screen_name=user_screen_name, date=created_at, replies=replies, likes=likes, retweets=retweets))

        return tweets

    sources = list()

    def add_source(self, name: str, path: str):
        for i in self.sources:
            if name == i.name:
                #print('Not allowed action in module Twibot[In function: Twibot.add_source]: Trying to add a source already added')
                return

        self.sources.append(Source_Adress(name, path))
            
        return

    def crawl(self):
        for src in self.sources:
            self.get(src.path)
            
            self.scroll_down(0)

            tweets = driver.parse_tweets()

            self.save_tweets_as_csv(src, tweets)

        return

    def crawl_for_sources_in_following(self):
        self.get('https://twitter.com/%s/following' % self.username)
        self.scroll_down()
        page = bs(self.page_source, 'lxml')

        for grid in page.find_all("div", class_="Grid"):
            for cell in grid.find_all("div", class_="Grid-cell"):
                elem = cell.find("div", class_="ProfileCard")
                if elem is not None:
                    uname = elem['data-screen-name']
                    try:
                        self.add_source(uname, 'https://twitter.com/%s' % uname)
                    except Error as e:
                        print(e.msg)
        return
        
    def scroll_down(self, scrolls: int = -1):
        last_height = 0
        new_height = self.execute_script("return document.body.scrollHeight")

        while last_height < new_height and scrolls != 0:
                last_height = new_height

                driver.execute_script(\
                    "window.scrollTo(0, document.body.scrollHeight);")

                time.sleep(2)

                new_height = driver.execute_script(
                    "return document.body.scrollHeight")

                scrolls -= 1
        return

    def save_tweets_as_csv(self, src: Source_Adress, tweets: list):
        dir = './data/collected/%s' % src.name

        try:
            if not os.path.exists(dir):
                os.makedirs(dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        with open('%s/%s_data_base.csv' % (dir, src.name), 'w+') as db_file:
            db_file.write('"%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s"\n' %
                        ('id', 'text', 'user_screen_name', 'username', 'date', 'retweets', 'likes', 'replies'))
            for tweet in tweets:
                db_file.write('"%i", "%s", "%s", "%s", "%i", "%i", "%i", "%i"\n' %
                            (tweet.id, tweet.text, tweet.user_screen_name, tweet.username, tweet.date, tweet.retweets, tweet.likes, tweet.replies))
        return

if __name__ == "__main__":
    with open('key', 'r') as key:
        cred = list()
        for line in key:
            cred.append(line[:-1])

    driver = Twibot(cred[0], cred[1])

    driver.crawl_for_sources_in_following()
    
    driver.crawl()
    
    driver.close()
