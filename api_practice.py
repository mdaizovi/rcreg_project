#WORKS!
#https://www.brownpapertickets.com/api2/datelist?id=t3iip9rK2C&event_id=2304351
#ALSO WORKS!!!
#http://www.brownpapertickets.com/api2/eventlist?id=t3iip9rK2C&event_id=2304351
#ALSO WORKS!
#https://www.brownpapertickets.com/api2/pricelist?id=t3iip9rK2C&event_id=2304351&date_id=1330623

#officil python docs:
#https://docs.python.org/2.7/howto/urllib2.html

from rcreg_project.settings import BPT_Developer_ID
import urllib,urllib2
import xmltodict
import json

base_url='http://www.brownpapertickets.com/api2/'
rc2016='2304351'
BPT_CLient_ID='RollerCon'#I'm not sure if this is right
BPT_Producer_ID='7367'
d1={'id':BPT_Developer_ID}
d2={'id':BPT_Developer_ID, 'event_id':rc2016}
d3={'id':BPT_Developer_ID, 'event_id':rc2016, 'date_id':'1330623'}


def queryBPT(query, params):
    #query should be a string, like 'datelist'
    base_url='http://www.brownpapertickets.com/api2/'
    url_values = urllib.urlencode(params)
    #print "url_values ",url_values  # The order may differ.
    full_url = base_url + query+ '?' + url_values
    #print "full_url ",full_url
    r = urllib2.urlopen(full_url)
    return r

def getdatedict():
    r=queryBPT('datelist', d2)
    result = xmltodict.parse(r)
    date_dict=result['document']['date']
    return date_dict

def getdateid():
    #this only works because there's only one? or would it wok w/ many?
    r=queryBPT('datelist', d2)
    result = xmltodict.parse(r)
    date_id=result['document']['date']['date_id']
    return str(date_id)

def getpricedict():
    r=queryBPT('pricelist', d3)
    result = xmltodict.parse(r)
    price_dict=result['document']['price']
    return price_dict

def displaypricedict():
    '''Produces something like this:
    Price ID:  4337614
    Name:  Off Skates Convention Pass
    Live:  y
    Value:  49.00
    Service_fee:  2.71
'''
    price_order_dict=getpricedict()
    for l in price_order_dict:
        price_id=l['price_id']
        print "Price ID: ",price_id

        name=l['name']
        print "Name: ",name

        live=l['live']
        print "Live: ",live

        value=l['value']
        print "Value: ",value

        service_fee=l['service_fee']
        print "Service_fee: ",service_fee,"\n"

def display2():
        '''Produces something like this:
        price_id :  4337616
        live :  y
        name :  Skater Pass 18+
        value :  129.00
        service_fee :  5.51
        venue_fee :  0.00
        price_available :  50
    '''
    price_order_dict=getpricedict()
    for l in price_order_dict:
        for k,v in l.iteritems():
            print k,": ",v
        print "\n"

#result=queryBPT('pricelist', d3)
#print(json.dumps(xmltodict.parse(result), indent=4))

#NOTES
#this
#https://www.brownpapertickets.com/api2/datelist?id=t3iip9rK2C&event_id=2304351
#returns this
# <document>
# <result>success</result>
# <resultcode>000000</resultcode>
# <note/>
# <totaldates>1</totaldates>
# <date>
# <date_id>1330623</date_id>
# <live>y</live>
# <datestart>2016-07-27</datestart>
# <dateend>2016-07-31</dateend>
# <timestart>10:00</timestart>
# <timeend>21:00</timeend>
# <date_available>10000</date_available>
# </date>
# </document>


#and this: https://www.brownpapertickets.com/api2/pricelist?id=t3iip9rK2C&event_id=2304351&date_id=1330623
#returns this:
# <document>
# <result>success</result>
# <resultcode>000000</resultcode>
# <note/>
# <totalprices>7</totalprices>
# <price>
# <price_id>4337615</price_id>
# <live>y</live>
# <name>MVP Pass'+ SINGLE PASS</name>
# <value>169.00</value>
# <service_fee>6.91</service_fee>
# <venue_fee>0.00</venue_fee>
# <price_available>1</price_available>
# </price>
# <price>
# <price_id>4337648</price_id>
# <live>n</live>
# <name>MVP Pass 18+ (Group Rate)</name>
# <value>169.00</value>
# <service_fee>6.91</service_fee>
# <venue_fee>0.00</venue_fee>
# <price_available>0</price_available>
# </price>
# <price>
# <price_id>4337616</price_id>
# <live>y</live>
# <name>Skater Pass 18+</name>
# <value>129.00</value>
# <service_fee>5.51</service_fee>
# <venue_fee>0.00</venue_fee>
# <price_available>50</price_available>
# </price>
# <price>
# <price_id>4337613</price_id>
# <live>y</live>
# <name>Volunteer MVP Pass 18+</name>
# <value>99.00</value>
# <service_fee>4.46</service_fee>
# <venue_fee>0.00</venue_fee>
# <price_available>50</price_available>
# </price>
# <price>
# <price_id>4337612</price_id>
# <live>y</live>
# <name>Volunteer Skater Pass 18+</name>
# <value>89.00</value>
# <service_fee>4.11</service_fee>
# <venue_fee>0.00</venue_fee>
# <price_available>50</price_available>
# </price>
# <price>
# <price_id>4337614</price_id>
# <live>y</live>
# <name>Off Skates Convention Pass</name>
# <value>49.00</value>
# <service_fee>2.71</service_fee>
# <venue_fee>0.00</venue_fee>
# <price_available>50</price_available>
# </price>
# <price>
# <price_id>4337611</price_id>
# <live>y</live>
# <name>Volunteer Off Skates Convention Pass</name>
# <value>19.00</value>
# <service_fee>1.66</service_fee>
# <venue_fee>0.00</venue_fee>
# <price_available>50</price_available>
# </price>
# </document>
