from multiprocessing import Process, Manager
from datetime import datetime
from bs4 import BeautifulSoup
import argparse
import requests
import json
import re
import sys
sys.setrecursionlimit(90000)

SITE_URL = 'https://old.reddit.com/'
REQUEST_AGENT = 'Mozilla/5.0 Chrome/47.0.2526.106 Safari/537.36'

def createSoup(url):
    return BeautifulSoup(requests.get(url, headers={'User-Agent':REQUEST_AGENT}).text, 'lxml')

def getSearchResults(searchUrl):
    posts = []
    while True:
        resultPage = createSoup(searchUrl)
        posts += resultPage.findAll('div', {'class':'search-result-link'})
        footer = resultPage.findAll('a', {'rel':'nofollow next'})
        if footer:
            searchUrl = footer[-1]['href']
        else:
            return posts

def getFlair(source):
    flairline = source.find('span',{'class':'flair'})
    flair = '<no flair>' if flairline == None else flairline.text
    return flair    

def parseComments(commentsUrl):
    commentTree = {}
    commentsPage = createSoup(commentsUrl)
    commentsDiv = commentsPage.find('div', {'class':'sitetable nestedlisting'})
    comments = commentsDiv.findAll('div', {'data-type':'comment'})
    for comment in comments:
        tagline = comment.find('p', {'class':'tagline'})
        author = tagline.find('a', {'class':'author'})
        author = "[deleted]" if author == None else author.text
        flair = getFlair(tagline)
        date = tagline.find('time')['datetime']
        date = datetime.strptime(date[:19], '%Y-%m-%dT%H:%M:%S')
        commentId = comment.find('p', {'class':'parent'}).find('a')['name']
        score = comment.find('span', {'class':'score unvoted'})
        score = 0 if score == None else int(re.match(r'[+-]?\d+', score.text).group(0))
        print(commentId, 'date:', date, 'author:', author, 'flair:', flair, 'score:', score)
        commentTree[commentId] = {'author':author, 'flair':flair, 'score':score, 'date':str(date)}
    return commentTree

def parsePost(post, results):
    time = post.find('time')['datetime']
    date = datetime.strptime(time[:19], '%Y-%m-%dT%H:%M:%S')
    title = post.find('a', {'class':'search-title'}).text
    score = post.find('span', {'class':'search-score'}).text
    score = int(re.match(r'[+-]?\d+', score).group(0))
    author = post.find('a', {'class':'author'}).text
    flair = getFlair(post)
    subreddit = post.find('a', {'class':'search-subreddit-link'}).text
    commentsTag = post.find('a', {'class':'search-comments'})
    url = commentsTag['href']
    numComments = int(re.match(r'\d+', commentsTag.text).group(0))
    print("\n" + str(date)[:19] + ":", numComments, score, author, subreddit, title)
    commentTree = {} if numComments == 0 else parseComments(url)
    results.append({'title':title, 'url':url, 'date':str(date), 'score':score,
                    'author':author, 'flair':flair, 'subreddit':subreddit, 'comments':commentTree})

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--subreddit', type=str, help='optional subreddit restriction')
    parser.add_argument('--date', type=str, help='optional date restriction (day, week, month or year)')
    args = parser.parse_args()
	    
    if args.subreddit == None:
        print('Please specify subreddit with flag --subreddit "x". Exiting.')
        sys.exit()
    else:    
        searchUrl = SITE_URL + 'r/' + args.subreddit

    if args.date == 'day' or args.date == 'week' or args.date == 'month' or args.date == 'year':
        searchUrl += '&t=' + args.date
    elif args.date != None:
        print('WARNING: Invalid date restriction parameter. Proceeding without any restrictions.')
        
    print('Search URL:', searchUrl)
    posts = getSearchResults(searchUrl)
    print('Started scraping', len(posts), 'posts.')
    
    results = Manager().list()
    jobs = []
    for post in posts:
        job = Process(target=parsePost, args=(post, results))
        jobs.append(job)
        job.start()
    for job in jobs:
        job.join()