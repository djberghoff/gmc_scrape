#import libraries
from bs4 import BeautifulSoup as bs
import requests
import pandas as pd
import numpy as np
from datetime import datetime

#functions

def get_school_directory(school_ids):
    school_directory = {}
    player_directory = {}
    for key in school_ids.keys():
        school_name = school_ids.get(key)
        url = 'http://gmcsports.com/bkteamstats.aspx?satc=270&year=2010&cmp=1&schoolid=%s' % key
        r = requests.get(url)
        data = r.text
        soup = bs(data, 'lxml')

        roster_table = soup.find('table', width="100%")
        names = roster_table.find_all('a')
        player_directory = {}
        for a in names:
            player_name = a['href'].split('=')[1]
            player_id = a.text
            player_directory.update({player_name: player_id})
            school_directory.update({school_name: player_directory})
    return school_directory

def get_player_directory(school_ids):
    player_directory = {}

    for key in school_ids.keys():
        school_name = school_ids.get(key)
        url = 'http://gmcsports.com/bkteamstats.aspx?satc=270&year=2010&cmp=1&schoolid=%s' % key
        r = requests.get(url)
        data = r.text
        soup = bs(data, 'lxml')

        roster_table = soup.find('table', width="100%")
        names = roster_table.find_all('a')
        for a in names:
            player_attr_list = []
            player_id = a['href'].split('=')[1]
            player_name = a.text
            player_attr_list.append(player_name)
            player_attr_list.append(school_name)
            player_directory.update({player_id: player_attr_list})
    return player_directory

def url_list(soup_input):
    url_list = []
    roster = soup_input.find(id='playerRosterInfo')
    names = roster.find_all('option')
    roster_ids = []
    for i in names:
        roster_ids.append( i.attrs.get('value'))
    for player in roster_ids:
        url_list.append('http://gmcsports.com/bkPlayerStats.aspx?player=%s'%player)
    return url_list

def player_dict(names):
    player_dict={}
    for name in names:
        player_dict.update({name.get('value'): name.text})
    return player_dict

def get_player_nm(url):
    player_id = url.split('=')[1]
    player_name = player_directory_output.get(player_id)[0]
    return player_name

def get_player_school(url):
    player_id = url.split('=')[1]
    player_school = player_directory_output.get(player_id)[1]
    return player_school

def get_columns(headers):
    columns_df = ['PlayerID','Player_Name','Player_Team']
    for tr in headers.find_all('th'):
        columns_df.append(tr.text)
    return columns_df

def get_table_ids(soup):
    table_ids = []
    for tr in soup.find_all('tr'):
        tr_id = tr.get('id')
        if tr_id != None:
            table_ids.append(tr_id)
    for i in table_ids:
        if 'SeasonTotals' in i:
            table_ids.remove(i)
    return table_ids

def game_stats(game_id,player_url,soup):
    game = soup.find(id=game_id)
    tds = game.find_all('td')
    player_nm_input = get_player_nm(player_url)
    player_id_index = player_url.split('=')[1]
    player_school = get_player_school(player_url)
    stats1 = [player_id_index,player_nm_input,player_school]
    for i in tds:
        stats1.append(i.text)
    return stats1


def get_season_stats_by_player(player_urls):
    for player in player_urls:
        r = requests.get(player)
        data = r.text
        soup = bs(data, 'lxml')
        table_ids = get_table_ids(soup)
        for game in table_ids:
            season_stats_out.append(game_stats(game,player,soup))
    return season_stats_out

def split_columns(df):
    fg = df['FG'].str.split('-',n=1,expand=True)
    fg3p = df['3P'].str.split('-',n=1,expand=True)
    ft = df['FT'].str.split('-',n=1,expand=True)
    result_split = df['RESULT'].str.split(' ',n=1,expand=True)
    df['RESULT'] = result_split[0]
    df['SCORE']= result_split[1]
    df['Court']=['Away' if '@' in x else 'Home' for x in df['OPP']]
    df['OPP']=df['OPP'].str.replace('@','')
    df['FGM']=fg[0]
    df['FGA']=fg[1]
    df['3PM']=fg3p[0]
    df['3PA']=fg3p[1]
    df['FTM']=ft[0]
    df['FTA']=ft[1]
    df.drop(['FG','3P','FT'],axis=1,inplace=True)
    df['MIN']=np.where(df['MIN']=='Did Not Play or No Stats Accumulated',0,df['MIN'])

def to_numeric(df,non_numeric):
    all_cols = [i for i in df.columns]
    numeric_cols = [i for i in all_cols if i not in non_numeric]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col])
        df[col].fillna(0, inplace=True)
        df[col] = df[col].astype('int64')

def edit_dates(df):
    df['DATE'] = pd.to_datetime(df['DATE'], format='%m/%d')
    df['month'] = pd.DatetimeIndex(df['DATE']).month
    df['day'] = pd.DatetimeIndex(df['DATE']).day
    df['year'] = np.where(df['month'] == 12, 2010, 2011)
    df['DATE'] = pd.to_datetime(df[['month', 'day', 'year']], format='%m/%d/%Y')
    df['gameID'] = df['year'].map(str) + df['month'].map(str).str.zfill(2) + df['day'].map(str).str.zfill(2)

