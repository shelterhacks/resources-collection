import requests
import urllib.request
import time
from bs4 import BeautifulSoup
import pandas as pd 

url = 'http://www.hudhousing.org/nationwide-public-housing/massachusetts-public-housing'

response = requests.get(url)
print(response.text)

soup = BeautifulSoup(response.text, 'html.parser')

table = soup.findAll('table')[0]
print(table)

new_table = pd.DataFrame(columns=range(0,4), index=range(0,136))

new_dict = {}
row_marker = 0
for row in table.findAll('tr'): 
	column_marker = 0 
	columns = row.findAll('td')
	for column in columns: 
		# print(row_marker, column_marker)
		# new_dict[column]
		new_table.iat[row_marker, column_marker] = column.get_text()
		column_marker+=1
	row_marker += 1
# data = pd.read_html(url)
# print(data)
print(new_table)
new_table.to_csv("section8.csv")