import csv
import os
import datetime
from rcreg_project.settings import BASE_DIR
from rcreg_project.extras import remove_punct, ascii_only, ascii_only_no_punct
import openpyxl
import collections

from con_event.models import  Con, MatchingCriteria, Registrant, SKILL_LEVEL_CHG, SKILL_LEVEL_TNG, GENDER
from scheduler.models import Challenge, Roster

from django.db import models
from django.db.models import Q
import random, string
from django.utils import timezone


#real rollertron has about 49 rosters with no skill, and i couldn't run skill mismatch bc some had no opponent
#wrote around it, need to test.
#then get a way to get average skill and see if i can just change it to that.




def random_roster(con):
    rand_gen = random.choice(GENDER)[0]
    ran_skill = random.choice(SKILL_LEVEL_CHG)[0]
    ran_name = ''.join(random.choice(string.lowercase) for i in range(10))
    r1 = Roster(skill=ran_skill, gender=rand_gen, name=ran_name, con=con)
    skills_a = r1.skills_allowed()
    gender_a = r1.genders_allowed()

    er = list(Registrant.objects.filter(con=con, skill__in=skills_a, gender__in=gender_a))
    cap1 = random.choice(er)
    r1.captain = cap1

    return r1

def random_training(con, user_list):
    ran_skill = random.choice(SKILL_LEVEL_TNG)[0]
    ran_name = ''.join(random.choice(string.lowercase) for i in range(7))
    ran_onsk8s = [True, True, True, False]
    ran_sess = [1,1,1,2,1,1,1]
    t1 = Training(skill=ran_skill, name=ran_name, onsk8s=random.choice(ran_onsk8s), sessions=random.choice(ran_sess))

    er = list(Coach.objects.filter(user__in = user_list))
    coach = random.choice(er)
    t1.coach = coach

    return t1


def make_act():

    con = Con.objects.get(pk=3)

    cno = 0
    tno = 0

    while cno < 200:
        r1 = random_roster(con)
        r2 = random_roster(con)
        chal = Challenge(roster1=r1, roster2=r2, captain2accepted=True, RCaccepted=True, submitted_on=timezone.now())
        try:
            #r1.save()
            #r2.save()
            #chal.save()
            cno += 1
            print "challenge saved. ",cno
        except:
            print "error."

    user_list = []
    r_list = list(Registrant.objects.filter(con=con))
    for r in r_list:
        user_list.append(r.user)

    while tno < 100:
        t1 = random_training(con, user_list)
        try:
            #t1.save()
            tno += 1
            print "training saved. ",tno
        except:
            print "error."











#no_skill = get_no_skill()
def get_no_skill():
    no_skillr = []
    no_skillc = list(Challenge.objects.filter(Q(roster1__skill=None)|Q(roster2__skill=None)))
    for c in no_skillc:
        for r in [c.roster1, c.roster2]:
            if r and not r.skill:
                no_skillr.append(r)

    print "no skill rosters: ",len(no_skillr)
    return no_skillr

#skill_list = get_skill_range(roster)
def get_skill_range(roster):
    skills = []
    for s in roster.participants.all():
        if s.skill not in skills:
            skills.append(s.skill)
    return skills

def id_skill(roster, skill_list):
    print roster.skill, roster.pk, roster
    print skill_list

    if skill_list == ["A"]:
        roster.skill = "AO"
    elif skill_list == ["A", "B"] or skill_list == ["B","A"]:
        roster.skill = "AB"
    elif skill_list == ["B"]:
        roster.skill = "BO"
    elif skill_list == ["C", "B"] or skill_list == ["B","C"]:
        roster.skill = "BC"
    elif skill_list == ["C"]:
        roster.skill = "CO"
    else:
        print "no match found"
    #roster.save()


