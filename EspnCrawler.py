import re
import urllib2
import datetime

from bs4 import BeautifulSoup

espn_urls = {"ncaa":"http://scores.espn.go.com/ncb/scoreboard?date=",
             "nba":"http://scores.espn.go.com/nba/scoreboard?date="}

def convert_to_seconds(timestamp):
    m,s = map(int,timestamp.split(":"))
    return 60*m+s

class Game(object):
    def __init__(self, team_0, team_1, date):
        self.date = date
        self.team_0 = team_0
        self.team_1 = team_1
        self.events = []
    
    def add_event(self, event):
        self.events.append(event)
    
    def toJSON(self):
        t0 = 0
        t1 = 0
        pt = 0
        ss = [[[0,0]],[[0,0]]]
        events = self.events
        for i in range(len(events)):
            j0 = 0
            j1 = 0
            #check to see which team
            if events[i][1][0] > t0:
                j0+=events[i][1][0]-t0
                if events[i][0] > pt:
                    pt = events[i][0]
                    ss[0].append([events[i][0],j0])
                    t0=events[i][1][0]
                    j0 = 0
            elif events[i][1][1] > t1:
                j1+=events[i][1][1]-t1
                if events[i][0] > pt:
                    pt = events[i][0]
                    ss[1].append([events[i][0],j1])
                    t1=events[i][1][1]
                    j1 = 0
        return {"date":self.date.isoformat(),"events":self.events,"team_a":self.team_0,
                "team_b":self.team_1,"score_series":ss,"a_score":t0,"b_score":t1}


class EspnScraper(object):
    """
    sport: nba or ncaa
    start_date: datetime date object
    
    Example usage:
        #create a scraper
        scraper = EspnScraper("nba")
    
        #download all pbp data and save them somewhere
        for g in scraper.get_games(datetime.date(2012,11,9)):
            #write to a database or file
    """
    
    def __init__(self, sport):
        self.sport = sport
        self.urls = []
    
    def get_games(self, start_date):
        urls = self.get_game_urls(self.sport, start_date)
        for g in self.get_game_data(urls):
            yield g
    
    def get_game_links(self, page):
        soup = BeautifulSoup(page)
        links = soup.find_all("a")
        self.urls = ["http://scores.espn.go.com"+l["href"] for l in links if l.text == u'Play\u2011By\u2011Play']

    def get_game_data(self):
        for i in range(0, len(self.urls), 2):
            d = self.urls[i]
            for url in self.urls[i+1]:
                page = urllib2.urlopen(url+"&period=0")
                game = self.get_game(page, d)
                game_id = re.search(r'[0-9]+$',url).group(0)
                yield game.toJSON()

    def get_game_urls(self, start_date):
        game_urls = []
        base_url = espn_urls[self.sport]
        delta = datetime.date.today() - start_date
        for i in range(delta.days + 1):
            url = base_url+start_date.__str__().replace("-","")
            games = get_game_links(urllib2.urlopen(url))
            if len(games) > 0:
                game_urls.extend([start_date,games])
            start_date+=datetime.timedelta(days=1)
        return game_urls
    
    def get_game(self, page, date):
        #make the soup
        soup = BeautifulSoup(page)

        #get the table
        table = soup.find("table","mod-data")

        #get the teams playing
        vals = [v for v in table.find("thead").find_all("th")]
        team_0 = vals[1].text
        team_1 = vals[3].text

        game = Game(team_0, team_1, date)
    
        if self.sport == "nba":
            #get real time events
            rows = [r for r in table.find_all("tr")]
            q = -1
            ptr = -1
            ot = 0
            for row in rows:
                entries = row.find_all("td")
                if len(entries) == 4:
                    #get the time data
                    tr = convert_to_seconds(entries[0].text)
                    if tr > ptr:
                        q+=1
                        if q > 3:
                            ot+=1
                    ptr = tr
                    if q < 4:
                        t = q*720 + 720-tr
                    else:
                        t = 2880 + ot*300-tr
                    event = [t,map(int,entries[2].text.split("-"))]
                    game.add_event(event)
        elif self.sport == "ncaa":
            #get real time events
            rows = [r for r in table.find_all("tr")]
            h = -1
            ptr = -1
            ot = 0
            for row in rows:
                entries = row.find_all("td")
                if len(entries) == 4:
                    #get the time data
                    tr = convert_to_seconds(entries[0].text)
                    if tr > ptr:
                        h+=1
                        if h > 2:
                            ot+=1
                    ptr = tr
                    if h < 2:
                        t = h*1200 + 1200-tr
                    else:
                        t = 2400 + ot*300-tr
                    event = [t,map(int,entries[2].text.split("-"))]
                    game.add_event(event)
        return game