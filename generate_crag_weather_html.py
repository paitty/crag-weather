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

#for location in climbing_locations.keys():
#    print(location)

# datetime object containing current date and time
now = datetime.now()

# dd/mm/YY H:M:S
now2 = now + timedelta(hours=2)
header_now_date_time = now2.strftime("%d/%m/%Y %H:%M:%S")

def get_next_weekday(startdate, weekday):
    """
    @startdate: given date, in format '2013-05-25'
    @weekday: week day as a integer, between 0 (Monday) to 6 (Sunday)
    """
    d = datetime.strptime(startdate, '%Y-%m-%d')
    t = timedelta((7 + weekday - d.weekday()) % 7)
    return (d + t).strftime('%Y-%m-%d')

def get_next_day(day,duration):
    """
    @startdate: given date, in format '2013-05-25'
    @weekday: week day as a integer, between 0 (Monday) to 6 (Sunday)
    """
    if day=='Monday':
        day_num = 0
    if day=='Tuesday':
        day_num = 1
    if day=='Wednesday':
        day_num = 2
    if day=='Thursday':
        day_num = 3
    if day=='Friday':
        day_num = 4
    if day=='Saturday':
        day_num = 5
    if day=='Sunday':
        day_num = 6
    d = now
    t = timedelta((7 + day_num - d.weekday()) % 7)

    start = (d+t).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start+timedelta(hours=duration)
    return start, end

days_of_a_week = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
days_of_the_week = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
for i in range(7):
    days_of_the_week[i] = days_of_a_week[(now.weekday()+i)%7]

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

def get_duration(location):
    zagreb = "15.957378573800682,45.789809813280925"
    destination = str(location[1])+","+str(location[0])
    url = "http://router.project-osrm.org/table/v1/driving/"+zagreb+";"+destination
    r= requests.get(url)
    duration = r.json()['durations'][0][1]/60
    return duration

def get_distance(key):
    if 'Distance' in climbing_locations[key].keys():
        distance=climbing_locations[key]['Distance']
    else:
        distance = get_duration(climbing_locations[key]['location'])
        climbing_locations[key]['Distance'] = distance
        with open('climbing-locations.json', 'w') as f:
            json_pretty = json.dumps(climbing_locations, indent=2)
            f.write(json_pretty)
    return distance

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
        if datetime_object.replace(tzinfo=None)>=start_date:
            temperature = weather['properties']['timeseries'][i]['data']['instant']['details']['air_temperature']
            wind = weather['properties']['timeseries'][i]['data']['instant']['details']['wind_speed']
            if 'next_1_hours' in weather['properties']['timeseries'][i]['data']:
                add_rain= weather['properties']['timeseries'][i]['data']['next_1_hours']['details']['precipitation_amount']
            else:
                #TODO check if we dont miss anything like that
                add_rain= weather['properties']['timeseries'][i]['data']['next_6_hours']['details']['precipitation_amount']
            #if location[0] == 44.30403029180178:
            #    print(datetime_object.replace(tzinfo=None))
            #    if 'next_1_hours' in weather['properties']['timeseries'][i]['data']:
            #        print(weather['properties']['timeseries'][i]['data']['next_1_hours']['details']['precipitation_amount'])
            #    else:
            #        #TODO check if we dont miss anything like that
            #        print(weather['properties']['timeseries'][i]['data']['next_6_hours']['details']['precipitation_amount'])
            min_temp = min(min_temp, temperature)
            max_temp = max(max_temp, temperature)
            min_wind = min(min_wind, wind)
            max_wind = max(max_wind, wind)
            rain = rain + add_rain
        if datetime_object.replace(tzinfo=None)>=end_date:
            break
        i=i+1
    return min_temp, max_temp, rain, min_wind, max_wind

