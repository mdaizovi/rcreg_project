from scheduler.models import Venue, Location, Roster, Challenge, Training, Coach
from con_event.models import Country, State, Con, Registrant, Blog
from django.contrib.auth.models import Group, User
import csv
import os
import datetime
from rcreg_project.settings import BASE_DIR
from rcreg_project.extras import remove_punct,ascii_only,ascii_only_no_punct
import openpyxl
import collections

static_path=BASE_DIR+"/static/"
old_rc_path=static_path+'RC2015/unformatted/'
new_rc_path=static_path+'RC2015/exported/'
data_columns=['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X',
    'Y','Z','AA','AB','AC','AD','AE','AF','AG','AH','AI','AJ','AK','AL','AM','AN']

#xlfile=(old_rc_path+'myheader.xlsx')
#xlfile=(old_rc_path+'BPTheader.xlsx')
def get_header(xlfile):
    wb = openpyxl.load_workbook(xlfile)
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

def make_excel_odict_list(xlfile):
    """Takes in excel file of BPT registrant data, somewhat re-ordered and w/ a new header to suit my import needs,
    (as described in WTFAQ). Turns each row into an ordered dict, returns list of all ordered dicts"""
    wb = openpyxl.load_workbook(xlfile)
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

#xlfile=(old_rc_path+'SingleEmailRegistrants.xlsx')
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

    header=get_header((old_rc_path+'BPTheader.xlsx'))
    write_wb(old_rc_path,'NoSk8NameReg.xlsx',no_sk8name,header)
    write_wb(old_rc_path,'NoRealNameReg.xlsx',no_real_name,header)
    write_wb(old_rc_path,'CompleteReg.xlsx',complete_entries,header)


#xlfile=(old_rc_path+"RollerTron.xlsx")
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

    header=get_header((old_rc_path+'BPTheader.xlsx'))
    write_wb(old_rc_path,'SingleEmailRegistrants.xlsx',good_emails,header)
    write_wb(old_rc_path,'EmailDupeRegistrants.xlsx',bad_emails,header)

def sort_BPT_excel():
    """aggregates the cleaner funcitons, so i can enter the big BPT excel and shit out: good/bad emails, 2 incomplete name files, 1 complete name file"""
    BPT_header = get_header((old_rc_path+'BPTheader.xlsx'))
    email_dupes((old_rc_path+"RollerTron.xlsx"))
    find_incompletes((old_rc_path+'SingleEmailRegistrants.xlsx'))
    #the end.


# con=Con.objects.get(year="2016")
# clean_xlfile=(old_rc_path+'SingleEmailRegistrants.xlsx')
#clean_xlfile=(old_rc_path+'RegistrantFAIL copy.xlsx')
def import_from_excel(clean_xlfile,con):
    """This assumes that I've already checked for duplicate emails and lack of name, sk8name.
    This is data that could be ready for import via Django import/export, but I think this will be faster.
    This is coming from BPT format, not mine"""
    all_data=make_excel_odict_list(clean_xlfile)
    error_list=[]
    success_list=[]
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
            try:#I don't search by names because at this point they ahven't been ascii/punct cleaned, so will be different.
            #maybe I'll have to clean the names first and include names, if me being obstinate about email causes a problem?
                this_reg=Registrant.objects.get(con=con, email=email)
            except:
                this_reg=Registrant(con=con, email=email,first_name=first_name,last_name=last_name)

            this_reg.skill=skill
            this_reg.gender=gender
            this_reg.pass_type=pass_type
            this_reg.first_name=first_name
            this_reg.last_name=last_name
            this_reg.sk8name=sk8name
            this_reg.sk8number=sk8number
            this_reg.country=country
            this_reg.state=state
            this_reg.BPT_Ticket_ID=BPT_Ticket_ID
            this_reg.affiliation=affiliation
            this_reg.ins_carrier=ins_carrier
            this_reg.ins_number=ins_number
            this_reg.age_group=age_group
            this_reg.favorite_part=favorite_part
            this_reg.volunteer=volunteer
            this_reg.save()
            this_reg.save()#think I have to do twice tomake user? I forgot.
            success_list.append(od)
            print this_reg," Succesfully made"
        except:
            print "Fail: "
            error_list.append(od)
            print this_reg


    header=get_header((old_rc_path+'BPTheader.xlsx'))
    if success_list:
        write_wb(old_rc_path,'RegistrantsMade.xlsx',success_list,header)
    if error_list:
        write_wb(old_rc_path,'RegistrantFAIL.xlsx',error_list,header)



