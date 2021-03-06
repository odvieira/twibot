#!/usr/bin/env python3
from selenium import webdriver as wd
from bs4 import BeautifulSoup as bs
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import errno
import sys
import csv


class Source_Adress(object):
    def __init__(self, name: str, uri: str, user_id: int):
        self.name = name
        self.uri = uri
        self.user_id = int(user_id)
        return


class Tweet(object):
    def __init__(self, tweet_id: int, user_id: int, text=None, username=None, user_screen_name=None, date=0, retweets=0, likes=0, replies=0):
        self.tweet_id = int(tweet_id)
        self.text = text
        self.username = username
        self.user_screen_name = user_screen_name
        self.user_id = int(user_id)
        self.date = int(date)
        self.retweets = int(retweets)
        self.likes = int(likes)
        self.replies = int(replies)

        self.dictionary = dict(
            tweet_id=self.tweet_id, user_id=self.user_id,
            text=self.text, user_screen_name=self.user_screen_name,
            username=self.username, date=self.date,
            retweets=self.retweets, likes=self.likes,
            replies=self.replies)
        return


class Twibot(wd.Chrome):
    def __init__(self, username, password):
        super().__init__()

        self.user_id = 0
        self.username = username
        self.password = password
        self.parsed_users_history = list()
        self.parsed_users_season = list()
        self.sources = list()
        self.following = list()

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

        # Load users already parsed
        if os.path.exists('./data/hist/parsed_users_history.csv'):
            with open('./data/hist/parsed_users_history.csv', 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.parsed_users_history.append(int(row['user_id']))

        self.parsed_users_history.sort()

        element = WebDriverWait(self, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'Avatar'))
        )

        self.user_id = int(element.get_attribute('data-user-id'))

        self.add_source(self.username,
                        'https://twitter.com/%s' % self.username, self.user_id)
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
                    user_id = int(user_details_div['data-user-id'])

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

                tweets.append(
                    Tweet(tweet_id=tweet_id, user_id=user_id, text=text,
                          username=username, user_screen_name=user_screen_name,
                          date=created_at, replies=replies, likes=likes,
                          retweets=retweets))

        return tweets

    def binary_search(self, alist: list, item: int):
        first = 0
        last = len(alist)-1

        while first <= last:
            midpoint = (first + last)//2
            if alist[midpoint] == item:
                return True
            else:
                if item < alist[midpoint]:
                    last = midpoint-1
                else:
                    first = midpoint+1

        return False

    def add_source(self, name: str, uri: str, user_id: int):
        if self.binary_search(self.parsed_users_history, int(user_id)):
            return
        if self.binary_search(self.parsed_users_season, int(user_id)):
            return
        else:
            for i in self.sources:
                if user_id == i.user_id:
                    return

        self.sources.append(Source_Adress(name, uri, user_id))

        return

    def add_following(self, name: str, uri: str, user_id: int):
        for i in self.following:
            if user_id == i.user_id:
                return

        self.following.append(Source_Adress(name, uri, user_id))

        return

    def crawl_sources(self, crawl_limit: int=-1):
        for src in self.sources:
            if crawl_limit == 0:
                break

            self.get('%s/with_replies' % src.uri)
            self.scroll_down(5)

            tweets = self.parse_tweets()

            self.save_tweets_as_csv(src, tweets)
            self.parsed_users_season.append(int(src.user_id))

            crawl_limit -= 1

        self.parsed_users_season.sort()
        self.save_profile()
        return

    def crawl_for_sources_in_following(self, username_tag: str = None):
        if username_tag is None:
            username_tag = self.username

        self.get('https://twitter.com/%s/following' % username_tag)
        self.scroll_down(5)

        page = bs(self.page_source, 'lxml')

        for grid in page.find_all("div", class_="Grid"):
            for cell in grid.find_all("div", class_="Grid-cell"):
                elem = cell.find("div", class_="ProfileCard")
                if elem is not None:
                    uname = elem['data-screen-name']
                    user_id = elem['data-user-id']
                    self.add_source(
                        uname, 'https://twitter.com/%s' % uname, int(user_id))
                    self.add_following(
                        uname, 'https://twitter.com/%s' % uname, int(user_id))

        self.save_following()
        return

    def scroll_down(self, scrolls: int = -1):
        last_height = 0
        new_height = self.execute_script("return document.body.scrollHeight")

        while last_height < new_height and scrolls != 0:
            last_height = new_height

            driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);")

            time.sleep(2)

            new_height = driver.execute_script(
                "return document.body.scrollHeight")

            scrolls -= 1
        return

    def create_dir_to_save(self, dir_location: str):
        try:
            if not os.path.exists(dir_location):
                os.makedirs(dir_location)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    def save_following(self):
        dir_location = './data/collected/%s/%s' % (self.user_id, self.username)
        self.create_dir_to_save(dir_location)

        with open(
            '%s/%s_following.csv' % (dir_location, self.username),
                'w+') as following:

            following.write('"%s","%s","%s"\n' %
                            ('username', 'uri', 'user_id'))

            for i in self.following:
                following.write(
                    '"%s","%s","%i"\n' % (i.name, i.uri, i.user_id))

    def save_profile(self):
        hist = './data/hist'
        self.create_dir_to_save(hist)

        with open(
                "%s/parsed_users_history.csv" % hist, 'a') as parsed:

            if os.stat("./data/hist/parsed_users_history.csv").st_size == 0:
                parsed.write('"%s","%s","%s"\n' %
                             ('username', 'uri', 'user_id'))

            for i in self.sources:
                if self.binary_search(
                        self.parsed_users_season, i.user_id):
                    parsed.write(
                        '"%s","%s","%i"\n' % (i.name, i.uri, i.user_id))
        return

    def save_tweets_as_csv(self, src: Source_Adress, tweets: list()):
        dir_location = './data/collected/%s/%s' % (src.user_id, src.name)

        self.create_dir_to_save(dir_location)

        with open('%s/%s_data_base.csv' % (dir_location, src.name), 'w+') as db_file:

            writer = csv.DictWriter(
                db_file, ['tweet_id', 'user_id', 'text',
                          'user_screen_name', 'username', 'date',
                          'retweets', 'likes', 'replies'])

            writer.writeheader()

            for tweet in tweets:
                writer.writerow(tweet.dictionary)

        return


if __name__ == "__main__":
    with open('key', 'r') as key:
        cred = list()
        for line in key:
            cred.append(line[:-1])

    assert sys.path[0] is not None

    os.chdir(sys.path[0])

    driver = Twibot(cred[0], cred[1])

    del(cred)

    driver.crawl_for_sources_in_following()

    driver.crawl_sources()

    driver.close()
