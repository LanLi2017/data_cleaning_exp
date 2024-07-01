plan_add_column_demo = '''To answer the question, we can first use f_add_column() to add more columns by applying transformations, similar to f_trans_column() to the table.

/*
col : week | when | kickoff | opponent | results; final score | results; team record | game site | attendance
row 1 : 1 | saturday, april 13 | 7:00 p.m. | at rhein fire | w 27–21 | 1–0 | rheinstadion | 32,092
row 2 : 2 | saturday, april 20 | 7:00 p.m. | london monarchs | w 37–3 | 2–0 | waldstadion | 34,186
row 3 : 3 | sunday, april 28 | 6:00 p.m. | at barcelona dragons | w 33–29 | 3–0 | estadi olímpic de montjuïc | 17,503
*/
Purpose: Return top 5 competitions that have the most attendance.
Function: f_add_column({"baseColumnName": "attendance", expression:"value", "newColumnName":"attendance number"})
Explanation: We copy the value from column "attendance" and create a new column "attendance number" for each row.
'''

plan_select_column_demo = '''If the table only needs a few columns to answer the question, we use f_select_column() to select these columns for it. For example,
/*
col : Code | County | Former Province | Area (km2) | Population | Capital
row 1 : 1 | Mombasa | Coast | 212.5 | 939,370 | Mombasa (City)
row 2 : 2 | Kwale | Coast | 8,270.3 | 649,931 | Kwale
row 3 : 3 | Kilifi | Coast | 12,245.9 | 1,109,735 | Kilifi
*/
Question: what is the total number of counties with a population higher than 500000?
Function: f_select_column(County, Population)
Explanation: The question asks about the number of counties with a population higher than 500,000. We need to know the county and its population. We select column "County" and column "Population".'''

plan_select_row_demo = '''If the table only needs a few rows to answer the question, we use f_select_row() to select these rows for it. For example,
/*
col : Home team | Home Team Score | Away Team | Away Team Score | Venue | Crowd | Date
row 1 : st kilda | 13.12 (90) | melbourne | 13.11 (89) | moorabbin oval | 18836 | 19 august 1972
row 2 : south melbourne | 9.12 (66) | footscray | 11.13 (79) | lake oval | 9154 | 19 august 1972
row 3 : richmond | 20.17 (137) | fitzroy | 13.22 (100) | mcg | 27651 | 19 august 1972
*/
Question : Whose home team score is higher, richmond or st kilda?
Function: f_select_row(row 1, row 3)
Explanation: The question asks about the home team score of richmond and st kilda. We need to know the the information of richmond and st kilda in row 1 and row 3. We select row 1 and row 3.'''

plan_group_column_demo = '''If the question asks about items with the same value and the number of these items, we use f_group_column() to group the items. For example,
/*
col : District | Name | Party | Residence | First served
row 1 : District 1 | Nelson Albano | Dem | Vineland | 2006
row 2 : District 1 | Robert Andrzejczak | Dem | Middle Twp. | 2013†
row 3 : District 2 | John F. Amodeo | Rep | Margate | 2008
*/
Question: how many districts are democratic?
Function: f_group_column(Party)
Explanation: The question asks about how many districts are democratic. We need to know the number of Dem in the table. We group the rows according to column "Party".'''

plan_sort_column_demo = '''If the question asks about the order of items in a column, we use f_sort_column() to sort the items. For example,
/*
col : Position | Club | Played | Points
row 1 : 1 | Malaga CF | 42 | 79
row 10 : 10 | CP Merida | 42 | 59
row 3 : 3 | CD Numancia | 42 | 73
*/
Question: what club placed in the last position?
Function: f_sort_column(Position)
Explanation: The question asks about the club in the last position. We need to know the order of position from last to front. We sort the rows according to column "Position".'''

plan_full_chain_demo = '''Here are examples of using the operations to answer the question.

/*
col : Week | When | Kickoff | Opponent | Results; Final score | Results; Team record | Game site | Attendance
row 1 : 1 | Saturday, April 13 | 7:00 p.m. | at Rhein Fire | W 27–21 | 1–0 | Rheinstadion | 32,092
row 2 : 2 | Saturday, April 20 | 7:00 p.m. | London Monarchs | W 37–3 | 2–0 | Waldstadion | 34,186
row 3 : 3 | Sunday, April 28 | 6:00 p.m. | at Barcelona Dragons | W 33–29 | 3–0 | Estadi Olímpic de Montjuïc | 17,503
*/
Question: what is the date of the competition with highest points scored?
Function Chain: f_add_column(Points scored) -> f_select_row(row 1, row 2, row 3) -> f_sort_column(Points scored) -> <END>

/*
col : ISO/IEC Standard | Status | WG
row 1 : ISO/IEC TR 19759 | Published (2005) | 20
row 2 : ISO/IEC 15288 | Published (2008) | 7
row 3 : ISO/IEC 12207 | Published (2011) | 7
*/
Question: what is the number of standards published in 2011?
Function Chain: f_add_column(Year) -> f_select_row(row 3) -> f_group_column(Year) -> <END>

*/
Table page title: Reform Party of Florida
Table section title: Presidential nominee results
col : Year | Nominee | Votes
row 1 : 1996 | Ross Perot | 483,870 (9.12%)
row 2 : 2000 | Patrick Buchanan | 17,484 (0.29%)
row 3 : 2004 | Ralph Nader | 32,971 (0.43%)
row 4 : 2008 | No Candidate | 0 (0%)
row 5 : 2012 | Andre Barnett | 820 (0.01%)
row 6 : 2016 | Rocky De La Fuente | 9,108 (0.10%)
*/
Question: How did the Reform Party's candidate perform in Florida in the 2004 presidential election?
Function Chain: f_add_column(Votes Number) -> f_select_row(row 3) -> <END>'''
