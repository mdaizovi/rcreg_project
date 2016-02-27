from scheduler.models import Venue, Location, Roster, Challenge, Training, Coach
from con_event.models import Country, State, Con, Registrant, Blog
from django.contrib.auth.models import Group, User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
import csv
import os
import datetime
from rcreg_project.settings import BASE_DIR
from rcreg_project.extras import remove_punct,ascii_only,ascii_only_no_punct
import openpyxl
import collections

static_path=BASE_DIR+"/static/data/"
import_path=static_path+'unformatted/'
export_path=static_path+'exported/'

data_columns=['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X',
    'Y','Z','AA','AB','AC','AD','AE','AF','AG','AH','AI','AJ','AK','AL','AM','AN']

def wb_or_str(xlfile):
    """cehcks is xlfile input is a strong of name, or wb object. either makes or returns object."""
    if isinstance(xlfile , basestring):
        #if a string of file name is entered
        wb = openpyxl.load_workbook(xlfile)
    else:
        # if a wb object is entered
        wb = xlfile
    return wb

#xlfile=(static_path+'myheader.xlsx')
#xlfile=(static_path+'BPTheader.xlsx')
def get_header(xlfile):
    wb=wb_or_str(xlfile)
    sheet = wb.get_active_sheet()
    #sheet=wb.get_sheet_by_name('downloadreports-1')#this only works for RollerTron.xlsx
    header=collections.OrderedDict()
    for row in range(1, sheet.get_highest_row() + 1):
        for  c in data_columns:#global vairable, look at top of file
            location=c+str(row)
            data=sheet[location].value
            header[c]=data
    return header

def write_wb(target_location,target_name,od_list,header):
    """od_list is a list of ordered dicts, w/ k being target column in an excel sheet (A, B, etc) and v being the value,
    Each od represents 1 row."""

    wb = openpyxl.Workbook()
    sheet = wb.get_active_sheet()
    r=int(1)
    for od in od_list:
        while r<2:#write the header
            for k,v in header.items():
                location=str(k)+str(r)
                sheet[location].value = v
            r+=int(1)

        for k,v in od.items():
            location=str(k)+str(r)
            sheet[location].value = v
        r+=int(1)
    wb.save(target_location+target_name)
    return wb

def make_excel_odict_list(xlfile):
    """Takes in excel file of BPT registrant data, turns each row into an ordered dict, returns list of all ordered dicts"""
    wb=wb_or_str(xlfile)
    sheet = wb.get_active_sheet()
    #sheet=wb.get_sheet_by_name('downloadreports-1')#this only works for RollerTron.xlsx
    all_data=[]
    highest_row=sheet.get_highest_row()
    for row in range(2, sheet.get_highest_row() + 1):
        data_holding_dict = collections.OrderedDict()
        for  c in data_columns:
            location=c+str(row)
            data=sheet[location].value
            data_holding_dict[c]=data
        all_data.append(data_holding_dict)
    #so by now all_data has a shit ton of stuff
    return all_data

#xlfile=(export_path+'SingleEmailRegistrants.xlsx')
def find_incompletes(xlfile):
    """this assumes BPT header, not my header"""
    all_data=make_excel_odict_list(xlfile)
    no_sk8name=[]
    no_real_name=[]
    complete_entries=[]

    for od in all_data:
        sk8name=od.get("AC")
        first_name=od.get("AA")
        last_name=od.get("Z")

        if not sk8name:
            no_sk8name.append(od)
        if not first_name or not last_name:
            no_real_name.append(od)
        if sk8name and first_name and last_name:
            complete_entries.append(od)

    header=get_header((static_path+'BPTheader.xlsx'))
    date_str=datetime.date.today().strftime("%B %d %Y")#eg 'July 23 2010'

    if len(no_sk8name)>0:
        name_str='NoSk8NameReg '+ date_str +'.xlsx'
        no_sk8name_file=write_wb(export_path,name_str,no_sk8name,header)
    else:
        no_sk8name_file=None

    if len(no_real_name)>0:
        name_str='NoRealNameReg '+ date_str +'.xlsx'
        no_real_name_file=write_wb(export_path,name_str,no_real_name,header)
    else:
        no_real_name_file=None

    if len(complete_entries)>0:
        name_str='CompleteReg '+ date_str +'.xlsx'
        complete_entries_file=write_wb(export_path,name_str,complete_entries,header)
    else:
        complete_entries_file=None

    return no_sk8name_file,no_real_name_file,complete_entries_file