def createTable():
    new_table=soup.new_tag("table")
    new_table.attrs['class']='myTable'
    new_table.attrs['id']='myTable2'
    soup.html.body.append(new_table)
    display_table = soup.html.body.find_all("table")[-1]

    table_names=['Crag']+days_of_the_week+['Temp','Rain','Wind','Distance','Yr.no','Windy','plezanje.net','theCrag','Maps','Waze']
    new_header = soup.new_tag("tr")
    display_table.append(new_header)
    for col in table_names:
        new_column_header = soup.new_tag("th")
        new_column_header.string=col
        display_table.tr.append(new_column_header)

    for key in crag_score_sorted:
        new_line = soup.new_tag("tr")
        if 'type' in climbing_locations[key].keys():
            new_line.attrs['type']=climbing_locations[key]['type']
        display_table.append(new_line)
        last_line=display_table.find_all("tr")[-1]
        destination = 'location'
        if 'parking' in climbing_locations[key].keys():
            destination = 'parking'
        for col in table_names:
            new_tag=soup.new_tag('td')
            if col == 'Crag':
                new_tag.string=key
            elif col == 'Yr.no':
                new_link=soup.new_tag('a')
                new_link.string='Yr.no'
                new_link.attrs['href'] = 'https://www.yr.no/en/forecast/daily-table/'+str(climbing_locations[key]['location'][0])[:6]+", "+str(climbing_locations[key]['location'][1])[:6]
                new_link.attrs['target'] = '_blank'
                new_tag.append(new_link)
            elif col == 'Windy':
                new_link=soup.new_tag('a')
                new_link.string='Windy'
                new_link.attrs['href'] = 'https://www.windy.com/'+str(climbing_locations[key]['location'][0])[:6]+"/"+str(climbing_locations[key]['location'][1])[:6]
                new_link.attrs['target'] = '_blank'
                new_tag.append(new_link)
            elif col == 'plezanje.net':
                new_link=soup.new_tag('a')
                new_link.string='plezanje.net'
                new_link.attrs['href'] = 'https://plezanje.net/plezalisce/'+key.replace('(','').replace(')','').replace(' ','-').lower()
                new_link.attrs['target'] = '_blank'
                new_tag.append(new_link)
            elif col == 'theCrag':
                new_link=soup.new_tag('a')
                new_link.string='theCrag'
                new_link.attrs['href'] = 'https://www.thecrag.com/en/climbing/world/search?only=areas&S='+key
                new_link.attrs['target'] = '_blank'
                new_tag.append(new_link)
            elif col == 'Maps':
                new_link=soup.new_tag('a')
                new_link.string='Maps'
                new_link.attrs['href'] = 'https://www.google.com/maps/place/'+str(climbing_locations[key][destination][0])[:6]+","+str(climbing_locations[key][destination][1])[:6]
                new_link.attrs['target'] = '_blank'
                new_tag.append(new_link)
            elif col == 'Waze':
                new_link=soup.new_tag('a')
                new_link.string='Waze'
                new_link.attrs['href'] = 'waze://?ll='+str(climbing_locations[key][destination][0])[:6]+","+str(climbing_locations[key][destination][1])[:6]
                new_link.attrs['target'] = '_blank'
                new_tag.append(new_link)    
            elif col == 'Distance':
                #TODO find better way to store distance
                distance = get_distance(key)
                total_minutes=int(int(distance)/10)*10
                minutes=total_minutes%60
                hours=(total_minutes-minutes)/60
                if hours == 0:
                    new_tag.string=str(minutes)+" min"
                else:
                    new_tag.string=str(int(hours))+"h"+str(minutes)+"m"
            elif col in days_of_the_week:
                new_img=soup.new_tag('img')
                new_img.attrs['src'] = 'check-mark.png'
                new_img.attrs['width'] = 20
                if 'Temp_style' in climbing_day[col][key].keys():
                    new_img.attrs['src'] = 'hot.PNG'                  
                if 'Wind_style' in climbing_day[col][key].keys():
                    new_img.attrs['src'] = 'wind-leaf.png'                  
                if 'Rain_style' in climbing_day[col][key].keys():
                    new_img.attrs['src'] = 'cloud-with-rain.png'
                new_tag.append(new_img)
            else:
                if col+'_style' in climbing_weather[key].keys():
                    new_tag.attrs['style']="font-weight:bold"
                new_tag.string=climbing_weather[key][col]
            last_line.append(new_tag)

#start, end = get_next_weekend()

start_date, end_date =  get_next_day('Saturday',48)
climbing_weather = {}