def make_countries():
    csvfile=(static_path+"All countries.csv")

    with open(csvfile) as file1:
        data = csv.reader(file1, delimiter=',')
        rownumber=0
        countryinfo=[]
        errorlist=[]
        for row in data:
            rownumber = rownumber +1
            if rownumber >= 2:
                countryinfo.append(row)

    for datalist in countryinfo:
        try:
            slugname=datalist[0]
            name=datalist[1]
            county, created=Country.objects.get_or_create(name=name, slugname=slugname)
            print "%s (%s) made successfully" % (country.name, country.slugname)
        except:
            errorlist.append(datalist)

    if errorlist:
        f=open(static_path+"Country Errors.csv", "wb")
        writer = csv.writer(f, delimiter=',', quoting=csv.QUOTE_ALL)
        for error in errorlist:
            writer.writerow(error)

        f.close()

def make_states():
    csvfile=(static_path+"states.csv")

    with open(csvfile) as file1:
        data = csv.reader(file1, delimiter=',')
        rownumber=0
        stateinfo=[]
        errorlist=[]
        for row in data:
            rownumber = rownumber +1
            if rownumber >= 2:
                stateinfo.append(row)

    for datalist in stateinfo:
        try:
            slugname=datalist[0]
            name=datalist[1]
            country_name=datalist[2]
            try:
                country=Country.objects.get(name=country_name)
            except:
                country=Country.objects.get(name="United States")

            state, created=State.objects.get_or_create(name=name, slugname=slugname, country=country)
            print "5"
            state.save()
            print "%s %s (%s) made successfully" % (state.name, state.slugname, state.country)
        except:
            errorlist.append(datalist)

    if errorlist:
        f=open(static_path+"State Errors.csv", "wb")
        writer = csv.writer(f, delimiter=',', quoting=csv.QUOTE_ALL)
        for error in errorlist:
            writer.writerow(error)
        f.close()

def make_rcs():
    rc1, created1=Con.objects.get_or_create(start=datetime.date(2015, 07, 22),end=datetime.date(2015, 07, 26))
    rc2, created2=Con.objects.get_or_create(BPT_event_id='2304351',start=datetime.date(2016, 07, 27),end=datetime.date(2016, 07, 31))
    rc2.save()
    rc3, created3=Con.objects.get_or_create(start=datetime.date(2017, 07, 26),end=datetime.date(2017, 07, 30))
    for r in [rc1,rc2,rc3]:
        r.ticket_link="http://rollercon.com/register/rollercon-pass/"
        r.hotel_book_link="http://rollercon.com/register/hotel-reservations/"
        r.save()


def venue_setup():
    venue, created=Venue.objects.get_or_create(name="The Westgate Resort & Convention Center")
    l1, created1=Location.objects.get_or_create(venue=venue,location_type='Seminar Room',name="RC Classroom 231")
    l2, created2=Location.objects.get_or_create(venue=venue,location_type='Seminar Room',name="RC Classroom 233")
    l3, created3=Location.objects.get_or_create(venue=venue,location_type='Seminar Room',name="RC Classroom 235")
    l4, created4=Location.objects.get_or_create(venue=venue,location_type='Flat Track',name="RC MVP-1 Training Track One")
    l5, created5=Location.objects.get_or_create(venue=venue,location_type='Flat Track',name="RC MVP-2 Training Track Two")
    l6, created6=Location.objects.get_or_create(venue=venue,location_type='Flat Track',name="RC MVP-3 Training Track Three")
    l7, created7=Location.objects.get_or_create(venue=venue,location_type='Flat Track',name="RC MVP-4 Training Track Four")
    l8, created8=Location.objects.get_or_create(venue=venue,location_type='Flat Track',name="RC MVP-5 Training Track Five")
    l9, created9=Location.objects.get_or_create(venue=venue,location_type='Banked Track',name="RC-BT Banked Track")
    l10, created10=Location.objects.get_or_create(venue=venue,location_type='Flat Track',name="RC-C1 Competition Track One")
    l11, created11=Location.objects.get_or_create(venue=venue,location_type='Flat Track',name="RC-C2 Competition Track Two")
    l12, created12=Location.objects.get_or_create(venue=venue,location_type='Flat Track',name="RC-C3 Scrimmage Track")