#xlfile=(import_path+"RollerTron.xlsx")
def email_dupes(xlfile):
    """Takes in list of ordered dicts from BPT Excel sheet, shits out 2 excels: 1 of people who entered unique emails,
    1 of peolpe who are attached to an email that is used more than once."""
    all_data=make_excel_odict_list(xlfile)
    email_list=[]
    last_email=None
    good_emails=[]
    bad_emails=[]

    for od in all_data:
        email2=od.get("AB")
        email_list.append(email2)

    for od in all_data:
        email2=od.get("AB")
        if int(email_list.count(email2))>1:
            bad_emails.append(od)
        else:
            good_emails.append(od)

    header=get_header((static_path+'BPTheader.xlsx'))
    date_str=datetime.date.today().strftime("%B %d %Y")#eg 'July 23 2010'
    if len(good_emails)>0:
        name_str='SingleEmailRegistrants '+ date_str +'.xlsx'
        single_file=write_wb(export_path,name_str,good_emails,header)
    else:
        single_file=None

    if len(bad_emails)>0:
        name_str='EmailDupeRegistrants '+ date_str +'.xlsx'
        dupe_file=write_wb(export_path,name_str,bad_emails,header)
    else:
        dupe_file=None

    return single_file,dupe_file

#target_file=(export_path+"RollerTron.xlsx")
#target_file=(import_path+'RollerTron Attendee @ 022316 copy.xlsx')
#target_file=(import_path+'RespondersNOTINDB.xlsx')
#single_file, dupe_file, no_sk8name_file, no_real_name_file, complete_entries_file=sort_BPT_excel(target_file)
def sort_BPT_excel(target_file):
    """aggregates the cleaner funcitons, so i can enter the big BPT excel and shit out: good/bad emails, 2 incomplete name files, 1 complete name file"""
    BPT_header = get_header((static_path+'BPTheader.xlsx'))
    single_file,dupe_file=email_dupes(target_file)

    no_sk8name_file,no_real_name_file,complete_entries_file=find_incompletes(single_file)

    return single_file, dupe_file, no_sk8name_file, no_real_name_file, complete_entries_file



