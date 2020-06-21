#FLOW-OF THE CODE
#1. Get health expenditure oas a percentage of GDP of each countries. *Data I got here was only till 2017
#2. Get daily covid-19 cases repoted in each country
#3. Now dot eh following:
#    a. Get the date when maximum number of covid-19 cases were observed in a country
#    b. Get the 3rd quartile date
#    c. If the date of max cases is <= 3rd quartile date it means we haven't seen higher cases in last 25% of the recorded time frame starting today and going backwards
#          d. Take the difference of minimum record date and date obtained above as days it took to approach conditiond of flatline/downfall
#          Assumption here is, if out of 100 days we havent recorded as high as highest of all time cases post 75th date, then we can say that COVID-19 situation is stabilizing
#4. Get only the records of those countries where in max of alltime records were falling in 1st 3 quartiles.
#5. Run multiple linear regression on the dataset with days to flatline as target variable and population and health expenditure as independent
#6. Get the predicted days values by putting the realized intercept and coefficient values in regression values
#7. add the values to the minimum record date to get the dates when it will flatline

#import operations

import pandas as pd
import io
import requests
from datetime import datetime
from datetime import timedelta
from sklearn import linear_model

#Getting data for Each country's health expenditure as a portion of their GDP
health_expenditure_csv          =   'https://apps.who.int/gho/athena/data/GHO/GHED_CHEGDP_SHA2011?filter=REGION:*;COUNTRY:*&x-sideaxis=COUNTRY&x-topaxis=GHO;YEAR&profile=crosstable&format=csv'
csv_string_load                 =   requests.get(health_expenditure_csv).content                            #Reading the URL content
health_expenditure_df           =   pd.read_csv(io.StringIO(csv_string_load.decode('utf-8')))               #Converting the recevied string in to a file object, decoding it to UTF-8 for dataframe's read_csv function
new_header                      =   health_expenditure_df.iloc[0]                                           #Returns pandas series containing values of first row
health_expenditure_df           =   health_expenditure_df[1:]                                               #Takes all the data from dataframe starting from second row ||| in short we are removing the first raw
health_expenditure_df.columns   =   new_header                                                              #Setting the first row as header to the new data frame
health_expenditure_df           =   health_expenditure_df[['Country',2017.0]]                               #Getting only the required columns
health_expenditure_df.columns   =   ['country','YR_2017']                                                   #Renaming the columns

#Getting data for Each Country's COVID19 reports reported per day since 12/31/2019 till the previous date of the date the code runs on.
yesterdays_date         =  (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")                        #The site has a data latency of 1 day. hence We'll have to get data for dates until yesterday
covid19_cases_excel     =  'https://www.ecdc.europa.eu/sites/default/files/documents/COVID-19-geographic-disbtribution-worldwide-{}.xlsx'.format(yesterdays_date)
covid_xl_string_load    =  requests.get(covid19_cases_excel).content                                        #Reading the URL content
covid_cases_df          =  pd.read_excel(io.BytesIO(covid_xl_string_load))                                  #Converting the recevied string in to a file object, decoding it to UTF-8 for dataframe's read_csv function
covid_cases_df          =  covid_cases_df[['dateRep','cases','countriesAndTerritories','popData2019']]      #Renaming the columns

#Formatting the data in dataframe to get the final DF upon which we'll perform regression.
columns                     = ['country','flatlinedays', 'population']                                      #Creating an empty dataframe
regression_df               = pd.DataFrame(columns=columns)                                                 #Giving column names
country_list                = covid_cases_df['countriesAndTerritories'].unique().tolist()                   #Getting the list of unique countries from covid19 database to iterate the group by clause over the names
countries_groupe_by_object  = covid_cases_df.groupby(covid_cases_df.countriesAndTerritories)                #Creating a group by over country names column
for country in country_list:           
    country_df                  = countries_groupe_by_object.get_group(country)                             #Create a dataframe of only one coutry details
    flat_date_limit             = pd.Timestamp(country_df.dateRep.quantile([0.75])[0.75])                   #Get the 3rd quartile date
    date_max_cases_reported     = country_df.loc[country_df['cases'] == country_df.cases.max(), 'dateRep'].iloc[0] #Get the date when max cases till today were recorded
    date_start_cases_reported   = country_df.dateRep.min()                                                  #get the earliest date fro when we have the data for a country
    days_flat_line_reached      = 0                                                                         #Create a days variable which shows the day when we started to see a decline in covid19 cases on daily basis
    if date_max_cases_reported <= flat_date_limit:                                                          #If we have not seen highest number of cases in last 25% of observable time frame from today till backwards
        days_flat_line_reached  = (date_max_cases_reported - date_start_cases_reported).days                #Take the difference of maxcases date and min date as days required to reach flatline
    else:                                                                                                   #Else take the days as 0
        days_flat_line_reached  = 0
    regression_df               = regression_df.append({'country' : country_df['countriesAndTerritories'].unique()[0] , 'flatlinedays' : days_flat_line_reached,'population' : country_df['popData2019'].unique()[0]} , ignore_index=True) #append to the empty dataframe the 4 records of country, flatline days, and population
indexes                         = regression_df[regression_df['flatlinedays'] == 0].index                   #get indexes for records where we hae max cases in 4th quartile
regression_df.drop(indexes,inplace = True)                                                                  #drop the records that have still not reached the flatline
final_regression_df             = pd.merge(regression_df, health_expenditure_df, on='country', how='left').fillna(0) #Combine the dataframe with health expenditure as a percentage of GDP and replace nulls with 0
final_regression_df.columns     = ['country','flatlinedays', 'population','health_expense']                 #Give final column names 

#Performing multiple linear regression to get an equation

X = final_regression_df[['health_expense','population']] 
Y = final_regression_df['flatlinedays']

regression = linear_model.LinearRegression()
regression.fit(X, Y)

intercept = regression.intercept_
health_expense_coeff = regression.coef_[0]
population_coeff = regression.coef_[1]

#Calculating the days to get flatlined for India
country = "India"  
INDIA_df                = countries_groupe_by_object.get_group(country)                                     #get the dataframe values of only the intended country
min_report_dt           = INDIA_df.dateRep.min()                                                            #get the minimum reporting date
population              = INDIA_df['popData2019'].unique()[0]                                               #Get the population
health_expense          = health_expenditure_df.loc[health_expenditure_df['country'] == country, 'YR_2017'].iloc[0] #Get the health exepense per GDP
days_to_get_flatlined   = intercept + (population*population_coeff) + (health_expense*health_expense_coeff) #Substitute the values in regression equation


print("Days to get flatlined:{}".format(min_report_dt + timedelta(days=days_to_get_flatlined)))             #add the days to minimum report date to get date when it will flatlined

#Ouput in case of INDIA : 13th March 2020
#This model for the lack of data and sheer neglecttowards proper feature selection fails to give an accurate picture

#Reason for taking population and health expenditure are as follows
#1. Population: The higher the number of subjects higher will be the liklihood of infections increasing. Considering all the nations of the world are of equal surface area with varying density of population per sq meter which will be directly proportional to the popoulation size
#2. Health expense as % of GDP: The higher the %age, more is the capability to fight against the pandemic