#mismatch, mismatch_challenge, no_cap, incompletec = get_skill_mismatch()
def get_skill_mismatch():
    mismatch = []
    mismatch_challenge = []
    no_cap = []
    incompletec = []
    for c in Challenge.objects.all():
        print c.pk, c
        for r in [c.roster1, c.roster2]:
            if r and r.captain:
                my_team, opponent, my_acceptance, opponent_acceptance = c. my_team_status([r.captain])
                if my_team and opponent:
                    sa =  opponent.opponent_skills_allowed()
                    if my_team.skill not in sa:
                        if r not in mismatch:
                            mismatch.append(r)
                            # print "adding"
                            # print r, r.skill, " not in "
                            # print sa
                        if c not in mismatch_challenge:
                            mismatch_challenge.append(c)
                    else:
                        pass
                        #print my_team.pk, my_team, " okay: ",my_team.skill, sa

            elif r and not r.captain:
                no_cap.append(r)
            elif not r and c not in incompletec:
                print "incomplete"
                incompletec.append(c)

    print "done"
    print "mismatch roster: ", len(mismatch)
    print "mismatch_challenge: ",len(mismatch_challenge)
    print "no_cap:", len(no_cap)
    print "incompletec: ",len(incompletec)
    return mismatch, no_cap, incompletec















"""This whole file is for helping me compare excel files of who SHOULD BE in RollerTron
and who ACTUALLY IS in RollerTron.
Assumes the ACUALLY IS is re-arranged from export to look like BPT excel.
This is kind of a private mess. I didn't see the point in deleting it, but you can if you want.
"""

staticdata_path=BASE_DIR+"/static/data/"
date_str=datetime.date.today().strftime("%B %d %Y")

########If you want to run data comparison to see if all people who SHOULD be in the database ARE.

#python manage.py shell
#from compare_data import*
#db_xlfile=(staticdata_path+'Registrant-2016-06-12 REORDERED copy.xlsx')
#bpt_xlfile=(staticdata_path+'RollerTron MASTER @ 060316 copy.xlsx')
#sort_it_out(db_xlfile,bpt_xlfile)


#########if you just want to look for name dupes:

#python manage.py shell
#from compare_data import*
#xlfile=(staticdata_path+'RollerTron MASTER @ 060316 copy.xlsx')
#all_data=make_excel_odict_list(xlfile)
#same_name(all_data)


data_columns=['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X',
    'Y','Z','AA','AB','AC','AD','AE','AF','AG','AH','AI','AJ','AK','AL','AM','AN']

def wb_or_str(xlfile):
    """checks is xlfile input is a strong of name, or wb object. either makes or returns object."""
    if isinstance(xlfile , basestring):
        #if a string of file name is entered
        wb = openpyxl.load_workbook(xlfile)
    else:
        # if a wb object is entered
        wb = xlfile
    return wb

def get_header(xlfile):
    """Gets header from source Excel sheet for printing other
    input: Excel file
    output: """
    wb=wb_or_str(xlfile)
    sheet = wb.get_active_sheet()
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
    all_data=[]
    highest_row=sheet.get_highest_row()
    for row in range(2, sheet.get_highest_row() + 1):
        data_holding_dict = collections.OrderedDict()
        for  c in data_columns:
            location=c+str(row)
            data=sheet[location].value
            data_holding_dict[c]=data
        all_data.append(data_holding_dict)

    return all_data

def find_incompletes(xlfile):
    """this assumes BPT header, not my header form exporting Admin
    Makes sure each Registrant has all the necessary informaiton
    Returns 3 Excel files"""
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

    header=get_header((staticdata_path+'BPTheader.xlsx'))
    #date_str=datetime.date.today().strftime("%B %d %Y")#eg 'July 23 2010'
    #global vairable, look at top of file

    if len(no_sk8name)>0:
        name_str='NoSk8NameReg '+ date_str +'.xlsx'
        no_sk8name_file=write_wb(staticdata_path,name_str,no_sk8name,header)
    else:
        no_sk8name_file=None

    if len(no_real_name)>0:
        name_str='NoRealNameReg '+ date_str +'.xlsx'
        no_real_name_file=write_wb(staticdata_path,name_str,no_real_name,header)
    else:
        no_real_name_file=None

    if len(complete_entries)>0:
        name_str='CompleteReg '+ date_str +'.xlsx'
        complete_entries_file=write_wb(staticdata_path,name_str,complete_entries,header)
    else:
        complete_entries_file=None

    return no_sk8name_file,no_real_name_file,complete_entries_file