#con=Con.objects.get(year="2016")
#complete_entries_filee=(export_path+'SingleEmailRegistrants.xlsx')
#complete_entries_file=(export_path+'RegistrantFAIL copy.xlsx')
#complete_entries_file=(import_path+'RollerTron Attendee @ 022316 copy.xlsx')
complete_entries_file=(import_path+'TEST.xlsx')
def import_from_excel(complete_entries_file,con):
    """This assumes that I've already checked for duplicate emails and lack of name, sk8name.
    This is data that could be ready for import via Django import/export, but I think this will be faster.
    This is coming from BPT format, not mine"""
    all_data=make_excel_odict_list(complete_entries_file)
    error_list=[]
    success_list=[]
    repeat_email_list=[]
    for od in all_data:
        skill=od.get("AF")
        gender=od.get("AG")
        pass_type=od.get("V")
        email=od.get("AB")
        if not email:
            email=od.get("Q")
        first_name =od.get("AA")
        if not first_name:
            first_name =od.get("I")
        last_name = od.get("Z")
        if not last_name:
            last_name = od.get("H")
        sk8name = od.get("AC")
        sk8number =str(od.get("AE"))
        country_name = od.get("O")
        state_name=od.get("M")
        BPT_Ticket_ID=od.get("A")

        affiliation=od.get("AH")
        ins_carrier=od.get("AI")
        ins_number=od.get("AJ")
        age_group=od.get("AK")
        favorite_part=od.get("AM")
        volunteer=od.get("AL")
        for att in [first_name,last_name,sk8name,sk8number,affiliation,ins_carrier,ins_number,favorite_part,volunteer]:
            cleaned_att=ascii_only_no_punct(att)
            str_att=str(cleaned_att)
            if len(str_att)>100:
                att=str_att[:100]

        if country_name:
            try:
                country=Country.objects.get(name__iexact=country_name)
            except:
                country=None
        else:
            country=None

        if state_name:
            try:
                state=State.objects.get(slugname=state_name)
            except:
                state=None
        else:
            state=None

        try:#this is the overarching try, any failure will send to error_list
            this_reg=None
            try:#stating with most matches, broadening, until i'm sure it doesn't exist
                this_reg=Registrant.objects.get(con=con, email=email,first_name=first_name,last_name=last_name,sk8name=sk8name)
                print "found %s, first try"%(this_reg)
            except ObjectDoesNotExist:
                #first try: con and email match, and EITHER f/l name or ska8name
                reg_q=Registrant.objects.filter(con=con, email=email).filter(Q(first_name__iexact=first_name,last_name__iexact=last_name)|Q(sk8name__iexact=sk8name))
                if reg_q.count()==1:
                    this_reg=reg_q[0]
                    print "found %s, second try"%(this_reg)
                else:#allow for same person, different email
                    reg_q=Registrant.objects.filter(con=con).filter(Q(first_name__iexact=first_name,last_name__iexact=last_name)|Q(sk8name__iexact=sk8name))
                    if reg_q.count()==1:
                        this_reg=reg_q[0]
                        print "found %s, third try w/ diff email"%(this_reg)
                    else:
                        try:
                            Registrant.objects.get(con=con, email=email)
                            print "email exists"
                            repeat_email_list.append(od)
                        except ObjectDoesNotExist:
                            #here's where I think doesn't exist, make a new One . if repeat email, will fail upon save
                            print "think doesn't exist"
                            this_reg=Registrant(con=con, email=email,first_name=first_name,last_name=last_name)

            if this_reg:#ie if no repeat email
                attr_dict={'sk8name':sk8name,'sk8number':sk8number,'skill':skill,"gender":gender,'pass_type':pass_type,'first_name':first_name,'last_name':last_name,
                    'country':country,'state':state,'BPT_Ticket_ID':BPT_Ticket_ID,'affiliation':affiliation,'ins_carrier':ins_carrier,'ins_number':ins_number,'age_group':age_group,
                    'favorite_part':favorite_part,'volunteer':volunteer}
                for k,v in attr_dict.iteritems():
                    print k," is ",v
                    value = getattr(this_reg, k)
                    #Notice this only adds data that doesn't exist, it doesn't overwrite existing db data
                    #I could make update by saying if old != new, if i wanted. dob't know if i want.
                    if v and not value:
                        print "setting ",this_reg,"s ",k
                        setattr(this_reg, k, v)
                    elif not v:
                        print "od doesn't have ",k
                    elif value:
                        print this_reg,"already has a ",k,": ",value

                this_reg.save()
                this_reg.save()#think I have to do twice tomake user? I forgot.
                success_list.append(od)
                print this_reg," Succesfully made"
        except:
            print "Fail: "
            error_list.append(od)
            print this_reg


    header=get_header((static_path+'BPTheader.xlsx'))
    date_str=datetime.date.today().strftime("%B %d %Y")#eg 'July 23 2010'

    if success_list:
        name_str='RegistrantsMade '+ date_str +'.xlsx'
        write_wb(export_path,name_str,success_list,header)
        print "success list written"
    if error_list:
        name_str='RegistrantFAIL '+ date_str +'.xlsx'
        write_wb(export_path,name_str,error_list,header)
        print "error list written"
    if repeat_email_list:
        name_str='RegistrantREPEATEMAILFAIL '+ date_str +'.xlsx'
        write_wb(export_path,name_str,repeat_email_list,header)
        print "repeat_email_list written"


