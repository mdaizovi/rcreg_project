from scheduler.models import Venue, Location, Roster, Challenge, Training, Coach
from con_event.models import Country, State, Con, Registrant, Blog
from django.contrib.auth.models import Group, User
from swingtime.models import Occurrence
#from swingtime.models import Occurrence
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

#python manage.py shell
#from basic_data import*

con=Con.objects.get(year="2016")
date_list=con.get_date_range()[0:1]
duration=1
location=Location.objects.get(pk=7)
#possible_times=location.empty_times(date_list,duration)


def get_gametypes():
    con=Con.objects.get(year="2016")
    gametypedict={}

    for c in Challenge.objects.filter(con=con, RCaccepted=True):
        if c.gametype not in gametypedict:
            gametypedict[c.gametype]=[c]
        else:
            templist=gametypedict.get(c.gametype)
            templist.append(c)
            gametypedict[c.gametype]=list(templist)

    for k,v in gametypedict.iteritems():
        print k
        for item in v:
            print item.pk, item.name, item.gametype, item.duration, item.is_a_game
    print "\nSUMMARY\n"
    for k,v in gametypedict.iteritems():
        print k, ": ",len(v)


def get_duration():
    con=Con.objects.get(year="2016")
    durdict={}

    for c in Challenge.objects.filter(con=con, RCaccepted=True):
        if c.duration not in durdict:
            durdict[c.duration]=[c]
        else:
            templist=durdict.get(c.duration)
            templist.append(c)
            durdict[c.duration]=list(templist)
    print "\nChallenges\n"
    for k,v in durdict.iteritems():
        print k
        for item in v:
            print item.pk, item.name, item.gametype, item.duration, item.is_a_game
    print "\nChallenge SUMMARY\n"
    for k,v in durdict.iteritems():
        print k, ": ",len(v)

    durdictTR={}
    for c in Training.objects.filter(con=con, RCaccepted=True):
        if c.duration not in durdictTR:
            durdictTR[c.duration]=[c]
        else:
            templist=durdictTR.get(c.duration)
            templist.append(c)
            durdictTR[c.duration]=list(templist)
    print "\nTrainings\n"
    for k,v in durdictTR.iteritems():
        print k
        for item in v:
            print item.pk, item.name, item.duration
    print "\nTraining SUMMARY\n"
    for k,v in durdictTR.iteritems():
        print k, ": ",len(v)



def get_idosyncracies():
    perfect=[]
    imperfect=[]
    con=Con.objects.get(year="2016")

    for c in Challenge.objects.filter(con=con, RCaccepted=True):
        if c.gametype!="6GAME" or c.is_a_game:
            print "%s is_a_game or 6GAME, and duration is %s"%(c.name, c.duration)
            if float(c.duration)<1.0:
                print  "%s duration is %s"%(c.name, c.duration)
                if c not in imperfect:
                    imperfect.append(c)

            if c.is_a_game and c.gametype!="6GAME":
                print "%s is_a_game, but is not 6GAME"%(c.name)
                if c not in imperfect:
                    imperfect.append(c)
            if c.gametype=="6GAME" and not c.is_a_game:
                print "%s is 6GAME, but not is_a_game"%(c.name)
                if c not in imperfect:
                    imperfect.append(c)

        if c.gametype=="6GAME" and c.is_a_game and float(c.duration)>=1.0:
            if c not in perfect:
                perfect.append(c)
        elif c.gametype!="6GAME" and not c.is_a_game and float(c.duration)<=1.0:
            if c not in perfect:
                perfect.append(c)

        if c.gametype!="6GAME" and not c.is_a_game and float(c.duration)>=1.0:
            print "%s is not a game, but duration is %s"%(c.name, c.duration)
            if c not in imperfect:
                imperfect.append(c)

    print "Perfect: ",len(perfect)
    print "Imperfect: ",len(imperfect)
    return perfect, imperfect


def test_interest_default():
    con=Con.objects.get(year="2016")
    for t in Training.objects.filter(con=con, RCaccepted=True):
        if not t.interest:
            print t.name, "Coaches: ",t.display_coach_names(),t.get_default_interest()#don'tsave!
        else:
            print "%s has an interest, it's %s"%(t.name,str(t.interest))
    print " "
    for c in Challenge.objects.filter(con=con, RCaccepted=True):
        if not c.interest:
            print c.name, c.get_default_interest()#don'tsave!
        else:
            print "%s has an interest, it's %s"%(t.name,str(t.interest))

