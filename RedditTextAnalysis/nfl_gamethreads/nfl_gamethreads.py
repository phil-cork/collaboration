import pandas as pd
import numpy as np
import praw
from bs4 import BeautifulSoup


def get_comments(reddit=praw.Reddit, submission_id=''):
    '''
    Returns a list of comments from the specified reddit thread associated with the submission_id parameter.
    The list includes the comment's author, content, upvotes, downvotes, created time, and author's flair.

    Parameters
    --- --- --- 
    reddit: praw.Reddit instance
        The pre-created reddit instance set up by user. Only read rights required.

    submission_id: string
        The unique id associated with the reddit thread of interest. Gain by accessed by the reddit API or extracted from the thread's permalink.
    '''

    # create a praw.Submission object based on the subject_id to access comments
    submission = reddit.submission(submission_id)
    
    # ignore all of the "Load More Comment" prompts to return entire comment tree
    submission.comments.replace_more(limit=None)

    # store variables of interest in a list and return it
    comments_list = [(submission_id, (str(comment.author), str(comment.body), int(comment.ups), int(comment.downs), comment.created_utc, str(comment.author_flair_text))) for comment in submission.comments.list()]

    return comments_list


def get_game_data(reddit=praw.Reddit, submission_id=''):
    '''
    Returns a tuple of the submission_id, home team, home team score, away team, away team score, winner, 
    combined score, difference in final score, predicted winner, predicted difference, and predicted over/under, and the record of the teams prior to the game.

    Parameters
    --- --- --- 
    reddit: praw.Reddit instance
        The pre-created reddit instance set up by user. Only read rights required.

    submission_id: string
        The unique id associated with the reddit thread of interest. Gain by accessed by the reddit API or extracted from the thread's permalink.
    '''

    submission = reddit.submission(submission_id)
    
    soup = BeautifulSoup(submission.selftext_html, 'html.parser')

    #hometeam and score
    home_team = soup('tr')[2]('td')[0].text
    home_score = int(soup('tr')[2]('td')[-1].text)
    #awayteam and score
    away_team = soup('tr')[3]('td')[0].text
    away_score = int(soup('tr')[3]('td')[-1].text)
    #combined
    combined_score = home_score + away_score
    diff = max(home_score, away_score) - min(home_score, away_score)
    if max(home_score, away_score) == home_score:
        winner = home_team
    else:
        winner = away_team

    odds = str(soup('tr')[6]('td')[-1].text)
    odds_list = odds.split()
    odds_length = len(odds_list)

    # odds_list is length 5 if team city is two words, 4 otherwise
    if odds_length == 5:
        pred_winner = odds_list[0] + " " + odds_list[1]
        pred_diff = odds_list[2][1:]
        pred_ou = odds_list[4]   
    if odds_length == 4:
        pred_winner = odds_list[0]
        pred_diff = odds_list[1][1:]
        pred_ou = odds_list[3]



    # drop "Game Thread: "
    title = submission.title[13:]

    # split into two teams and their records
    text_list = title.split(" at ")
 

    # find the wins and losses by searching for text on each side of the parantheses and dash
    away_team_wins = int(text_list[0][text_list[0].find(start:='(')+len(start):text_list[0].find('-')])
    away_team_losses = int(text_list[0][text_list[0].find(start:='-')+len(start):text_list[0].find(')')])
    away_record = " (" + str(away_team_wins) + "-" + str(away_team_losses) + ")"
    away_team_full = text_list[0].replace(away_record, "")
    # find the wins and losses by searching for text on each side of the parantheses and dash
    home_team_wins = int(text_list[1][text_list[1].find(start:='(')+len(start):text_list[1].find('-')])
    home_team_losses = int(text_list[1][text_list[1].find(start:='-')+len(start):text_list[1].find(')')])
    home_record = " (" + str(home_team_wins) + "-" + str(home_team_losses) + ")"
    home_team_full = text_list[1].replace(home_record, "")


    gamethread_data = (submission_id, title, home_team_full, home_team_wins, home_team_losses,  
                       away_team_full, away_team_wins, away_team_losses, 
                       home_score, away_score, winner, combined_score, diff, pred_winner, pred_diff, pred_ou)

    return gamethread_data