def make_registrants():
    con1=Con.objects.get(pk=1)
    con2=Con.objects.get(pk=2)
    password="@$$p3nn13$"
    r1, created1=Registrant.objects.get_or_create(con=con1, pass_type="MVP", gender="Female", skill="B", email="mdaizovi@gmail.com",first_name="Michela",last_name="Dai Zovi", sk8name="Dahmernatrix",sk8number="505", country=Country.objects.get(name="Thailand"))
    r2, created2=Registrant.objects.get_or_create(con=con1, pass_type="MVP", gender="Female", skill="A", email="denise.grimes@gmail.com",first_name="Denise",last_name="Grimes", sk8name="Ivanna S. Pankin",sk8number="22", country=Country.objects.get(name="United States"))
    r3, created3=Registrant.objects.get_or_create(con=con1, pass_type="MVP", gender="Female", skill="A", email="derbydish99@gmail.com",first_name="Patricia",last_name="Ethier", sk8name="Trish the Dish",sk8number="86", country=Country.objects.get(name="United States"))
    r4, created4=Registrant.objects.get_or_create(con=con1, pass_type="MVP", gender="Female", skill="B", email="rollerconcoordinator@gmail.com",first_name="Angela",last_name="Parill", sk8name="Leggs'n Bacon",sk8number="11", country=Country.objects.get(name="United States"))

    r5, created1=Registrant.objects.get_or_create(con=con2, pass_type="MVP", gender="Female", skill="B", email="mdaizovi@gmail.com",first_name="Michela",last_name="Dai Zovi", sk8name="Dahmernatrix",sk8number="505", country=Country.objects.get(name="Thailand"))
    r6, created2=Registrant.objects.get_or_create(con=con2, pass_type="MVP", gender="Female", skill="A", email="denise.grimes@gmail.com",first_name="Denise",last_name="Grimes", sk8name="Ivanna S. Pankin",sk8number="22", country=Country.objects.get(name="United States"))
    r7, created3=Registrant.objects.get_or_create(con=con2, pass_type="MVP", gender="Female", skill="A", email="derbydish99@gmail.com",first_name="Patricia",last_name="Ethier", sk8name="Trish the Dish",sk8number="86", country=Country.objects.get(name="United States"))
    r8, created4=Registrant.objects.get_or_create(con=con2, pass_type="MVP", gender="Female", skill="B", email="rollerconcoordinator@gmail.com",first_name="Angela",last_name="Parill", sk8name="Leggs'n Bacon",sk8number="11", country=Country.objects.get(name="United States"))

    user_list=[r1,r2,r3,r4]
    for u in user_list:
        u.user.set_password(password)
        u.user.save()

def make_more_registrants():
    con=Con.objects.get(pk=2)

    csvfile=(old_rc_path+"EXAMPLE_MVP_DATA.csv")

    with open(csvfile) as file1:
        data = csv.reader(file1, delimiter=',')
        rownumber=0
        info=[]
        errorlist=[]
        for row in data:
            rownumber = rownumber +1
            if rownumber >= 2:
                info.append(row)

    for datalist in info:
        try:
            state_slugname=datalist[0]
            country_str=datalist[1]
            last_name=datalist[2]
            first_name=datalist[3]
            sk8name=datalist[4]
            gender=datalist[5]

            country=Country.objects.get(name=country_str)
            if state_slugname:
                state=State.objects.get(slugname=state_slugname)
            else:
                state=None

            import random, string
            random_email=''.join(random.choice(string.lowercase) for i in range(10))
            random_email+="@gmail.com"

            from random import randint
            sk8number=(randint(0,100))

            skill=str((randint(0,4)))

            new_sk8er=Registrant(skill=skill,con=con, state=state, country=country, first_name=first_name, last_name=last_name, sk8number=str(sk8number),sk8name=sk8name, gender=gender, email=random_email)
            new_sk8er.save()

        except:
            errorlist.append(datalist)

    if errorlist:
        f=open(old_rc_path+"Registrant Errors.csv", "wb")
        writer = csv.writer(f, delimiter=',', quoting=csv.QUOTE_ALL)
        for error in errorlist:
            writer.writerow(error)
        f.close()