#con=Con.objects.get(year="2016")
#qset=list(Training.objects.filter(con=con))
#loc=show_loc(qset)
def show_loc(qset):
    loc={}
    for t in qset:
        if t.location_type not in loc:
            loc[t.location_type]=[t]
        else:
            temp=loc.get(t.location_type)
            temp.append(t)
            loc[t.location_type]=list(temp)
    return loc


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
    long_emails=[]

    for od in all_data:
        email2=od.get("AB")
        email_list.append(email2)
        try:
            if len(email2)>=30:
                print "long email ",email2
                long_emails.append(od)
        except:
            print "error with ",od

            #thought i had error, don't think this is necessary
    # for od in all_data:
    #     email2=od.get("AB")
    #     if not email2:
    #         email2=od.get("Q")
    #     email_list.append(email2)
    #     if len(email)>=30:
    #         print "long email ",email
    #         long_emails.append(od)



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

    if len(long_emails)>0:
        name_str='LONGEmailRegistrants '+ date_str +'.xlsx'
        dupe_file=write_wb(export_path,name_str,long_emails,header)

    return single_file,dupe_file

def sort_BPT_excel(target_file):
    """aggregates the cleaner funcitons, so i can enter the big BPT excel and shit out: good/bad emails, 2 incomplete name files, 1 complete name file"""
    BPT_header = get_header((static_path+'BPTheader.xlsx'))
    single_file,dupe_file=email_dupes(target_file)
    no_sk8name_file,no_real_name_file,complete_entries_file=find_incompletes(single_file)

    return single_file, dupe_file, no_sk8name_file, no_real_name_file, complete_entries_file

#from basic_data import*
#target_file=(import_path+'RollerTron Attendee 042716.xlsx')
#con=Con.objects.get(year="2016")
#single_file, dupe_file, no_sk8name_file, no_real_name_file, complete_entries_file=sort_BPT_excel(target_file)
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
                    #value = getattr(this_reg, k)
                    #if v and not value:
                    if v:
                        print "setting or updating",this_reg,"s ",k
                        setattr(this_reg, k, v)
                    elif not v:
                        print "od doesn't have ",k
                    # elif value:
                    #     print this_reg,"already has a ",k,": ",value
                        #NEW NOTE this was making everyone have default MVP Female setting


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


# #########temporary roster splitting funcitons############
# ####### maybe temporarily disable delete signals and replace w/ print statements in case I fuck up somewhere, so i won't accidentally delete all?######
#
# #python manage.py shell
# #from basic_data import*
#
# #lessthan1,just1,morethan1=get_shared_rosters()
# def get_shared_rosters():
#     lessthan1=[]
#     just1=[]
#     morethan1=[]
#     for r in Roster.objects.all():
#         connections=list(r.roster1.all())+list(r.roster2.all())
#         if len(connections)==1:
#             just1.append(r)
#         elif len(connections)<1 and not r.registered and not r.auditing:
#             print "homeless roster ",r," pk: ",r.pk
#             lessthan1.append(r)
#         elif len(connections)>1:
#             print "dual roster: ",r," pk: ",r.pk
#             morethan1.append(r)
#
#     print "final tally: "
#     print "homeless: ",len(lessthan1)
#     print "just1: ",len(just1)
#     print "morethan1: ",len(morethan1)
#
#     return lessthan1,just1,morethan1
#
# #unglue(morethan1)
# def unglue(roster_list):
#     for r in roster_list:
#         print "starting to unglue ",r
#         connections=list(r.roster1.all())+list(r.roster2.all())
#         print len(connections)," connections :",connections
#
#         for c in connections[1:]:
#             this_clone=r.clone_roster()
#
#             old_team,selected_team=c.replace_team(r,this_clone)
#
#             print old_team," is no longer in ",c," now it's ",selected_team
#             c.save()
#
#         print "prev captain #: ",r.captain.captaining
#         r.captain.save()#to reset captain#
#         print "new captain #: ",r.captain.captaining
#         print "done ungluing ",r
#     print "done with unglue function"
#
# ##########after done, re enable delete signals#########
# ###########################start real basic data#########################
