#Creating dataframe to assign gameweek scheduling

#empty lists to save dates
dates_start = []
dates_end = []
for x in range(0,18):
    #start of season and remaining weeks (except week 18) are on thursdays - 7 days from then will be start of new week
    dates_start.append(date(2021,9,8) + timedelta(days = 7*x))
    #end of week will be monday each week (except for week 18 again)
    dates_end.append(date(2021,9,12) +timedelta(days = 7*x))


week_df = pd.DataFrame()
week_df["week"] = week
week_df["week_start"] = dates_start
week_df["week_end"] = dates_end

#replacing week 18 values due to strict saturday-sunday NFL schedule
week_df.at[week_df.index.max(),"week_start"] = date(2022,1,7)
week_df.at[week_df.index.max(),"week_end"] = date(2022,1,8)

week_df.to_csv("/Users/lawandyaseen/Desktop/collaboration/RedditTextAnalysis/nfl_week_dates.csv", index = False)
