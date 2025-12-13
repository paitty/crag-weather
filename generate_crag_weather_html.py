import json
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
import requests
import folium
import pandas as pd
import folium.plugins as plugins

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
    if day=='Mon':
        day_num = 0
    if day=='Tue':
        day_num = 1
    if day=='Wed':
        day_num = 2
    if day=='Thu':
        day_num = 3
    if day=='Fri':
        day_num = 4
    if day=='Sat':
        day_num = 5
    if day=='Sun':
        day_num = 6
    d = datetime.now()
    t = timedelta((7 + day_num - d.weekday()) % 7)

    start = (d+t).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start+timedelta(hours=duration)
    return start, end

def days_of_week_from_today():
    # datetime object containing current date and time
    now = datetime.now()
    days_of_a_week = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
    days_of_the_week = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    for i in range(7):
        days_of_the_week[i] = days_of_a_week[(now.weekday()+i)%7]
    return days_of_the_week

def get_next_weekend_short():
    """
    @startdate: given date, in format '2013-05-25'
    @weekday: week day as a integer, between 0 (Monday) to 6 (Sunday)
    """
    d = datetime.now()
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
    if 'Distance' in locations[key].keys():
        distance=locations[key]['Distance']
    else:
        distance = get_duration(locations[key]['location'])
        locations[key]['Distance'] = distance
        with open(location_file, 'w') as f:
            json_pretty = json.dumps(locations, indent=2)
            f.write(json_pretty)
    return distance

def add_weather(location, start_date, end_date):

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

    #example call
    #https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=45.434&lon=15.188
    url = "https://api.met.no/weatherapi/locationforecast/2.0/compact?lat="+str(location[0])[:6]+"&lon="+str(location[1])[:6]
    r= requests.get(url, headers=headers)
    yr_weather=r.json()
    i=0
    min_temp = 100
    max_temp = -100
    rain = 0
    min_wind =100
    max_wind = -100

    while True:
        #TODO check if the datetime is our time
        datetime_object = datetime.fromisoformat(yr_weather['properties']['timeseries'][i]['time'])
        if datetime_object.replace(tzinfo=None)>=start_date:
            temperature = yr_weather['properties']['timeseries'][i]['data']['instant']['details']['air_temperature']
            wind = yr_weather['properties']['timeseries'][i]['data']['instant']['details']['wind_speed']
            if 'next_1_hours' in yr_weather['properties']['timeseries'][i]['data']:
                add_rain= yr_weather['properties']['timeseries'][i]['data']['next_1_hours']['details']['precipitation_amount']
            else:
                #TODO check if we dont miss anything like that
                add_rain= yr_weather['properties']['timeseries'][i]['data']['next_6_hours']['details']['precipitation_amount']
            #if location[0] == 44.30403029180178:
            #    print(datetime_object.replace(tzinfo=None))
            #    if 'next_1_hours' in yr_weather['properties']['timeseries'][i]['data']:
            #        print(yr_weather['properties']['timeseries'][i]['data']['next_1_hours']['details']['precipitation_amount'])
            #    else:
            #        #TODO check if we dont miss anything like that
            #        print(yr_weather['properties']['timeseries'][i]['data']['next_6_hours']['details']['precipitation_amount'])
            min_temp = min(min_temp, temperature)
            max_temp = max(max_temp, temperature)
            min_wind = min(min_wind, wind)
            max_wind = max(max_wind, wind)
            rain = rain + add_rain
        if datetime_object.replace(tzinfo=None)>=end_date:
            break
        i=i+1
    return min_temp, max_temp, rain, min_wind, max_wind