for key in climbing_locations.keys():
    location = climbing_locations[key]['location']
    min_temp, max_temp, rain, min_wind, max_wind = add_weather(location, start_date, end_date)
    climbing_weather[key]={}
    climbing_weather[key]['Temp']=str(int(min_temp))+"-"+str(int(max_temp))+"°"
    climbing_weather[key]['Rain']=int(rain)
    if rain>6:
        climbing_weather[key]['Rain_style']='bold'
    climbing_weather[key]['Wind']=str(int(min_wind))+"-"+str(int(max_wind))+" m/s"
    if (min_wind+max_wind)/2>5:
        climbing_weather[key]['Wind_style']='bold'
    climbing_weather[key]['Score'] = get_distance(key)
    climbing_weather[key]['Score']+=10*rain
    climbing_weather[key]['Score']+=20*(min_wind+max_wind)/2

climbing_day={}
for day in days_of_the_week:
    climbing_day[day]={}
    day_start_date, day_end_date = get_next_day(day,24)
    for key in climbing_locations.keys():
        location = climbing_locations[key]['location']
        min_temp, max_temp, rain, min_wind, max_wind = add_weather(location, day_start_date, day_end_date)
        climbing_day[day][key]={}
        if rain>3:
            climbing_day[day][key]['Rain_style']='bold'
        if (min_wind+max_wind)/2>5:
            climbing_day[day][key]['Wind_style']='bold'
        if (max_temp+min_temp)>50:
            climbing_day[day][key]['Temp_style']='bold'

with open('climbing-weather.json') as f:
    old_climbing_weather = json.load(f)

with open('climbing-weather.json', 'w') as f:
    json_pretty = json.dumps(climbing_weather, indent=2)
    f.write(json_pretty)

for key in climbing_locations.keys():
    rain = climbing_weather[key]['Rain']
    diff_rain = 0
    if key in old_climbing_weather.keys():
    	diff_rain = rain-old_climbing_weather[key]['Rain']
    str_diff_rain=str(diff_rain)
    if diff_rain>0:
        str_diff_rain = "+"+str_diff_rain
    climbing_weather[key]['Rain']=str(int(rain))+" mm ("+str_diff_rain+")"

test = sorted(climbing_weather.items(), key=lambda x: x[1]['Score'])
crag_score_sorted=[]
for i in range(len(test)):
    crag_score_sorted.append(test[i][0])

header_next_weekend = get_next_weekend_short()

HTML_DOC = """<!DOCTYPE html>
<html>
<head>
	<style type="text/css">
		.myTable { background-color:#eee;border-collapse:collapse; }
        .myTable tr:nth-child(2n) {background-color:#ccc;}
		.myTable td, .myTable th { padding:5px;border:1px solid #000; }
	</style>
	<title>Crag Weather</title>
    <script>
        function searchTable() {
            let table = document.getElementById('myTable2');
            let rows = table.getElementsByTagName('tr');
            let hideClosed = document.getElementById('hideClosedCheckbox').checked;

            for (let i = 1; i < rows.length; i++) {  // Start from 1 to skip the header
                let type = rows[i].getAttribute('type');
                let hideRow = false;

                // Check if any of the cells in the row contains the word "Closed"
                if (type != 'multipitch') {
                    hideRow = true;
                }
                rows[i].style.display = 'none';
                // If the checkbox is checked, hide rows containing "Closed"
                if (hideRow && hideClosed) {
                    rows[i].style.display = 'none';
                } else {
                    rows[i].style.display = '';
                }
            }
        }
    </script>
</head>
<body>
	<h1>Idemo penjati u """+crag_score_sorted[0]+"""!</h1>
    <p>
        Vikend """+header_next_weekend+"""
        <br>
        Azurirana na """+header_now_date_time+"""
        <br>
        Na temelju yr.no API
        <br>
        Ocjena = Distance + 10 x rain + 20 x avg wind
    </p>
    Prikazi samo dugi smjerovi <input type="checkbox" id="hideClosedCheckbox" onchange="searchTable()">
</body>
</html>
"""

soup = BeautifulSoup(HTML_DOC, "html.parser")

createTable()

html = soup.prettify("utf-8")
with open("build_outputs_folder/index.html", "wb") as file:
    file.write(html)

import generate_pollen_html

generate_pollen_html.generate_pollen_table()
