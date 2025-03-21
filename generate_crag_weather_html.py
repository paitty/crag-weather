import json
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
import requests

headers = {'Accept':	'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Encoding':	'gzip, deflate, br, zstd',
    'Accept-Language':	'en-US,fr;q=0.8,hr;q=0.5,en;q=0.3',
    'Connection':	'keep-alive',
    'DNT':	'1',
    'Host':	'api.met.no',
    'Priority':	'u=0, i',
    'Sec-Fetch-Dest':	'document',
    'Sec-Fetch-Mode':	'navigate',
    'Sec-Fetch-Site':	'none',
    'Sec-Fetch-User':	'?1',
    'Sec-GPC':	'1',
    'sitename': 'https://github.com/paitty/crag-weather.git',
    'Upgrade-Insecure-Requests':	'1',
    'User-Agent':	'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:135.0) Gecko/20100101 Firefox/135.0'}


with open('climbing-locations.json') as f:
    climbing_locations = json.load(f)

for location in climbing_locations.keys():
    print(location)

# datetime object containing current date and time
now = datetime.now()

# dd/mm/YY H:M:S
header_now_date_time = now.strftime("%d/%m/%Y %H:%M:%S")

def get_next_weekday(startdate, weekday):
    """
    @startdate: given date, in format '2013-05-25'
    @weekday: week day as a integer, between 0 (Monday) to 6 (Sunday)
    """
    d = datetime.strptime(startdate, '%Y-%m-%d')
    t = timedelta((7 + weekday - d.weekday()) % 7)
    return (d + t).strftime('%Y-%m-%d')

def get_next_weekend():
    """
    @startdate: given date, in format '2013-05-25'
    @weekday: week day as a integer, between 0 (Monday) to 6 (Sunday)
    """
    d = now
    t = timedelta((7 + 5 - d.weekday()) % 7)
    start = (d+t).replace(hour=7, minute=0, second=0, microsecond=0)
    end = start+timedelta(hours=36)
    return start, end

start, end = get_next_weekend()

def get_next_weekend_short():
    """
    @startdate: given date, in format '2013-05-25'
    @weekday: week day as a integer, between 0 (Monday) to 6 (Sunday)
    """
    d = now
    t1 = timedelta((7 + 5 - d.weekday()) % 7)
    t2=t1+timedelta(days = 1)
    weekend = (d + t1).strftime('%d')+"-"+(d + t2).strftime('%d/%m/%Y')
    return weekend

header_next_weekend = get_next_weekend_short()

HTML_DOC = """<!DOCTYPE html>
<html>
<head>
	<style type="text/css">
		.myTable { background-color:#eee;border-collapse:collapse; }

		.myTable td, .myTable th { padding:5px;border:1px solid #000; }
	</style>
	<title>Crag Weather</title>
</head>
<body>

	<h1>Idemo penjati u *Damelju*!</h1>

	<p>Vikend """+header_next_weekend+"""
	<br>
	Updated on """+header_now_date_time+"""
	<br>
	Based on yr.no API
	</p>

	</body>
	</html>

            """


soup = BeautifulSoup(HTML_DOC, "html.parser")

def add_weather(location, start_date, end_date):
    #example call
    #https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=45.434&lon=15.188
    url = "https://api.met.no/weatherapi/locationforecast/2.0/compact?lat="+str(location[0])[:6]+"&lon="+str(location[1])[:6]
    r= requests.get(url, headers=headers)
    weather=r.json()
    i=0
    min_temp = 100
    max_temp = -100
    rain = 0
    min_wind =100
    max_wind = -100

    while True:
        #TODO check if the datetime is our time
        datetime_object = datetime.fromisoformat(weather['properties']['timeseries'][i]['time'])
        if datetime_object.replace(tzinfo=None)>start_date:
            temperature = weather['properties']['timeseries'][i]['data']['instant']['details']['air_temperature']
            wind = weather['properties']['timeseries'][i]['data']['instant']['details']['wind_speed']
            add_rain= weather['properties']['timeseries'][i]['data']['next_1_hours']['details']['precipitation_amount']
            min_temp = min(min_temp, temperature)
            max_temp = max(max_temp, temperature)
            min_wind = min(min_wind, wind)
            max_wind = max(max_wind, wind)
            rain = rain + add_rain
        if datetime_object.replace(tzinfo=None)>end_date:
            break
        i=i+1
    return min_temp, max_temp, rain, min_wind, max_wind

start_date, end_date =  get_next_weekend()

for key in climbing_locations.keys():
    location = climbing_locations[key]['location']
    min_temp, max_temp, rain, min_wind, max_wind = add_weather(location, start_date, end_date)
    climbing_locations[key]['Temp']=str(int(min_temp))+"-"+str(int(max_temp))+"°"
    climbing_locations[key]['Rain']=str(int(rain))+" mm"
    climbing_locations[key]['Wind']=str(int(min_wind))+"-"+str(int(max_wind))+" m/s"
    
def get_duration(location):
    zagreb = "15.957378573800682,45.789809813280925"
    destination = str(location[1])+","+str(location[0])
    url = "http://router.project-osrm.org/table/v1/driving/"+zagreb+";"+destination
    r= requests.get(url)
    duration = str(int(r.json()['durations'][0][1]/60))
    return duration

def createTable():
    new_table=soup.new_tag("table")
    new_table.attrs['class']='myTable'
    soup.html.body.append(new_table)
    display_table = soup.html.body.find_all("table")[-1]
    
    table_names=['Crag','Temp','Rain','Wind','Distance','Yr.no','Windy.com'] #['Crag','Temp','Rain','Wind','Distance','Yr.no','Windy.com']
    new_header = soup.new_tag("tr")
    display_table.append(new_header)
    for col in table_names:
        new_column_header = soup.new_tag("th")
        new_column_header.string=col
        display_table.tr.append(new_column_header)

    for key in climbing_locations.keys():
        new_line = soup.new_tag("tr")
        display_table.append(new_line)
        last_line=display_table.find_all("tr")[-1]
        for col in table_names:
            new_tag=soup.new_tag('td')
            if col == 'Crag':
                new_tag.string=key
            elif col == 'Yr.no':
                new_link=soup.new_tag('a')
                new_link.string='link'
                new_link.attrs['href'] = 'https://www.yr.no/en/forecast/daily-table/'+str(climbing_locations[key]['location'][0])[:6]+", "+str(climbing_locations[key]['location'][1])[:6]
                new_link.attrs['target'] = '_blank'
                new_tag.append(new_link)
            elif col == 'Windy.com':
                new_link=soup.new_tag('a')
                new_link.string='link'
                new_link.attrs['href'] = 'https://www.windy.com/'+str(climbing_locations[key]['location'][0])[:6]+"/"+str(climbing_locations[key]['location'][1])[:6]
                new_link.attrs['target'] = '_blank'
                new_tag.append(new_link)
            elif col == 'Distance':
                #TODO find better way to store distance
                new_tag.string=get_duration(climbing_locations[key]['location'])+" min"
            else:
                new_tag.string=climbing_locations[key][col]
            last_line.append(new_tag)

createTable()

html = soup.prettify("utf-8")
with open("index.html", "wb") as file:
    file.write(html)