def add_snow(location):
    headers={'User-Agent': 'Mozilla/5.0'}
    
    url = 'https://www.bergfex.com/'+location.replace('(','').replace(')','').replace(' ','').lower()
    r= requests.get(url, headers=headers)
    print(r.text[:1000])
    soup = BeautifulSoup(r.text, "html.parser")
    
    snow_mountain=''
    snow_valley=''
    opening_status=''
    for snow_height_tag in soup.find_all("div", class_="tw-pl-4"):
        if snow_height_tag.h3.text == 'Snow depth':
            snow_mountain = snow_height_tag.div.find_all('span')[1].text
            snow_valley = snow_height_tag.div.find_all('span')[3].text

    for parent_div in soup.find_all('div', {'class': 'tw-flex tw-justify-start tw-items-center tw-gap-3'}):
        s= parent_div.contents[1]['x-bind']
        opening_status = s.split("'")[1]
        if opening_status == 'Closed':
            parent_div2 = parent_div.contents[3].find_all('div')
            parent_div3 = parent_div2[1].find_all('span')
            s= parent_div3[1].text
            opening_status = s.split(" - ")[0]
    
    #for opening in soup.find_all("div", class_="tw-flex tw-justify-start tw-items-center tw-gap-3"):    
    #   s= opening.div['x-bind']
    #   opening_status = s.split("'")[1]
    #   if opening_status not in ['Open']:
    #       opening_status = "closed"

    
    return snow_mountain, snow_valley, opening_status

def createTable():
    days_of_the_week = days_of_week_from_today()

    new_table=soup.new_tag("table")
    new_table.attrs['class']='myTable'
    new_table.attrs['id']='myTable2'
    soup.html.body.append(new_table)
    display_table = soup.html.body.find_all("table")[-1]

    if type_activity=='climbing':
        table_names=['Crag']+days_of_the_week+['Temp','Rain','Wind','Distance','Yr.no','Windy','plezanje.net','theCrag','Maps','Waze']
    elif type_activity=='skiing':
        table_names=['Crag']+days_of_the_week+['Temp','Rain','Wind','Snow_mountain','Snow_valley','Open','Distance','Yr.no','Windy','Bergfex','Maps','Waze']
    
    
    
    new_header = soup.new_tag("tr")
    display_table.append(new_header)
    for col in table_names:
        new_column_header = soup.new_tag("th")
        new_column_header.string=col
        display_table.tr.append(new_column_header)

    for key in sorted_by_score:
        new_line = soup.new_tag("tr")
        if 'type' in locations[key].keys():
            new_line.attrs['type']=locations[key]['type']
        display_table.append(new_line)
        last_line=display_table.find_all("tr")[-1]
        destination = 'location'
        if 'parking' in locations[key].keys():
            destination = 'parking'
        for col in table_names:
            new_tag=soup.new_tag('td')
            if col == 'Crag':
                new_tag.string=key
            elif col == 'Yr.no':
                new_link=soup.new_tag('a')
                new_link.string='Yr.no'
                new_link.attrs['href'] = 'https://www.yr.no/en/forecast/daily-table/'+str(locations[key]['location'][0])[:6]+", "+str(locations[key]['location'][1])[:6]
                new_link.attrs['target'] = '_blank'
                new_tag.append(new_link)
            elif col == 'Windy':
                new_link=soup.new_tag('a')
                new_link.string='Windy'
                new_link.attrs['href'] = 'https://www.windy.com/'+str(locations[key]['location'][0])[:6]+"/"+str(locations[key]['location'][1])[:6]
                new_link.attrs['target'] = '_blank'
                new_tag.append(new_link)
            elif col == 'plezanje.net':
                new_link=soup.new_tag('a')
                new_link.string='plezanje.net'
                new_link.attrs['href'] = 'https://plezanje.net/plezalisce/'+key.replace('(','').replace(')','').replace(' ','-').lower()
                new_link.attrs['target'] = '_blank'
                new_tag.append(new_link)
            elif col == 'Bergfex':
                new_link=soup.new_tag('a')
                new_link.string='bergfex'
                new_link.attrs['href'] = 'https://www.bergfex.com/'+key.replace('(','').replace(')','').replace(' ','').lower()
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
                new_link.attrs['href'] = 'https://www.google.com/maps/place/'+str(locations[key][destination][0])[:6]+","+str(locations[key][destination][1])[:6]
                new_link.attrs['target'] = '_blank'
                new_tag.append(new_link)
            elif col == 'Waze':
                new_link=soup.new_tag('a')
                new_link.string='Waze'
                new_link.attrs['href'] = 'waze://?ll='+str(locations[key][destination][0])[:6]+","+str(locations[key][destination][1])[:6]
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
                if 'Temp_style' in climbing_day_style[col][key].keys():
                    new_img.attrs['src'] = 'hot.PNG'                  
                if 'Wind_style' in climbing_day_style[col][key].keys():
                    new_img.attrs['src'] = 'wind-leaf.png'                  
                if 'Rain_style' in climbing_day_style[col][key].keys():
                    new_img.attrs['src'] = 'cloud-with-rain.png'
                if 'Snow_style' in climbing_day_style[col][key].keys():
                    new_img.attrs['src'] = 'snowflake.png'
                if col in ['Sat','Sun']:
                    new_tag.attrs['style']="background-color:#bbb;"
                new_tag.append(new_img)
            else:
                if col+'_style' in weather[key].keys():
                    new_tag.attrs['style']="font-weight:bold"
                new_tag.string=str(weather[key][col])
            last_line.append(new_tag)