def email_dupes(xlfile):
    """Takes in list of ordered dicts from BPT Excel sheet, shits out 2 excels: 1 of people who entered unique emails,
    1 of people who are attached to an email that is used more than once."""
    all_data=make_excel_odict_list(xlfile)
    email_list=[]
    last_email=None
    good_emails=[]
    bad_emails=[]
    long_emails=[]

    for od in all_data:
        email2=od.get("AB")
        email_list.append(email2)
        if len(email2)>=30:
            print "long email ",email2
            long_emails.append(od)

    for od in all_data:
        email2=od.get("AB")
        if int(email_list.count(email2))>1:
            bad_emails.append(od)
        else:
            good_emails.append(od)

    header=get_header((staticdata_path+'BPTheader.xlsx'))
    #date_str=datetime.date.today().strftime("%B %d %Y")#eg 'July 23 2010'
    #global vairable, look at top of file

    if len(good_emails)>0:
        name_str='SingleEmailRegistrants '+ date_str +'.xlsx'
        single_file=write_wb(staticdata_path,name_str,good_emails,header)
    else:
        single_file=None

    if len(bad_emails)>0:
        name_str='EmailDupeRegistrants '+ date_str +'.xlsx'
        dupe_file=write_wb(staticdata_path,name_str,bad_emails,header)
    else:
        dupe_file=None

    if len(long_emails)>0:
        name_str='LONGEmailRegistrants '+ date_str +'.xlsx'
        dupe_file=write_wb(staticdata_path,name_str,long_emails,header)

    return single_file,dupe_file

def sort_BPT_excel(target_file):
    """aggregates the cleaner funcitons, so i can enter the big BPT excel and shit out: good/bad emails, 2 incomplete name files, 1 complete name file"""
    BPT_header = get_header((staticdata_path+'BPTheader.xlsx'))
    single_file,dupe_file=email_dupes(target_file)

    no_sk8name_file,no_real_name_file,complete_entries_file=find_incompletes(single_file)

    return single_file, dupe_file, no_sk8name_file, no_real_name_file, complete_entries_file


class Registrant:
    ########REMEMEBER THIS IS A TEMPORARY CLASS MEANTTO MIMIC REGISTRANT OBJEC,T NOT THE REAL THING!!!
    def __init__(self):
        self.pass_type=None
        self.email=None
        self.first_name = None
        self.last_name = None
        self.sk8name = None
        self.BPT_Ticket_ID=None


def make_temp_registrants(all_data):
    """makes temporary registrant objects from the OD list of existing real Registrants from the DB,
    mimcking important attributes. As exported from Excel, re-arranged to mimic BPT so I could re-use code"""

    reg_obj_list=[]
    dict_connection={}

    for od in all_data:
        email=ascii_only_no_punct(od.get("AB"))
        if not email:
            ascii_only_no_punct(od.get("Q"))

        first_name=ascii_only_no_punct(od.get("AA"))
        if not first_name:
            first_name =ascii_only_no_punct(od.get("I"))

        last_name = ascii_only_no_punct(od.get("Z"))
        if not last_name:
            last_name = ascii_only_no_punct(od.get("H"))
        sk8name = ascii_only_no_punct(od.get("AC"))

        BPT_Ticket_ID=ascii_only_no_punct(od.get("A"))

        attr_dict={'email':email,'first_name':first_name,'last_name':last_name,'sk8name':sk8name,'BPT_Ticket_ID':BPT_Ticket_ID}
        this_reg=Registrant()
        for k,v in attr_dict.iteritems():
            setattr(this_reg, k, v)

        reg_obj_list.append(this_reg)
        #make the dictionary so I can unpck them later
        dict_connection[this_reg]=od

    return reg_obj_list,dict_connection