def game_score_stats(df):
    df['GMSCORE'] = np.where(df['MIN'] == 0, 0,df['PTS'] + 0.4 * df['FGM'] - 0.7 * df['FGA'] - 0.4 * (df['FTA'] - df['FTM']) + 0.7 * df['OFF'] + 0.3 * df['DEF'] + df['STL'] + 0.7 * df['AST'] + 0.7 * df['BLK'] - 0.4 * df['PF'] - df['TO'])
    df['GS_RANK'] = df.groupby('DATE')['GMSCORE'].rank(ascending=False, method='min').astype('int64')

def player_averages(df):
    return df.groupby(['PlayerID','Player_Name','Player_Team'])['MIN','PTS','STL','BLK','AST','OFF','DEF','TOT','TO','PF','GMSCORE'].mean().round(decimals=1).reset_index()

def player_totals(df):
    return df.groupby(['PlayerID','Player_Name','Player_Team'])['MIN', 'FGM', 'FGA', 'FTM', 'FTA', '3PM', '3PA', 'PTS', 'STL', 'BLK', 'AST', 'OFF', 'DEF', 'TOT', 'TO', 'PF'].sum().reset_index()

def player_totals_advanced(player_totals_df):
    player_totals_df['eFG'] = (player_totals_df['FGM'] + 0.5 * player_totals_df['3PM']) / player_totals_df['FGA']
    player_totals_df['TS%'] = player_totals_df['PTS'] / (2 * (player_totals_df['FGA'] + 0.44 * player_totals_df['FTA']))
    player_totals_df['eFG'].fillna(0, inplace=True)
    player_totals_df['TS%'].fillna(0, inplace=True)
    player_totals_df['PTS_per24'] = player_totals_df['PTS'] / player_totals_df['MIN'] * 24
    player_totals_df['STL_per24'] = player_totals_df['STL'] / player_totals_df['MIN'] * 24
    player_totals_df['BLK_per24'] = player_totals_df['BLK'] / player_totals_df['MIN'] * 24
    player_totals_df['AST_per24'] = player_totals_df['AST'] / player_totals_df['MIN'] * 24
    player_totals_df['REB_per24'] = player_totals_df['TOT'] / player_totals_df['MIN'] * 24
    player_totals_df['PTS_rank'] = player_totals_df['PTS'].rank(ascending=False, method='min').astype('int64')
    player_totals_df['OREB_rank'] = player_totals_df['OFF'].rank(ascending=False, method='min').astype('int64')
    player_totals_df['DREB_rank'] = player_totals_df['OFF'].rank(ascending=False, method='min').astype('int64')
    player_totals_df['REB_rank'] = player_totals_df['TOT'].rank(ascending=False, method='min').astype('int64')
    player_totals_df['AST_rank'] = player_totals_df['AST'].rank(ascending=False, method='min').astype('int64')
    player_totals_df['STL_rank'] = player_totals_df['STL'].rank(ascending=False, method='min').astype('int64')
    player_totals_df['TO_rank'] = player_totals_df['TO'].rank(ascending=False, method='min').astype('int64')
    player_totals_df['BLK_rank'] = player_totals_df['BLK'].rank(ascending=False, method='min').astype('int64')
    player_totals_df['PF_rank'] = player_totals_df['PF'].rank(ascending=False, method='min').astype('int64')
    player_totals_df['eFG_rank'] = player_totals_df['eFG'].rank(ascending=False, method='min').astype('int64')
    player_totals_df['TS%_rank'] = player_totals_df['TS%'].rank(ascending=False, method='min').astype('int64')

def team_totals_by_game(df):
    return df.groupby(['Player_Team','gameID','OPP'])['MIN', 'FGM', 'FGA', 'FTM', 'FTA', '3PM', '3PA', 'PTS', 'STL', 'BLK', 'AST', 'OFF', 'DEF', 'TOT', 'TO', 'PF'].sum().reset_index()

def syc_game_totals(df):
    syc_team = df['Player_Team']=='Sycamore'
    return df[syc_team].reset_index(drop=True)

def syc_opp(df):
    syc_game = df['OPP']=='Sycamore'
    col_same = {'Player_Team','gameID','OPP'}
    suffix = df['Player_Team'].str[:3]
    return df[syc_game]

def syc_opp_columns_suffix(df):
    suffix = df['Player_Team'].str[:3]
    new_names = [(i, i + '_' + suffix) for i in df.iloc[:, 3:].columns.values]
    column_names = ['Player_Team','GameID','OPP']
    for col in new_names:
        column_names.append(col)
    df=df[column_names]
    return df

def syc_players(df):
    syc_player_ind = df['Player_Team']=='Sycamore'
    return df[syc_player_ind].reset_index(drop=True)