def make_coaches():
    con=Con.objects.get(year="2015")

    csvfile=(old_rc_path+"coaches_data.csv")
    coach_list=[]

    with open(csvfile) as file1:
        data = csv.reader(file1, delimiter=',')
        rownumber=0
        info=[]
        errorlist=[]
        for row in data:
            rownumber = rownumber +1
            if rownumber >= 2:
                info.append(row)

    for datalist in info:
        try:
            sk8name=str(datalist[0])
            print "sk8name ",sk8name
            last_name=str(datalist[2])
            print "last_name ",last_name
            first_name=str(datalist[3])
            print "first_name ",first_name
            intl_str=str(datalist[4])
            print "intl_str",intl_str
            gender=str(datalist[5])
            print "gender",gender
            email=str(datalist[6])
            print "email",email
            country_str=str(datalist[8])
            print "country_str",country_str
            state_slugname=datalist[10]
            print "state_slugname",state_slugname
            coach_description=datalist[11]

            if not intl_str or len(intl_str)<1:
                intl=False
            else:
                intl=True

            if country_str:
                try:
                    country=Country.objects.get(name=country_str)
                except:
                    print "error finding country",country_str
                    country=Country.objects.get(name="United States")
            else:
                country=Country.objects.get(name="United States")

            if state_slugname:
                try:
                    state=State.objects.get(slugname=state_slugname)
                except:
                    print "error finding state",state_slugname
            else:
                state=None

            print "about to make coach"
            coach=None#to serest who it is

            r_query=Registrant.objects.filter(con=con,sk8name=sk8name)
            for entry in r_query:
                entry.delete()
            try:
                coach=Registrant.objects.get(con=con,email=email,first_name=first_name,last_name=last_name)
                sk8name=sk8name
                sk8number="X"
                skill="A"
                coach.country=country
                coach.state=state
                coach.gender=gender

            except:
                coach=Registrant(con=con,email=email,first_name=first_name,last_name=last_name,sk8name=sk8name,sk8number="X",skill="A",country=country,state=state,gender=gender)

            print "coach",coach

            coach.save()
            coach.save()#save twice to make sure has user?
            print "saved!"
            coach_list.append(coach)

            coach_object,created=Coach.objects.get_or_create(user=coach.user)
            coach_object.description=coach_description
            print "COACH OBJECT ",coach_object,coach_object.description
            coach_object.save()

        except:
            print "ERROR with ",sk8name
            errorlist.append(datalist)

    if errorlist:
        f=open(old_rc_path+"Coach Errors.csv", "wb")
        writer = csv.writer(f, delimiter=',', quoting=csv.QUOTE_ALL)
        for error in errorlist:
            writer.writerow(error)
        f.close()

    return "done! %s coaches!"%str(len(coach_list))

def swap_captain_name():
    csvfile=(new_rc_path+"Training.csv")
    training_list=[]

    with open(csvfile) as file1:
        data = csv.reader(file1, delimiter=',')
        rownumber=0
        info=[]
        errorlist=[]
        for row in data:
            rownumber = rownumber +1
            if rownumber >= 2:
                info.append(row)

    replacement_info=[]
    for datalist in info:
        training_pk=int(datalist[0])
        #print "training_pk",training_pk
        training=Training.objects.get(pk=training_pk)
        #print "training",training
        coach_names=training.display_coach_names()
        #print "coach_names",coach_names
        datalist[10]=coach_names
        #print "datalist",datalist
        replacement_info.append(datalist)

    f=open(new_rc_path+"TrainingCoaches.csv", "wb")
    writer = csv.writer(f, delimiter=',', quoting=csv.QUOTE_ALL)
    for data in replacement_info:
        writer.writerow(data)
    f.close()