def same_name(od_list):
    """Inspired by Carla Smith affair, 1 had orignial input too loose, so different people with the same name but different emails, diff sk8names, oculd be seen as 1 perosn
    As of May 2016 that has been changed.
    Takes in ordered dict list of everyone from BPT list who should be in DB,
    sees who has the same name, prints list of possible doppelgangers."""

    names={}
    sortedods=[]

    dupes=[]
    for od in od_list:

        first_name=od.get("AA")
        if not first_name:
            first_name=od.get("F")

        last_name=od.get("Z")
        if not last_name:
            last_name=od.get("E")


        email=od.get("AB")
        if not email:
            email=od.get("Q")

        if first_name and last_name:
            sk8ername_str=first_name+" "+last_name

            if sk8ername_str in names and (email!=names.get(sk8ername_str)):
                dupes.append(od)

                for ods in sortedods:
                    fn=ods.get("AA")
                    if not fn:
                        fn=ods.get("F")
                    ln=ods.get("Z")
                    if not ln:
                        ln=ods.get("E")

                    if fn and ln:
                        sk8n=fn+" "+ln
                        if sk8n==sk8ername_str:
                            dupes.append(ods)
                            break

            else:
                names[sk8ername_str]=email
                sortedods.append(od)

    if len(dupes)>0:
        header=get_header((staticdata_path+'BPTheader.xlsx'))
        name_str='Doppelsk8ers '+ date_str +'.xlsx'
        write_wb(staticdata_path,name_str,dupes,header)
        print "Doppelsk8ers written"
    else:
        print "no dupes"



def comp_obj_lists(db_obj_list, bpt_obj_list):
    """mimics db lookup to see which objects are in 1 list but not the other.
    First list should be objs in DB, second objects that may or may not be in DB"""

    def make_search_crit_list(search_crit_list_str, obj_list):
        """takes in list of search criteria as strings, like ["first_name","last_name"] and makes tuple of that object's values
        returns list of all tuples made"""
        search_crit_list=[]
        dict_connection={}

        for obj in obj_list:
            list2btuple=[]
            for crit_str in search_crit_list_str:
                list2btuple.append(getattr(obj, crit_str))
            this_tup=tuple(list2btuple)
            search_crit_list.append(this_tup)
            dict_connection[this_tup]= obj

        return search_crit_list, dict_connection

    def trim_obj_list(in_db, bpt_obj_list,search_crit_list_str):
        """takes list of which objects are in the db as of moment and which should be but haven't been found yet,
        makes search criteria list of db entries and filters should be in by, returns
        modified lists of who is in d and who may not be, after that filter"""
        print "trim_obj_list("

        in_db_search_crit_list,in_db_dict_connection=make_search_crit_list(search_crit_list_str, in_db)
        bpt_search_crit_list,bpt_dict_connection=make_search_crit_list(search_crit_list_str, bpt_obj_list)

        bpt_set = set(bpt_search_crit_list)
        db_set = set(in_db_search_crit_list)
        intersect=bpt_set.intersection(db_set)

        just_found=[]

        for obj_tup in intersect:
            if obj_tup is not None:
                obj=bpt_dict_connection.get(obj_tup)
                if obj is not None:
                    bpt_obj_list.remove(obj)
                    just_found.append(obj)

        #reminder: make shallow copies, not pointers.
        return list(in_db), list(bpt_obj_list),just_found


    in_db=list(db_obj_list)
    not_found_yet=list(bpt_obj_list)

    all_found=[]
    print "all_found len: ",len(all_found)

    in_db, not_found_yet,just_found=trim_obj_list(in_db, not_found_yet,["email", "first_name","last_name","sk8name"])
    print "pass 1: %s found in DB by emial, fname, lname,sk8name, %s not found, %s total "%( str(len(just_found)), str(len(not_found_yet)), str((len(in_db)+len(not_found_yet))) )
    all_found+=just_found
    print "all_found len: ",len(all_found)

    #next, email and fname and lname NOT sk8name
    in_db, not_found_yet,just_found=trim_obj_list(in_db, not_found_yet,["email", "first_name","last_name"])
    print "pass 2: %s found in DB by email, fname, lname,but NOT sk8name, %s not found, %s total "%( str(len(just_found)), str(len(not_found_yet)), str((len(in_db)+len(not_found_yet))) )
    all_found+=just_found
    print "all_found len: ",len(all_found)
