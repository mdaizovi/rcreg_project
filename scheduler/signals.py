
def delete_homeless_roster_chg(sender, instance,**kwargs):
    """Challenge Pre-delete. upon deleting Challenge, checks to see if related rosters have other connections, if not, deletes them as well
    Not necessary for Training, d/t 1:1 """
    print "starting delete_homeless_roster_chg"
    my_rosters=[]
    caps=[]
    if instance.roster1:
        my_rosters.append(instance.roster1)
        if instance.roster1.captain:
            caps.append(instance.roster1.captain)
    if instance.roster2:
        my_rosters.append(instance.roster2)
        if instance.roster2.captain:
            caps.append(instance.roster2.captain)
    for r in my_rosters:
        if r.id:
            connections=list(r.roster1.all())+list(r.roster2.all())
            if len(connections)<=1:#1 because this challenge hasn't been deleted yet.
                r.delete()

    for c in caps:#to adjust captain number
        c.save()


def delete_homeless_roster_ros(sender, instance,**kwargs):
    """Post Save from Roster
    Deletes a Roster if it has no Captain and no Challenges"""
    print "running delete_homeless_roster_ros("
    my_connections=list(instance.roster1.all())+list(instance.roster2.all())

    if len(my_connections)<1 and not instance.captain:
        instance.delete()

def delete_homeless_chg(sender, instance,**kwargs):
    """Post-Save. Deletes Challenge if it has no Rosters"""
    if not instance.roster1 and not instance.roster2:
        instance.delete()


def adjust_captaining_no(sender, instance,**kwargs):
    '''Pre-Delete on Roster. Upon deleting a roster, removes captain and saves registrant to adjust captain number.'''
    #somehow this is related to why my User name would change after I deleted all of the Registrant's rosters,
    #But I'm still not sure why.
    #actualy cap number is realted to chalenges, not rosters. this should run when a captain leaves/deletes a challenge, or not at all
    # print "deleting roster, running adjust captain number"
    # if instance.captain:
    #     captain=instance.captain
    #     instance.captain=None
    #     captain.save()
    pass
    #want to mke sure all is good before i delete forever. this didn't work'


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
        #this is dumb. I should have jsut made it not look for matching criteria in game rosters
        #or maybe not, bc what if someone accidentlal ymakes it a non-game and then people get kicked off the roster?
        roster.skill=SKILL_LEVEL_CHG[0][0]#no skill restricitons
        roster.gender=GENDER[-1][0]#na coed
        roster.intl=False

    if instance.gametype=="6GAME":
        instance.is_a_game=True
        instance.duration=DEFAULT_SANCTIONED_DURATION
    else:
        instance.is_a_game=False
        if instance.gametype=="6CHAL":
            instance.duration=DEFAULT_SANCTIONED_DURATION
        elif instance.gametype in ["3CHAL","36CHAL"]:
            instance.duration=DEFAULT_CHALLENGE_DURATION

    for r in [instance.roster1,instance.roster2]:
        if r and not r.cap:
            r.cap=GAME_CAP
            if instance.is_a_game:
                set_mc(r)
            #print "about to save",r
            r.save()
