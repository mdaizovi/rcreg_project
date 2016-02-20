#from scheduler.models import Roster
def delete_homeless_roster(sender, instance,**kwargs):
    """upon deleting Challenge, checks to see if related rosters have other connections, if not, deletes them as well
    Not necessary for Training, d/t 1:1 """
    print "running delete_homeless_roster"
    my_rosters=[]
    print "my_rosters"
    if instance.roster1:
        my_rosters.append(instance.roster1)
    if instance.roster2:
        my_rosters.append(instance.roster2)
    for r in my_rosters:
        print "r",r
        connections=list(r.roster1.all())+list(r.roster2.all())
        print "connections",connections
        if len(connections)<=1:
            r.delete()


def adjust_captaining_no(sender, instance,**kwargs):
    '''upon deleting a roster, removes captain and saves registrant to adjust captain number.'''
    if instance.captain:
        captain=instance.captain
        instance.captain=None
        instance.save()
        captain.save()

def challenge_defaults(sender, instance,**kwargs):
    """This sents Challenge roster matching criteria defaults to something that'll allow the registrnt
    varies slightly depending on whether is game or not"""
    from con_event.models import GENDER,SKILL_LEVEL_CHG
    from scheduler.models import DEFAULT_CHALLENGE_DURATION,DEFAULT_SANCTIONED_DURATION,GAMETYPE,GAME_CAP
    #make a pre save so i don't have to also add save and make infinite loop
    print "running challenge_defaults"

    def set_mc(roster):
        """these are the default matching criteria I want forgames"""
        roster.skill=SKILL_LEVEL_CHG[0][0]
        roster.gender=GENDER[-1][0]
        roster.intl=False
        roster.save()

    if instance.is_a_game:
        print "CD is a game"#I think maybr this doesn't run the first time, becasue isn't a game yet.
        instance.gametype=GAMETYPE[-1][0]
        if not instance.duration:
            instance.duration=DEFAULT_SANCTIONED_DURATION
        for r in [instance.roster1,instance.roster2]:
            if r:
                set_mc(r)
                r.cap=GAME_CAP
    else:
        if not instance.duration:
            instance.duration=DEFAULT_CHALLENGE_DURATION
