from con_event.models import GENDER, SKILL_LEVEL_CHG
from scheduler.app_settings import DEFAULT_CHALLENGE_DURATION, DEFAULT_SANCTIONED_DURATION

#-------------------------------------------------------------------------------
def delete_homeless_roster_chg(sender, instance, **kwargs):
    """pre_delete from challenge. Checks to see if related rosters have other
    connections, if not, deletes them as well. Shoulh have made rosters 1:1
    instead of fk, but don't care to introduce new bugs by changing.
    """

    my_rosters = []
    caps = []

    for r in [instance.roster1, instance.roster2]:
        if r:
            my_rosters.append(r)
            if r.captain:
                caps.append(r.captain)

    for r in my_rosters:
        if r.id:
            connections = list(r.roster1.all()) + list(r.roster2.all())
            if len(connections) == 1:  # This challenge hasn't deleted yet
                r.delete()

    for c in caps:  # To adjust captain number
        c.save()


#-------------------------------------------------------------------------------
def delete_homeless_roster_ros(sender, instance, **kwargs):
    """post_save from roster.
    Deletes a Roster if it has no captain and no challenges.
    """

    my_connections = list(instance.roster1.all()) + list(instance.roster2.all())
    if len(my_connections) <1 and not instance.captain:
        instance.delete()

#-------------------------------------------------------------------------------
def delete_homeless_chg(sender, instance, **kwargs):
    """post_save. Deletes challenge if it has no rosters."""

    if not instance.roster1 and not instance.roster2:
        instance.delete()

#-------------------------------------------------------------------------------
def challenge_defaults(sender, instance, **kwargs):
    """pre_save from challenge. If it's a game, sets defaults to
    no skill or gender restrictions.
    """
    #  Avoid parallel import
    from scheduler.models import GAMETYPE

    if instance.gametype == "6GAME":
        instance.duration = DEFAULT_SANCTIONED_DURATION
    else:
        if instance.gametype == "6CHAL":
            instance.duration = DEFAULT_SANCTIONED_DURATION
        elif instance.gametype in ["3CHAL", "36CHAL"]:
            instance.duration = DEFAULT_CHALLENGE_DURATION