def create_weather():
    start_date, end_date =  get_next_day('Sat',48)
    weather = {}
    
    for key in locations.keys():
        location = locations[key]['location']
        min_temp, max_temp, rain, min_wind, max_wind = add_weather(location, start_date, end_date)
        snow_mountain, snow_valley, open = add_snow(key)
        weather[key]={}
        weather[key]['Temp']=str(int(min_temp))+"/"+str(int(max_temp))+"°"
        weather[key]['Rain']=str(int(rain))+" mm"
        weather[key]['Snow_mountain']=snow_mountain
        weather[key]['Snow_valley']=snow_valley
        weather[key]['Open']=open
        if rain>6:
            weather[key]['Rain_style']='bold'
        weather[key]['Wind']=str(int(min_wind))+"-"+str(int(max_wind))+" m/s"
        if (min_wind+max_wind)/2>5:
            weather[key]['Wind_style']='bold'
        if (min_temp+max_temp)>50:
            weather[key]['Temp_style']='bold'
        weather[key]['Score'] = get_distance(key)
        weather[key]['Score']+=10*rain
        weather[key]['Score']+=20*(min_wind+max_wind)/2
    return weather

def create_day_style():
    climbing_day_style = {}
    for day in days_of_week_from_today():
        climbing_day_style[day]={}
        day_start_date, day_end_date = get_next_day(day,24)
        for key in locations.keys():
            location = locations[key]['location']
            min_temp, max_temp, rain, min_wind, max_wind = add_weather(location, day_start_date, day_end_date)
            climbing_day_style[day][key]={}
            if rain>3:
                climbing_day_style[day][key]['Rain_style']='bold'
            if (min_wind+max_wind)/2>5:
                climbing_day_style[day][key]['Wind_style']='bold'
            if (max_temp+min_temp)>50:
                climbing_day_style[day][key]['Temp_style']='bold'
            if max_temp<2 and rain>3:
                climbing_day_style[day][key]['Snow_style']='bold'
    return climbing_day_style

def add_diff_in_weather():
    #get old climbing weather
    with open(type_activity+'-weather.json') as f:
        old_weather = json.load(f)

    #store new climbing weather to become old climbing weather next time
    with open(type_activity+'-weather.json', 'w') as f:
        json_pretty = json.dumps(weather, indent=2)
        f.write(json_pretty)

    #compute rain difference between old and new climbing weather
    for key in locations.keys():
        rain = int(weather[key]['Rain'][:-3])
        diff_rain = 0
        str_diff_rain = "0"
        if key in old_weather.keys():
            diff_rain = rain-int(old_weather[key]['Rain'][:-3])
        str_diff_rain=str(diff_rain)
        if diff_rain>0:
            str_diff_rain = "+"+str_diff_rain
        weather[key]['Rain']=str(int(rain))+" mm ("+str_diff_rain+")"

def sort_by_score():
    test = sorted(weather.items(), key=lambda x: x[1]['Score'])
    sorted_by_score=[]
    for i in range(len(test)):
        sorted_by_score.append(test[i][0])
    return sorted_by_score

