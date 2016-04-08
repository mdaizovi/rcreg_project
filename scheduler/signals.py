#from scheduler.models import Roster
def delete_homeless_roster_chg(sender, instance,**kwargs):
    """upon deleting Challenge, checks to see if related rosters have other connections, if not, deletes them as well
    Not necessary for Training, d/t 1:1 """
    #print "starting delete_homeless_roster_chg"
    my_rosters=[]
    if instance.roster1:
        my_rosters.append(instance.roster1)
    if instance.roster2:
        my_rosters.append(instance.roster2)
    for r in my_rosters:
        if r.id and not r.name and not r.captain:
            connections=list(r.roster1.all())+list(r.roster2.all())
            if len(connections)<=1:
                #print "this si where I would delete ",r
                r.delete()

def delete_homeless_roster_ros(sender, instance,**kwargs):
    """Post Save from Roster
    Deletes a Roster if it has no Captain and no Challenges or Trainings"""
    print "running delete_homeless_roster_ros("
    my_connections=list(instance.roster1.all())+list(instance.roster2.all())
    if instance.registered:
        my_connections.append(instance.registered)
    if instance.auditing:
        my_connections.append(instance.auditing)
    if len(my_connections)<1 and not instance.captain and not instance.registered and not instance.auditing:
        #print "about to delete ",instance
        #print "this is where I WOULD delete ",instance
        instance.delete()

def delete_homeless_chg(sender, instance,**kwargs):
    """Deletes Challenge if it has no Rosters"""
    if not instance.roster1 and not instance.roster2:
        #print "about to delete homeless challenge",instance
        #print "delete_homeless_chg: this is where I WOULD delete ",instance
        instance.delete()


def adjust_captaining_no(sender, instance,**kwargs):
    '''upon deleting a roster, removes captain and saves registrant to adjust captain number.'''
    #somehow this is related to why my User name would change after I deleted all of the Registrant's rosters,
    #But I'm still nt sure why. Registrant didn't get deleted did it?
    #actualy cap number is realted to chalenges, not rosters. this should run when a cap leaves/delets a challenge, or not at all
    #print "deleting roster, running adjust captain number"
    if instance.captain:
        captain=instance.captain
        instance.captain=None
        captain.save()

def challenge_defaults(sender, instance,**kwargs):
    """Pre-save Challenge
    This sents Challenge roster matching criteria defaults to something that'll allow the registrnt
    varies slightly depending on whether is game or not"""
    from con_event.models import GENDER,SKILL_LEVEL_CHG
    from scheduler.models import DEFAULT_CHALLENGE_DURATION,DEFAULT_SANCTIONED_DURATION,GAMETYPE,GAME_CAP
    #make a pre save so i don't have to also add save and make infinite loop
    #print "starting chal defaults"
    def set_mc(roster):
        """these are the default matching criteria I want forgames"""
        roster.skill=SKILL_LEVEL_CHG[0][0]#no skill restricitons
        roster.gender=GENDER[-1][0]#na coed
        roster.intl=False

    if instance.is_a_game:
        instance.gametype=GAMETYPE[-1][0]
        if not instance.duration:
            instance.duration=DEFAULT_SANCTIONED_DURATION
    for r in [instance.roster1,instance.roster2]:
        if r and not r.cap:
            r.cap=GAME_CAP
            if instance.is_a_game:
                set_mc(r)
            #print "about to save",r
            r.save()
    else:
        if not instance.duration:
            instance.duration=DEFAULT_CHALLENGE_DURATION
