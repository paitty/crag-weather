import json
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
import requests
import folium
import folium.plugins as plugins
import pandas as pd

def generate_pollen_table():
    def createPollenTable():
        new_table=soup.new_tag("table")
        new_table.attrs['class']='myTable'
        new_table.attrs['id']='myTable2'
        soup.html.body.append(new_table)
        display_table = soup.html.body.find_all("table")[-1]

        table_names=list(pollen_table.keys())
        table_names.insert(0,'date')
        table_names.insert(len(table_names),'sum')
        new_header = soup.new_tag("tr")
        display_table.append(new_header)
        for col in table_names:
            new_column_header = soup.new_tag("th")
            new_column_header.string=col
            display_table.tr.append(new_column_header)

        date_list=[]
        for tree in pollen_table.keys():
            date_list = date_list + list(set(pollen_table[tree].keys()) - set(date_list))

        date_num_list=[]
        for date in date_list:
            new_date = datetime.strptime(date, "%d/%m/%Y")
            new_date = new_date.strftime("%Y%m%d")
            date_num_list = date_num_list+[new_date]
        
        sorted_date_num_list=sorted(date_num_list)

        sorted_date_list=[]
        for date in sorted_date_num_list:
            new_date = datetime.strptime(date, "%Y%m%d")
            new_date = new_date.strftime("%d/%m/%Y")
            sorted_date_list = sorted_date_list+[new_date]   
        
        for date in sorted_date_list:
            new_line = soup.new_tag("tr")
            display_table.append(new_line)
            last_line=display_table.find_all("tr")[-1]
            for col in table_names:
                if col == "date":
                    new_tag=soup.new_tag('td')
                    new_tag.string=date
                elif col == "sum":
                    sum = 0
                    for tree in pollen_table.keys():
                        if date in pollen_table[tree].keys():
                            sum=sum+float(pollen_table[tree][date])
                    new_tag=soup.new_tag('td')
                    formatted_sum ="{:.1f}".format(sum)
                    new_tag.string=str(formatted_sum).replace(".",",")
                else:
                    new_tag=soup.new_tag('td')
                    if date in pollen_table[col].keys():
                        value = float(pollen_table[col][date])
                        if value<2.0:
                            new_tag['bgcolor']='green'
                        elif value < 6.0:
                            new_tag['bgcolor']='orange'
                        else:
                            new_tag['bgcolor']='red'
                        new_tag.string=pollen_table[col][date].replace(".",",")
                    else:
                        new_tag.string=""
                last_line.append(new_tag)
        
        new_line = soup.new_tag("tr")
        display_table.append(new_line)
        last_line=display_table.find_all("tr")[-1]
        for col in table_names:
            new_column_header = soup.new_tag("th")
            new_column_header.string=col
            last_line.append(new_column_header)

    def createPredictionTable(tree):
        new_table=soup.new_tag("table")
        new_table.attrs['class']='myTable'
        new_table.attrs['id']='myTable2'
        soup.html.body.append(new_table)
        display_table = soup.html.body.find_all("table")[-1]

        col_names = ['D','D+1','D+2']
        table_names=['date']+col_names

        new_header = soup.new_tag("tr")
        display_table.append(new_header)
        for col in table_names:
            new_column_header = soup.new_tag("th")
            new_column_header.string=col
            display_table.tr.append(new_column_header)

        date_list=prediction_table[tree].keys()
        
        for date in date_list:
            new_line = soup.new_tag("tr")
            display_table.append(new_line)
            last_line=display_table.find_all("tr")[-1]
            for col in table_names:
                if col == "date":
                    new_tag=soup.new_tag('td')
                    new_tag.string=date
                else:
                    new_tag=soup.new_tag('td')
                    new_tag.string=convert_level(prediction_table[tree][date][col_names.index(col)])
                last_line.append(new_tag)
    
    def convert_level(input):
        output = input
        if input == 'p-umjerena':
            output = 'Med'
        elif input == 'p-visoka':
            output = 'High'
        elif input == 'p-niska':
            output = 'Low'
        return output
    
    headers = {'Accept':	'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Encoding':	'gzip, deflate, br, zstd',
        'Accept-Language':	'en-US,fr;q=0.8,hr;q=0.5,en;q=0.3',
        'Connection':	'keep-alive',
        'DNT':	'1',
        'Priority':	'u=0, i',
        'Sec-Fetch-Dest':	'document',
        'Sec-Fetch-Mode':	'navigate',
        'Sec-Fetch-Site':	'none',
        'Sec-Fetch-User':	'?1',
        'Sec-GPC':	'1',
        'sitename': 'https://github.com/paitty/crag-weather.git',
        'Upgrade-Insecure-Requests':	'1',
        'User-Agent':	'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:135.0) Gecko/20100101 Firefox/135.0'}

    url = "https://www.plivazdravlje.hr/alergije/prognoza/1/zagreb.html"
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(r.content,"html.parser")

    # datetime object containing current date and time
    now = datetime.now()

    today_date = now.strftime("%d/%m/%Y")

    pollen_table={}
    prediction_table={}

    with open('pollen-table.json') as f:
        pollen_table = json.load(f)
    
    with open('pollen-prediction-table.json') as f:
        prediction_table = json.load(f)

    for soup3 in soup.find_all('div'):
        #print(soup3.get("class"))
        if soup3.get("class"):
            if soup3.get("class")[0] == "peludHolder":
                for soup2 in soup3.find_all('div'):
                    if soup2.get("class")[0] == "peludKategorija":
                        break
                for soup1 in soup3.find_all('span'):
                    if soup1.get("class"):
                        if soup1.get("class")[0] == "peludStupacOcitanje":
                            break
                if soup2.text.strip() not in pollen_table.keys():
                    pollen_table[soup2.text.strip()]={}
                pollen_table[soup2.text.strip()][today_date] = soup1.text.strip()
                #print(soup2.text.strip()+": "+soup1.text.strip())
                prediction = []
                for soup6 in soup3.find_all('embed'):
                    if soup6.get('src'):
                        if int(soup6.get('width'))>20:
                            prediction = prediction + [soup6.get('src').split('/')[5].split('.')[0]]
                if soup2.text.strip() not in prediction_table.keys():
                    prediction_table[soup2.text.strip()]={}
                prediction_table[soup2.text.strip()][today_date] = prediction
                #print(prediction)

    with open('pollen-table.json', 'w') as f:
        json_pretty = json.dumps(pollen_table, indent=2)
        f.write(json_pretty)

    with open('pollen-prediction-table.json', 'w') as f:
        json_pretty = json.dumps(prediction_table, indent=2)
        f.write(json_pretty)


    pass
    HTML_DOC = """<!DOCTYPE html>
    <html>
    <head>
        <style type="text/css">
            .myTable { background-color:#eee;border-collapse:collapse; }

            .myTable td, .myTable th { padding:5px;border:1px solid #000; }
        </style>
        <title>Pollen in Zagreb</title>
    </head>
    <body>
        <p>
            Na temelju <a href="https://www.plivazdravlje.hr/alergije/prognoza/1/zagreb.html"> Pliva</a>
            <br>
            <a href="pollen.html">Pollen table</a>
            <br>
            <a href="pollen_prediction.html">Pollen prediction table</a>
            <br>
            <a href="ambrozija_map.html">Ambrozija map</a>
        </p>
        <br>
    </body>
    </html>
    """

    soup = BeautifulSoup(HTML_DOC, "html.parser")

    createPollenTable()

    html = soup.prettify("utf-8")
    with open("build_outputs_folder/pollen.html", "wb") as file:
        file.write(html)
    
    soup = BeautifulSoup(HTML_DOC, "html.parser")

    day_names = ['Today', 'Tomorrow', 'Overmorrow']
    for i in range(3):
        tomorrow_string = day_names[i]+" - High: "
        for tree in prediction_table.keys():
            if today_date in prediction_table[tree].keys():
                if prediction_table[tree][today_date][i]=='p-visoka':
                    tomorrow_string=tomorrow_string+tree+' '
        
        tomorrow_string = tomorrow_string + '- Medium: '
        for tree in prediction_table.keys():
            if today_date in prediction_table[tree].keys():
                if prediction_table[tree][today_date][i]=='p-umjerena':
                    tomorrow_string=tomorrow_string+tree+' '

        tomorrow_string = tomorrow_string + '- Low: '
        for tree in prediction_table.keys():
            if today_date in prediction_table[tree].keys():
                if prediction_table[tree][today_date][i]=='p-niska':
                    tomorrow_string=tomorrow_string+tree+' '
        
        new_paragraph=soup.new_tag("p")
        new_paragraph.string=tomorrow_string
        soup.html.body.append(new_paragraph)

    for tree in prediction_table.keys():
        new_paragraph=soup.new_tag("p")
        new_paragraph.string=tree
        soup.html.body.append(new_paragraph)
        createPredictionTable(tree)

    html = soup.prettify("utf-8")
    with open("build_outputs_folder/pollen_prediction.html", "wb") as file:
        file.write(html)

    with open('pollen_locations.json') as f:
        pollen_locations = json.load(f)

    def get_lat_lon(city):      
        url='https://nominatim.openstreetmap.org/search?q='+city+'&format=jsonv2'
        r= requests.get(url, headers=headers)
        if r.json() == []:
            url='https://nominatim.openstreetmap.org/search.php?q='+city.split()[0]+'&format=jsonv2'
            r= requests.get(url, headers=headers)
        lat = r.json()[0]['lat']
        lon = r.json()[0]['lon']
        return lat, lon

    def check_pollen(location_number):
        #example call
        #https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=45.434&lon=15.188
        url = "https://www.plivazdravlje.hr/alergije/prognoza/"+str(location_number)
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(r.content,"html.parser")
        city = "nothing"
        pollen_value = "-"
        for soup3 in soup.find_all('div'):
            #print(soup3.get("class"))
            if soup3.get("class"):
                if soup3.get("class")[0] == "peludPrognozaNaslov1":
                    city = soup3.text.strip()
                if soup3.get("class")[0] == "peludHolder":
                    for soup2 in soup3.find_all('div'):
                        if soup2.get("class")[0] == "peludKategorija":
                            break
                    for soup1 in soup3.find_all('span'):
                        if soup1.get("class"):
                            if soup1.get("class")[0] == "peludStupacOcitanje":
                                break
                    if soup2.text.strip()== 'Ambrozija':
                        pollen_value = soup1.text.strip()
                        break
        print(city+": "+pollen_value)
        return city, pollen_value

    pollen_table = {}
    for i in range(1,25):
        city, value = check_pollen(i)
        if city != 'nothing':
            if city not in pollen_locations.keys():
                pollen_locations[city]={}
                lat, lon = get_lat_lon(city)
                pollen_locations[city]['location']=[lat, lon]
                pollen_locations[city]['number']=str(i)
            pollen_table[city]=value

    with open('pollen_locations.json', 'w') as f:
        json_pretty = json.dumps(pollen_locations, indent=2)
        f.write(json_pretty)

    def display_cities_on_map(html_filename):
        latitudes =[]
        longitudes =[]
        pollen_color = []
        pollen_value = []
        links = []
        for key in pollen_locations.keys():
            latitudes.append(str(pollen_locations[key]['location'][0])[:6])
            longitudes.append(str(pollen_locations[key]['location'][1])[:6])
            location_number = pollen_locations[key]['number']
            value = pollen_table[key]
            if value == '-':
                icon_color ="#6B6B6B" #grey
                pollen_value.append(value)
            else:
                value = float(value)
                if value<2.0:
                    icon_color ="#2C01D5" #blue 
                elif value < 6.0:
                    icon_color ="#FF7327" #orange 
                else:
                    icon_color ="#D60A0A" #red 
                pollen_value.append(min(9,int(value)))
            
            pollen_color.append(icon_color)

            Pliva_link = "https://www.plivazdravlje.hr/alergije/prognoza/"+str(location_number)
            link = '<a href="'+Pliva_link+'" target=”_blank”>'+key+'</a>'
            links.append(link)
        
        df = pd.DataFrame({'Pollen_Links':links,
                            'Latitude':latitudes,
                            'Longitude':longitudes,
                            'Pollen_Color':pollen_color,
                            'Pollen_Values': pollen_value})

        m = folium.Map(location=[44.67789272618172, 15.945964471005263], tiles="OpenStreetMap", zoom_start=7)

        for i in range(0,len(df)):
            point_location=[df.iloc[i]['Latitude'], df.iloc[i]['Longitude']]
            icon_color = df.iloc[i]['Pollen_Color']
            #print(df.iloc[i]['Properties'])
            folium.Marker(
            location=point_location,
            icon=plugins.BeautifyIcon(icon=df.iloc[i]['Pollen_Values'], icon_shape="marker", border_color=icon_color, text_color=icon_color),
            popup=df.iloc[i]['Pollen_Links'],
            ).add_to(m)
        m.save(html_filename)

    display_cities_on_map('build_outputs_folder/ambrozija_map.html')
if __name__ == "__main__":
    print("This is a different version of the module.py file.")
    generate_pollen_table()