def add_categorical_legend(folium_map, title, colors, labels):
    if len(colors) != len(labels):
        raise ValueError("colors and labels must have the same length.")

    color_by_label = dict(zip(labels, colors))
    
    legend_categories = ""     
    for label, color in color_by_label.items():
        legend_categories += f"<li><span style='background:{color}'></span>{label}</li>"
        
    legend_html = f"""
    <div id='maplegend' class='maplegend'>
      <div class='legend-title'>{title}</div>
      <div class='legend-scale'>
        <ul class='legend-labels'>
        {legend_categories}
        </ul>
      </div>
    </div>
    """
    script = f"""
        <script type="text/javascript">
        var oneTimeExecution = (function() {{
                    var executed = false;
                    return function() {{
                        if (!executed) {{
                             var checkExist = setInterval(function() {{
                                       if ((document.getElementsByClassName('leaflet-top leaflet-right').length) || (!executed)) {{
                                          document.getElementsByClassName('leaflet-top leaflet-right')[0].style.display = "flex"
                                          document.getElementsByClassName('leaflet-top leaflet-right')[0].style.flexDirection = "column"
                                          document.getElementsByClassName('leaflet-top leaflet-right')[0].innerHTML += `{legend_html}`;
                                          clearInterval(checkExist);
                                          executed = true;
                                       }}
                                    }}, 100);
                        }}
                    }};
                }})();
        oneTimeExecution()
        </script>
      """
   

    css = """

    <style type='text/css'>
      .maplegend {
        z-index:9999;
        float:right;
        background-color: rgba(255, 255, 255, 1);
        border-radius: 5px;
        border: 2px solid #bbb;
        padding: 10px;
        font-size:12px;
        positon: relative;
      }
      .maplegend .legend-title {
        text-align: left;
        margin-bottom: 5px;
        font-weight: bold;
        font-size: 90%;
        }
      .maplegend .legend-scale ul {
        margin: 0;
        margin-bottom: 5px;
        padding: 0;
        float: left;
        list-style: none;
        }
      .maplegend .legend-scale ul li {
        font-size: 80%;
        list-style: none;
        margin-left: 0;
        line-height: 18px;
        margin-bottom: 2px;
        }
      .maplegend ul.legend-labels li span {
        display: block;
        float: left;
        height: 16px;
        width: 30px;
        margin-right: 5px;
        margin-left: 0;
        border: 0px solid #ccc;
        }
      .maplegend .legend-source {
        font-size: 80%;
        color: #777;
        clear: both;
        }
      .maplegend a {
        color: #777;
        }
    </style>
    """

    folium_map.get_root().header.add_child(folium.Element(script + css))

    return folium_map

def display_cities_on_map(html_filename):

    #headers={'User-Agent': 'Mozilla/5.0'}

    latitudes =[]
    longitudes =[]
    weather_color = []
    links = []
    for key in locations.keys():
        latitudes.append(str(locations[key]['location'][0])[:6])
        longitudes.append(str(locations[key]['location'][1])[:6])
        icon_color ="#004506" #green
        if 'Temp_style' in weather[key].keys():
            icon_color ="#D60A0A" #red               
        if 'Wind_style' in weather[key].keys():
            icon_color ="#525252" #grey                 
        if 'Rain_style' in weather[key].keys():
            icon_color ="#0D00C8" #blue
        weather_color.append(icon_color)
        yr_link = 'https://www.yr.no/en/forecast/daily-table/'+str(locations[key]['location'][0])[:6]+", "+str(locations[key]['location'][1])[:6]
        link = '<a href="'+yr_link+'" target=”_blank”>'+key+'</a>'
        links.append(link)
    
    df = pd.DataFrame({'Properties':links,
                        'Latitude':latitudes,
                        'Longitude':longitudes,
                        'Weather':weather_color})

    if type_activity=='climbing':
        center = [45.37789272618172, 15.445964471005263]
    elif type_activity=='skiing':
        center = [46.53811886433177, 14.907210304159063]
    
    m = folium.Map(location=center, tiles="OpenStreetMap", zoom_start=7)

    for i in range(0,len(df)):
        point_location=[df.iloc[i]['Latitude'], df.iloc[i]['Longitude']]
        icon_color = df.iloc[i]['Weather']
        #print(df.iloc[i]['Properties'])
        folium.Marker(
        location=point_location,
        icon=plugins.BeautifyIcon(icon="arrow-down", icon_shape="marker", border_color=icon_color, text_color=icon_color),
        popup=df.iloc[i]['Properties'],
        ).add_to(m)
    
    #add legend
    #m = add_categorical_legend(m, 'Distance to Rovinj:',
    #                         colors = ['#004506',"#D60A0A","#525252", "#0D00C8"],
    #                       labels = ['All good', 'Hot', 'Windy', 'Rainy'])
    m.save(html_filename)

