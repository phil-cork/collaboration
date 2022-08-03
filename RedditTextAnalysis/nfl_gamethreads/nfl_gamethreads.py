from operator import index
from statistics import stdev
import pandas as pd
import numpy as np
import praw
from bs4 import BeautifulSoup
from textblob import TextBlob
import datetime



### DATA COLLECTION FUNCTION ###

def get_submissions(redditor, sub_limit:int) -> list:
    # initialize a new list for storing gamethread data
    submission_list = []

    # for each gamethread, store the id, name, and date
    for submission in redditor.submissions.new(limit=sub_limit):
        submission_list.append((str(submission.id), str(submission.title), submission.created_utc))

    return submission_list



### MAIN GAMETHREAD FUNCTION ###

def build_gamethread_df(reddit:praw.Reddit, submission_list:list):
    
    gamethread_df = pd.DataFrame(submission_list, columns=['id','title','date'])

    # transform the date column from UTC timestamp to only the date
    gamethread_df['date'] = gamethread_df['date'].apply(lambda utc_entry: datetime.datetime.utcfromtimestamp(utc_entry))
    gamethread_df['date'] = gamethread_df['date'].dt.date

    # remove pre and post game threads, the superbowl halftime discussion, and the pro bowl discussion
    gamethread_df = gamethread_df[gamethread_df["title"].str.contains("Pre|Post|Halftime|Pro Bowl|Super Bowl|RedZone")==False].copy()
    gamethread_df.reset_index(inplace=True, drop=True)

    # append column for which NFL Week each game's date falls into
    gamethread_df = add_nfl_weeks(gamethread_df)

    # use text from the gamethread's content to get game-level details like teams and score
    gamedata = [scrape_game_data(reddit, each_id) for each_id in gamethread_df['id']]
    gamedata_df = pd.DataFrame(gamedata, columns=['id', 'home_team_full', 'home_team_wins', 'home_team_losses', 'home_team_ties', 
                       'away_team_full', 'away_team_wins', 'away_team_losses', 'away_team_ties',
                       'home_score', 'away_score', 'winner', 'combined_score', 'diff', 'pred_winner', 'pred_diff', 'pred_ou'])
    
    gamethread_df = gamethread_df.merge(gamedata_df, on='id')

    return gamethread_df



### GAMETHREAD HELPER FUNCTIONS ### 


def add_nfl_weeks(gamethread_df:pd.DataFrame):
    '''
    Takes in a DataFrame that includes at a minimum a "date" and appends the NFL Week based on the date provided.
    '''
    nfl_weeks = pd.read_csv('nfl_week_dates.csv', index_col='week')
    week_list = [i+1 for i in range(18)]

    all_gamethreads_df = pd.DataFrame(columns=gamethread_df.columns)
    all_gamethreads_df['week'] = 0

    for week in week_list:
        start = nfl_weeks.loc[week].at['week_start']
        end = nfl_weeks.loc[week].at['week_end']

        start_y = int(start[0:4])
        start_m = int(start[5:7])
        start_d = int(start[8:10])

        end_y = int(end[0:4])
        end_m = int(end[5:7])
        end_d = int(end[8:10])

        # store as date and use dates to query the dataframe provided
        start_date = datetime.date(start_y, start_m, start_d)
        end_date = datetime.date(end_y, end_m, end_d)

        gamethread_df_week = gamethread_df.query("date >= @start_date and date <= @end_date").copy()
        gamethread_df_week['week'] = week

        all_gamethreads_df= all_gamethreads_df.append(gamethread_df_week, ignore_index=True)

    return all_gamethreads_df


def scrape_game_data(reddit: praw.Reddit, submission_id: str):
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
    
    # split text on each team for record and full name
    away_team_wins, away_team_losses, away_team_ties, away_team_full = get_team_record(text_list[0])
    home_team_wins, home_team_losses, home_team_ties, home_team_full = get_team_record(text_list[1])
    
    # collect all and return
    gamethread_data = (submission_id, home_team_full, home_team_wins, home_team_losses, home_team_ties, 
                       away_team_full, away_team_wins, away_team_losses, away_team_ties,
                       home_score, away_score, winner, combined_score, diff, pred_winner, pred_diff, pred_ou)

    return gamethread_data



def get_team_record(team_string: str):
    '''
    A helper function that takes in the gamethread title split for the home and away team
    Returns each component of the team's record and their full name
    '''

    # split the name and record, then remove the parantheses
    team_list = team_string.split("(")
    record_list = team_list[1][:-1].split("-")

    wins = record_list[0]
    losses = record_list[1]
    if len(record_list) == 3:
        ties = record_list[2]
    else:
        ties = 0

    # store the name minus trailing whitespace
    team_full = team_list[0][:-1]

    return wins, losses, ties, team_full



### COMMENT FUNCTIONS ### 


def get_comments(reddit: praw.Reddit, submission_id: str, comments_only:bool):
    '''
    If comments_only = True, returns a list of only the comment body text for downstream text analysis
    If comments_only = False, the returned list is a list of tuples that includes the comment's author, content, upvotes, downvotes, created time, and author's flair.
    
    Parameters
    --- --- --- 
    reddit: praw.Reddit instance
        The pre-created reddit instance set up by user. Only read rights required.

    submission_id: string
        The unique id associated with the reddit thread of interest. Gain by accessed by the reddit API or extracted from the thread's permalink.

    comments_onlt: bool
        Determines the contents of the list to be returned, either only the comment body text or additional details
    '''

    # create a praw.Submission object based on the subject_id to access comments
    submission = reddit.submission(submission_id)
    
    # ignore all of the "Load More Comment" prompts to return entire comment tree
    submission.comments.replace_more(limit=None)

    if comments_only == False: # store variables of interest with comments in list of tuples
        comments_list = [(submission_id, str(comment.author), str(comment.body), int(comment.ups), comment.created_utc, str(comment.author_flair_text)) for comment in submission.comments.list()]

    else: # return only list of comments
        comments_list = [str(comment.body) for comment in submission.comments.list()]

    return comments_list


def analyze_text(text_df: pd.DataFrame, text_column: str):
    '''
    Takes in a dataframe with a 'column of text and returns the dataframe with two new appended columns that include the
    polatirty and subjectivity of each value of text from the Textblob package.

    Intended for use on dataframe of comments for analysis at the level of a single corpus.
    For aggregating text into a single set of statistics, see analyze_submission().

    Parameters
    --- --- ---
    text_df: pandas DataFrame
        Dataframe with at a minimum, a column of text to be analyzed

    text_column: str
        Name of the column in which text to be analyzed is stored
    '''
    text_df["polarity"] =  [TextBlob(each).sentiment.polarity for each in text_df[text_column]]
    text_df["subjectivity"] = [TextBlob(each).sentiment.subjectivity for each in text_df[text_column]]

    return text_df