def join_opp(df):
    df_merge = df.merge(right=syc_opponent_totals_df,how='inner',on='gameID',suffixes=('_player','_OPP'))
    df_merge_2 = df_merge.merge(right=syc_totals_by_game_df,how='inner',on='gameID',suffixes=('','_SYC'))
    return df_merge_2

#global variables
season_stats_out = []
teams_url = {'Lakota East':'http://gmcsports.com/bkPlayerStats.aspx?player=136805','Middletown':'http://gmcsports.com/bkPlayerStats.aspx?player=137323','Princeton':'http://gmcsports.com/bkPlayerStats.aspx?player=136917','Mason':'http://gmcsports.com/bkPlayerStats.aspx?player=134719','Fairfield':'http://gmcsports.com/bkPlayerStats.aspx?player=137811','Lakota West':'http://gmcsports.com/bkPlayerStats.aspx?player=136248','Sycamore':'http://gmcsports.com/bkPlayerStats.aspx?player=137585','Oak Hills': 'http://gmcsports.com/bkPlayerStats.aspx?player=135306','Colerain':'http://gmcsports.com/bkPlayerStats.aspx?player=135052','Hamilton':'http://gmcsports.com/bkPlayerStats.aspx?player=137140'}
school_ids = {1:'Colerain',2:'Fairfield',3:'Hamilton',4:'Lakota East',5:'Lakota West',29:'Mason',6:'Middletown',8:'Oak Hills',9:'Princeton',10:'Sycamore'}
school_directory_output=get_school_directory(school_ids)
player_directory_output=get_player_directory(school_ids)

for team in teams_url:
    url = teams_url.get(team)
    team_nm = team
    r = requests.get(url)
    data = r.text
    soup = bs(data,'lxml')
    roster = soup.find(id='playerRosterInfo')
    names = roster.find_all('option')
    player_urls = url_list(soup)
    stats = soup.find(id='statsContent')
    trow = stats.find_all('tr')
    headers = stats.find('tbody',class_='numeric')
    non_numeric_cols = {'PlayerID','Player_Name','Player_Team', 'DATE', 'OPP', 'RESULT', 'SCORE', 'Court'}
    columns_df = get_columns(headers)
    table_ids = get_table_ids(soup)
    season_stats = get_season_stats_by_player(player_urls)

#create data frame
df = pd.DataFrame(season_stats,columns=columns_df)
split_columns(df)
to_numeric(df,non_numeric_cols)
edit_dates(df)
game_score_stats(df)
df=df[['PlayerID','Player_Name','Player_Team','DATE','gameID','OPP','Court','RESULT','SCORE','MIN','FGM','FGA','3PM','3PA','FTM','FTA','STL','BLK','AST','TO','PF','OFF','DEF','TOT','PTS','GMSCORE','GS_RANK']]

syc_players_by_game_df = syc_players(df)
player_averages_df = player_averages(df)
player_totals_df = player_totals(df)
player_totals_advanced(player_totals_df)
team_totals_by_game_df = team_totals_by_game(df)
syc_totals_by_game_df = syc_game_totals(team_totals_by_game_df)
syc_opponent_totals_df = syc_opp(team_totals_by_game_df)
suffix = syc_opponent_totals_df['Player_Team'].str[:3]
syc_opponent_totals_df.columns=['Player_Team','gameID','OPP','MIN_','FGM','FGA','FTM','FTA','3PM','3PA','PTS','STL','BLK','AST','OFF','DEF','TOT','TO','PF']
syc_players_team_join_df = join_opp(syc_players_by_game_df)

#df_join = df.merge(syc_opponent_totals_df,suffixes=('_SYC','_OPP'),on='gameID')
#df_join.to_csv('/home/danny/Documents/GMC_scrape/season_stats_by_game_join_TEST.csv',encoding='utf-8')

#df.to_csv('/home/danny/Documents/GMC_scrape/player_season_stats_by_game.csv',encoding='utf-8')
#syc_players_by_game_df.to_csv('/home/danny/Documents/GMC_scrape/player_season_stats_by_game_SYC.csv',encoding='utf-8')
syc_players_team_join_df.to_csv('/home/danny/Documents/GMC_scrape/player_season_stats_by_game_SYC_opp_team_join.csv',encoding='utf-8')
#syc_totals_by_game_df.to_csv('/home/danny/Documents/GMC_scrape/SYC_team_totals_by_game.csv',encoding='utf-8')
#player_averages_df.to_csv('/home/danny/Documents/GMC_scrape/player_season_averages.csv',encoding='utf-8')
#player_totals_df.to_csv('/home/danny/Documents/GMC_scrape/player_season_totals.csv',encoding='utf-8')
#team_totals_by_game_df.to_csv('/home/danny/Documents/GMC_scrape/all_team_game_totals.csv', encoding='utf-8')
#syc_opponent_totals_df.to_csv('/home/danny/Documents/GMC_scrape/syc_games_opp_totals.csv', encoding='utf-8')