type_activity = 'skiing'
#type_activity = 'climbing'

for type_activity in ['skiing', 'climbing']:

    location_file = type_activity+'-locations.json'

    with open(location_file) as f:
        locations = json.load(f)
    
    weather = create_weather()

    climbing_day_style = create_day_style()

    #add_diff_in_weather()

    sorted_by_score = sort_by_score()

    # dd/mm/YY H:M:S
    now2 = datetime.now() + timedelta(hours=2)
    header_now_date_time = now2.strftime("%d/%m/%Y %H:%M:%S")
    header_next_weekend = get_next_weekend_short()

    HTML_header = f"""<!DOCTYPE html>
    <html>
    <head>
        <style type="text/css">
            .myTable {{ background-color:#eee;border-collapse:collapse; }}
            .myTable tr:nth-child(2n) {{background-color:#ccc;}}
            .myTable td, .myTable th {{ padding:5px;border:1px solid #000; }}
        </style>
        <title>{type_activity.capitalize()} Weather</title>
        <script>
            function searchTable() {{
                let table = document.getElementById('myTable2');
                let rows = table.getElementsByTagName('tr');
                let hideClosed = document.getElementById('hideClosedCheckbox').checked;

                for (let i = 1; i < rows.length; i++) {{  // Start from 1 to skip the header
                    let type = rows[i].getAttribute('type');
                    let hideRow = false;

                    // Check if any of the cells in the row contains the word "Closed"
                    if (type != 'multipitch') {{
                        hideRow = true;
                    }}
                    rows[i].style.display = 'none';
                    // If the checkbox is checked, hide rows containing "Closed"
                    if (hideRow && hideClosed) {{
                        rows[i].style.display = 'none';
                    }} else {{
                        rows[i].style.display = '';
                    }}
                }}
            }}
        </script>
    </head>
    <body>
        <h1>Let's go {type_activity} in {sorted_by_score[0]}!</h1>
        <p>
            Weekend {header_next_weekend}
            <br>
            Updated on {header_now_date_time}
            <br>
            Based on yr.no API
            <br>
            Score = Distance + 10 x rain + 20 x avg wind
        </p>
        Show only multi-pitch routes <input type="checkbox" id="hideClosedCheckbox" onchange="searchTable()">
    </body>
    </html>
    """

    soup = BeautifulSoup(HTML_header, "html.parser")

    createTable()

    HTML_footer = """   <br> <div class="container">
    <iframe id="iframe1" name="iframe1" frameborder="0"  
        src=" """+type_activity+"""_detail_footprint.html" width="800" height="500"></iframe>
        </div>  """

    soup_footer = BeautifulSoup(HTML_footer, "html.parser")

    soup.body.append(soup_footer)

    html = soup.prettify("utf-8")
    if type_activity=='climbing':
        with open("build_outputs_folder/index.html", "wb") as file:
            file.write(html)
    else:
        with open("build_outputs_folder/"+type_activity+"_index.html", "wb") as file:
            file.write(html)

    display_cities_on_map('build_outputs_folder/'+type_activity+'_detail_footprint.html')

import generate_pollen_html

generate_pollen_html.generate_pollen_table()