########none of this should work anymore, i removed the csv files
#also, should be unnecessary, now that db is live and i can't just dump it all the time
# def make_countries():
#     csvfile=(static_path+"All countries.csv")
#
#     with open(csvfile) as file1:
#         data = csv.reader(file1, delimiter=',')
#         rownumber=0
#         countryinfo=[]
#         errorlist=[]
#         for row in data:
#             rownumber = rownumber +1
#             if rownumber >= 2:
#                 countryinfo.append(row)
#
#     for datalist in countryinfo:
#         try:
#             slugname=datalist[0]
#             name=datalist[1]
#             county, created=Country.objects.get_or_create(name=name, slugname=slugname)
#             print "%s (%s) made successfully" % (country.name, country.slugname)
#         except:
#             errorlist.append(datalist)
#
#     if errorlist:
#         f=open(export_path+"Country Errors.csv", "wb")
#         writer = csv.writer(f, delimiter=',', quoting=csv.QUOTE_ALL)
#         for error in errorlist:
#             writer.writerow(error)
#
#         f.close()
#
# def make_states():
#     csvfile=(static_path+"statesall.csv")
#
#     with open(csvfile) as file1:
#         data = csv.reader(file1, delimiter=',')
#         rownumber=0
#         stateinfo=[]
#         errorlist=[]
#         for row in data:
#             rownumber = rownumber +1
#             if rownumber >= 2:
#                 stateinfo.append(row)
#
#     for datalist in stateinfo:
#         try:
#             slugname=datalist[0]
#             name=datalist[1]
#             country_name=datalist[2]
#             try:
#                 country=Country.objects.get(name=country_name)
#             except:
#                 country=Country.objects.get(name="United States")
#
#             state, created=State.objects.get_or_create(name=name, slugname=slugname, country=country)
#             print "5"
#             state.save()
#             print "%s %s (%s) made successfully" % (state.name, state.slugname, state.country)
#         except:
#             errorlist.append(datalist)
#
#     if errorlist:
#         f=open(export_path+"State Errors.csv", "wb")
#         writer = csv.writer(f, delimiter=',', quoting=csv.QUOTE_ALL)
#         for error in errorlist:
#             writer.writerow(error)
#         f.close()
#
# def make_rcs():
#     rc1, created1=Con.objects.get_or_create(start=datetime.date(2015, 07, 22),end=datetime.date(2015, 07, 26))
#     rc2, created2=Con.objects.get_or_create(BPT_event_id='2304351',start=datetime.date(2016, 07, 27),end=datetime.date(2016, 07, 31))
#     rc2.save()
#     rc3, created3=Con.objects.get_or_create(start=datetime.date(2017, 07, 26),end=datetime.date(2017, 07, 30))
#     for r in [rc1,rc2,rc3]:
#         r.ticket_link="http://rollercon.com/register/rollercon-pass/"
#         r.hotel_book_link="http://rollercon.com/register/hotel-reservations/"
#         r.save()
#
#
# def venue_setup():
#     venue, created=Venue.objects.get_or_create(name="The Westgate Resort & Convention Center")
#     l1, created1=Location.objects.get_or_create(venue=venue,location_type='Seminar Room',name="RC Classroom 231")
#     l2, created2=Location.objects.get_or_create(venue=venue,location_type='Seminar Room',name="RC Classroom 233")
#     l3, created3=Location.objects.get_or_create(venue=venue,location_type='Seminar Room',name="RC Classroom 235")
#     l4, created4=Location.objects.get_or_create(venue=venue,location_type='Flat Track',name="RC MVP-1 Training Track One")
#     l5, created5=Location.objects.get_or_create(venue=venue,location_type='Flat Track',name="RC MVP-2 Training Track Two")
#     l6, created6=Location.objects.get_or_create(venue=venue,location_type='Flat Track',name="RC MVP-3 Training Track Three")
#     l7, created7=Location.objects.get_or_create(venue=venue,location_type='Flat Track',name="RC MVP-4 Training Track Four")
#     l8, created8=Location.objects.get_or_create(venue=venue,location_type='Flat Track',name="RC MVP-5 Training Track Five")
#     l9, created9=Location.objects.get_or_create(venue=venue,location_type='Banked Track',name="RC-BT Banked Track")
#     l10, created10=Location.objects.get_or_create(venue=venue,location_type='Flat Track',name="RC-C1 Competition Track One")
#     l11, created11=Location.objects.get_or_create(venue=venue,location_type='Flat Track',name="RC-C2 Competition Track Two")
#     l12, created12=Location.objects.get_or_create(venue=venue,location_type='Flat Track',name="RC-C3 Scrimmage Track")
#
# def make_registrants():
#     con1=Con.objects.get(pk=1)
#     con2=Con.objects.get(pk=2)
#     password="@$$p3nn13$"
#     r1, created1=Registrant.objects.get_or_create(con=con1, pass_type="MVP", gender="Female", skill="B", email="mdaizovi@gmail.com",first_name="Michela",last_name="Dai Zovi", sk8name="Dahmernatrix",sk8number="505", country=Country.objects.get(name="Thailand"))
#     r2, created2=Registrant.objects.get_or_create(con=con1, pass_type="MVP", gender="Female", skill="A", email="denise.grimes@gmail.com",first_name="Denise",last_name="Grimes", sk8name="Ivanna S. Pankin",sk8number="22", country=Country.objects.get(name="United States"))
#     r3, created3=Registrant.objects.get_or_create(con=con1, pass_type="MVP", gender="Female", skill="A", email="derbydish99@gmail.com",first_name="Patricia",last_name="Ethier", sk8name="Trish the Dish",sk8number="99", country=Country.objects.get(name="United States"))
#     r4, created4=Registrant.objects.get_or_create(con=con1, pass_type="MVP", gender="Female", skill="B", email="coordinator@rollercon.com",first_name="Angela",last_name="Parrill", sk8name="Leggs'n Bacon",sk8number="11", country=Country.objects.get(name="United States"))
#
#     r5, created1=Registrant.objects.get_or_create(con=con2, pass_type="MVP", gender="Female", skill="B", email="mdaizovi@gmail.com",first_name="Michela",last_name="Dai Zovi", sk8name="Dahmernatrix",sk8number="505", country=Country.objects.get(name="Thailand"))
#     r6, created2=Registrant.objects.get_or_create(con=con2, pass_type="MVP", gender="Female", skill="A", email="denise.grimes@gmail.com",first_name="Denise",last_name="Grimes", sk8name="Ivanna S. Pankin",sk8number="22", country=Country.objects.get(name="United States"))
#     r7, created3=Registrant.objects.get_or_create(con=con2, pass_type="MVP", gender="Female", skill="A", email="derbydish99@gmail.com",first_name="Patricia",last_name="Ethier", sk8name="Trish the Dish",sk8number="99", country=Country.objects.get(name="United States"))
#     r8, created4=Registrant.objects.get_or_create(con=con2, pass_type="MVP", gender="Female", skill="B", email="coordinator@rollercon.com",first_name="Angela",last_name="Parrill", sk8name="Leggs'n Bacon",sk8number="11", country=Country.objects.get(name="United States"))
#
#     user_list=[r1,r2,r3,r4]
#     for u in user_list:
#         u.user.set_password(password)
#         u.user.save()
#
# def make_coaches():
#     con=Con.objects.get(year="2015")
#
#     csvfile=(import_path+"coaches_data.csv")
#     coach_list=[]
#
#     with open(csvfile) as file1:
#         data = csv.reader(file1, delimiter=',')
#         rownumber=0
#         info=[]
#         errorlist=[]
#         for row in data:
#             rownumber = rownumber +1
#             if rownumber >= 2:
#                 info.append(row)
#
#     for datalist in info:
#         try:
#             sk8name=str(datalist[0])
#             print "sk8name ",sk8name
#             last_name=str(datalist[2])
#             print "last_name ",last_name
#             first_name=str(datalist[3])
#             print "first_name ",first_name
#             intl_str=str(datalist[4])
#             print "intl_str",intl_str
#             gender=str(datalist[5])
#             print "gender",gender
#             email=str(datalist[6])
#             print "email",email
#             country_str=str(datalist[8])
#             print "country_str",country_str
#             state_slugname=datalist[10]
#             print "state_slugname",state_slugname
#             coach_description=datalist[11]
#
#             if not intl_str or len(intl_str)<1:
#                 intl=False
#             else:
#                 intl=True
#
#             if country_str:
#                 try:
#                     country=Country.objects.get(name=country_str)
#                 except:
#                     print "error finding country",country_str
#                     country=Country.objects.get(name="United States")
#             else:
#                 country=Country.objects.get(name="United States")
#
#             if state_slugname:
#                 try:
#                     state=State.objects.get(slugname=state_slugname)
#                 except:
#                     print "error finding state",state_slugname
#             else:
#                 state=None
#
#             print "about to make coach"
#             coach=None#to serest who it is
#
#             r_query=Registrant.objects.filter(con=con,sk8name=sk8name)
#             for entry in r_query:
#                 entry.delete()
#             try:
#                 coach=Registrant.objects.get(con=con,email=email,first_name=first_name,last_name=last_name)
#                 sk8name=sk8name
#                 sk8number="X"
#                 skill="A"
#                 coach.country=country
#                 coach.state=state
#                 coach.gender=gender
#
#             except:
#                 coach=Registrant(con=con,email=email,first_name=first_name,last_name=last_name,sk8name=sk8name,sk8number="X",skill="A",country=country,state=state,gender=gender)
#
#             print "coach",coach
#
#             coach.save()
#             coach.save()#save twice to make sure has user?
#             print "saved!"
#             coach_list.append(coach)
#
#             coach_object,created=Coach.objects.get_or_create(user=coach.user)
#             coach_object.description=coach_description
#             print "COACH OBJECT ",coach_object,coach_object.description
#             coach_object.save()
#
#         except:
#             print "ERROR with ",sk8name
#             errorlist.append(datalist)
#
#     if errorlist:
#         f=open(export_path+"Coach Errors.csv", "wb")
#         writer = csv.writer(f, delimiter=',', quoting=csv.QUOTE_ALL)
#         for error in errorlist:
#             writer.writerow(error)
#         f.close()
#
#     return "done! %s coaches!"%str(len(coach_list))
#
# def swap_captain_name():
#     csvfile=(import_path+"Training.csv")
#     training_list=[]
#
#     with open(csvfile) as file1:
#         data = csv.reader(file1, delimiter=',')
#         rownumber=0
#         info=[]
#         errorlist=[]
#         for row in data:
#             rownumber = rownumber +1
#             if rownumber >= 2:
#                 info.append(row)
#
#     replacement_info=[]
#     for datalist in info:
#         training_pk=int(datalist[0])
#         #print "training_pk",training_pk
#         training=Training.objects.get(pk=training_pk)
#         #print "training",training
#         coach_names=training.display_coach_names()
#         #print "coach_names",coach_names
#         datalist[10]=coach_names
#         #print "datalist",datalist
#         replacement_info.append(datalist)
#
#     f=open(static_path+"TrainingCoaches.csv", "wb")
#     writer = csv.writer(f, delimiter=',', quoting=csv.QUOTE_ALL)
#     for data in replacement_info:
#         writer.writerow(data)
#     f.close()
#
# def t_setup():
#     con=Con.objects.get(pk=1)
#     csvfile=(import_path+"TrainingCoaches.csv")
#
#     training_list=[]
#
#     with open(csvfile) as file1:
#         data = csv.reader(file1, delimiter=',')
#         info=[]
#         for row in data:
#             info.append(row)
#
#         for datalist in info:
#             training_pk=int(datalist[0])
#             name=datalist[1]
#             location_type=datalist[2]
#             RCaccepted_str=datalist[3]
#             if RCaccepted_str:
#                 RCaccepted=True
#             else:
#                 RCaccepted=False
#             intl_str=datalist[4]
#             if intl_str:
#                 intl=True
#             else:
#                 intl=False
#             skill=datalist[5]
#             if skill in [0,"0"]:
#                 skill=None
#             gender=datalist[6]
#             duration=datalist[7]
#             onsk8s_str=datalist[8]
#             if onsk8s_str:
#                 onsk8s=True
#             else:
#                 onsk8s=False
#             contact_str=datalist[9]
#             if contact_str:
#                 contact=True
#             else:
#                 contact=False
#             coach_names=datalist[10]
#             coach_list=coach_names.split(', ')
#             print "coach_list",coach_list
#             description=datalist[11]
#
#             print "about to make training"
#             training=None#to serest who it is
#
#             t_query=Training.objects.filter(name=name, con=con)
#             if len(t_query)>=1:
#                 for entry in t_query:
#                     entry.delete()
#
#
#             print "A"
#             training=Training(name=name,duration=duration,onsk8s=onsk8s,contact=contact,con=con,location_type=location_type,RCaccepted=RCaccepted,description=description)
#             registered=Roster(gender=gender,skill=skill,intl=False,con=con)
#             auditing=Roster(gender='NA/Coed',skill=None,intl=False,con=con)
#             auditing.save()
#             print "c"
#             registered.save()
#             print "d"
#
#             training.save()
#             registered.registered=training
#             auditing.auditing=training
#             registered.registered=training
#             auditing.auditing=training
#             auditing.save()
#             registered.save()
#             try:
#                 for coach_n in coach_list:
#                     print "getting coach: ",coach_n
#
#                     coach_list=Registrant.objects.filter(sk8name=coach_n, con=con)
#                     coach=coach_list[0]
#                     if len(coach_list)>1:
#                         for item in coach_list[1:]:
#                             item.delete()
#
#                     user_coach=Coach.objects.get(user=coach.user)
#                     training.coach.add(user_coach)
#             except:
#                 pass
#
#             training.save()
#             print "training %s saved!"%(training)
#             training_list.append(training)
#     print "done! %s Trainings made"%(str(len(training_list)))
#
# def make_groups():
#     g1,created1=Group.objects.get_or_create(name="Khaleesi")
#     g2,created2=Group.objects.get_or_create(name="Blood Rider")
#     g3,created3=Group.objects.get_or_create(name="NSO")
#     g4,created4=Group.objects.get_or_create(name="Volunteer")
#
# def easy_pws(user_list):
#     password="password"
#     for u in user_list:
#         u.set_password(password)
#         u.save()
#
# def set_pws(user_list,password):
#     #user_list=list(User.objects.filter(username__in=["mdaizovi@gmail.com","denise.grimes@gmail.com","derbydish99@gmail.com","rollerconcoordinator@gmail.com"]))
#     #password="@$$p3nn13$"
#     for u in user_list:
#         u.set_password(pw)
#         u.save()