############this looks like it could be problematic, prodice false positives. commented out########

    #next, email and fname and lname NOT sk8name
    # in_db, not_found_yet,just_found=trim_obj_list(in_db, not_found_yet,["email","last_name"])
    # print "pass 3: %s found in DB by email, lname, %s not found, %s total "%( str(len(just_found)), str(len(not_found_yet)), str((len(in_db)+len(not_found_yet))) )
    #all_found+=just_found
    #print "all_found len: ",len(all_found)
#######################################


    #next, email and fname and lname NOT sk8name
    in_db, not_found_yet,just_found=trim_obj_list(in_db, not_found_yet,["email", "first_name",])
    print "pass 4: %s found in DB by email, fname, %s not found, %s total "%( str(len(just_found)), str(len(not_found_yet)), str((len(in_db)+len(not_found_yet))) )
    all_found+=just_found
    print "all_found len: ",len(all_found)

    #next, email and sk8nme
    in_db, not_found_yet,just_found=trim_obj_list(in_db, not_found_yet,["email", "sk8name"])
    print "pass 5: %s found in DB by email, and sk8name, %s not found, %s total "%( str(len(just_found)), str(len(not_found_yet)), str((len(in_db)+len(not_found_yet))) )
    all_found+=just_found
    print "all_found len: ",len(all_found)

    #next, email and fname and lname and sk8name
    in_db, not_found_yet,just_found=trim_obj_list(in_db, not_found_yet,["first_name","last_name","sk8name"])
    print "pass 6: %s found in DB by fname, lname,sk8name, NOT email %s not found, %s total "%( str(len(just_found)), str(len(not_found_yet)), str((len(in_db)+len(not_found_yet))) )
    all_found+=just_found
    print "all_found len: ",len(all_found)

        #next, email and fname and lname and sk8name
    in_db, not_found_yet,just_found=trim_obj_list(in_db, not_found_yet,["first_name","sk8name"])
    print "pass 7: %s found in DB by fname,sk8name %s not found, %s total "%( str(len(just_found)), str(len(not_found_yet)), str((len(in_db)+len(not_found_yet))) )
    all_found+=just_found
    print "all_found len: ",len(all_found)

    #next, email and fname and lname and sk8name
    in_db, not_found_yet,just_found=trim_obj_list(in_db, not_found_yet,["last_name","sk8name"])
    print "pass 8: %s found in DB by lname, sk8name, %s not found, %s total "%( str(len(just_found)), str(len(not_found_yet)), str((len(in_db)+len(not_found_yet))) )
    all_found+=just_found
    print "all_found len: ",len(all_found)

    return in_db, not_found_yet,all_found

def sort_it_out(db_xlfile,bpt_xlfile):
    """bundles all of my functions together so I don't have to type so much"""
    db_all_data=make_excel_odict_list(db_xlfile)
    bpt_all_data=make_excel_odict_list(bpt_xlfile)

    db_obj_list,db_dict_connection=make_temp_registrants(db_all_data)
    bpt_obj_list,bpt_dict_connection=make_temp_registrants(bpt_all_data)

    in_db_obj, not_found_yet_obj,all_found_list=comp_obj_lists(db_obj_list, bpt_obj_list)

    in_db=[]
    for obj in all_found_list:
        od=bpt_dict_connection.get(obj)
        if od:
            in_db.append(od)

    not_found_yet=[]
    for obj in not_found_yet_obj:
        od=bpt_dict_connection.get(obj)
        if od:
            not_found_yet.append(od)

    header=get_header((staticdata_path+'BPTheader.xlsx'))
    #date_str=datetime.date.today().strftime("%B %d %Y")#eg 'July 23 2010'
    #global vairable, look at top of file

    if len(in_db)>0:
        name_str='BPT IN RollerTron '+ date_str +'.xlsx'
        write_wb(staticdata_path,name_str,in_db,header)
        print "in db list written"
    if len(not_found_yet)>0:
        name_str='BPT NOT IN RollerTron '+ date_str +'.xlsx'
        write_wb(staticdata_path,name_str,not_found_yet,header)
        print "not db list written"