def t_setup():
    con=Con.objects.get(pk=1)
    csvfile=(old_rc_path+"TrainingCoaches.csv")

    training_list=[]

    with open(csvfile) as file1:
        data = csv.reader(file1, delimiter=',')
        info=[]
        for row in data:
            info.append(row)

        for datalist in info:
            training_pk=int(datalist[0])
            name=datalist[1]
            location_type=datalist[2]
            RCaccepted_str=datalist[3]
            if RCaccepted_str:
                RCaccepted=True
            else:
                RCaccepted=False
            intl_str=datalist[4]
            if intl_str:
                intl=True
            else:
                intl=False
            skill=datalist[5]
            if skill in [0,"0"]:
                skill=None
            gender=datalist[6]
            duration=datalist[7]
            onsk8s_str=datalist[8]
            if onsk8s_str:
                onsk8s=True
            else:
                onsk8s=False
            contact_str=datalist[9]
            if contact_str:
                contact=True
            else:
                contact=False
            coach_names=datalist[10]
            coach_list=coach_names.split(', ')
            print "coach_list",coach_list
            description=datalist[11]

            print "about to make training"
            training=None#to serest who it is

            t_query=Training.objects.filter(name=name, con=con)
            if len(t_query)>=1:
                for entry in t_query:
                    entry.delete()


            print "A"
            training=Training(name=name,duration=duration,onsk8s=onsk8s,contact=contact,con=con,location_type=location_type,RCaccepted=RCaccepted,description=description)
            registered=Roster(gender=gender,skill=skill,intl=False,con=con)
            auditing=Roster(gender='NA/Coed',skill=None,intl=False,con=con)
            auditing.save()
            print "c"
            registered.save()
            print "d"

            training.save()
            registered.registered=training
            auditing.auditing=training
            registered.registered=training
            auditing.auditing=training
            auditing.save()
            registered.save()
            try:
                for coach_n in coach_list:
                    print "getting coach: ",coach_n

                    coach_list=Registrant.objects.filter(sk8name=coach_n, con=con)
                    coach=coach_list[0]
                    if len(coach_list)>1:
                        for item in coach_list[1:]:
                            item.delete()

                    user_coach=Coach.objects.get(user=coach.user)
                    training.coach.add(user_coach)
            except:
                pass

            training.save()
            print "training %s saved!"%(training)
            training_list.append(training)
    print "done! %s Trainings made"%(str(len(training_list)))

def make_groups():
    g1,created1=Group.objects.get_or_create(name="Khaleesi")
    g2,created2=Group.objects.get_or_create(name="Blood Rider")
    g3,created3=Group.objects.get_or_create(name="NSO")
    g4,created4=Group.objects.get_or_create(name="Volunteer")

def make_blog2():
    filename="Blog2.txt"
    file_path=os.path.join(static_path, filename)
    openfile = open(file_path)
    user=User.objects.get(first_name="Leggsn Bacon")
    post=openfile.read()
    b=Blog(headline ="General MVP Class Sign Up Rules and Regulations", user=user, post=post)
    b.save()

def make_blog3():
    current_working_dir=os.getcwd()
    filename="Blog3.txt"
    file_path=os.path.join(static_path, filename)
    openfile = open(file_path)
    user=User.objects.get(first_name="Dahmernatrix")
    post=openfile.read()
    b=Blog(headline ="FAQ", user=user, post=post)
    b.save()

def easy_pws(user_list):
    password="password"
    for u in user_list:
        u.set_password(password)
        u.save()

def set_pws(user_list,password):
    #user_list=list(User.objects.filter(username__in=["mdaizovi@gmail.com","denise.grimes@gmail.com","derbydish99@gmail.com","rollerconcoordinator@gmail.com"]))
    #password="@$$p3nn13$"
    for u in user_list:
        u.set_password(pw)
        u.save()
