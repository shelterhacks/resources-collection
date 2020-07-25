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

new_table = pd.DataFrame(columns=range(0,7), index=range(0,136))
def decodeEmail(e):
    de = ""
    k = int(e[:2], 16)

    for i in range(2, len(e)-1, 2):
        de += chr(int(e[i:i+2], 16)^k)

    return de
new_dict = {}
row_marker = 0
# https://stackoverflow.com/questions/23380171/using-beautifulsoup-to-extract-text-without-tags
for row in table.findAll('tr'): 
	column_marker = 0 
	columns = row.findAll('td')
	for column in columns: 
		# print(row_marker, column_marker)
		# new_dict[column]
		if column.find('a'): 
			children = column.findChildren()
			for a_tag in column.findAll('a'): 
				protected_email = a_tag.get('href')
				print(a_tag.text)
				new_table.iat[row_marker, column_marker] = a_tag.text
				column_marker+=1
				
				encrypted_email = protected_email.split('#', 1)[1]
				decoded_email = decodeEmail(encrypted_email)
				# https://stackoverflow.com/questions/12572362/how-to-get-a-string-after-a-specific-substring
				new_table.iat[row_marker, column_marker] = decoded_email
				column_marker+=1
			for bold in column.findAll('b'): 
				new_table.iat[row_marker, column_marker] = bold.next_sibling
				print(bold.text, bold.next_sibling)
				column_marker+=1

		else: 
			new_table.iat[row_marker, column_marker] = column.get_text()
			column_marker+=1
	row_marker += 1
# data = pd.read_html(url)
# print(data)
print(new_table)
new_table.to_csv("section8.csv")