import datetime, time

me = auth.user_id

# a facility is a gym which offers one or more location for different sports
db.define_table(
    'facility',
    HField('owner','reference auth_user',default=me),
    Field('name',required=True,unique=True),
    Field('address'),
    Field('city'),
    Field('zip'),
    Field('state',requires=IS_IN_SET(STATES)),
    Field('country',default='US'),
    Field('phone'),
    Field('email'),
    Field('home_page',requires=IS_EMPTY_OR(IS_URL())),
    Field('proxy','boolean',default=False),
    Field('proxy_email'),
    format='%(name)s')

# a location is, for example, a room in a facility dedicated to a sport
db.define_table(
    'location',
    HField('facility','reference facility'),
    Field('sport',requires=IS_IN_SET(SPORTS)),
    Field('name',required=True),
    Field('equipment_rental','boolean',default=True),
    Field('hourly_rate','double',default=10),
    Field('info','text'),
    Field('capacity','integer',default=1),
    format='%(name)s (%(id)s/%(sport)s/%(facility)s)')

# list of time slots for each location
db.define_table(
    'location_availability',
    HField('facility','reference facility'),
    Field('locations', 'list:reference location'),
    Field('open_status',requires=IS_IN_SET(('open','closed'))),
    Field('start_date','date'),
    Field('stop_date','date'),
    Field('start_time','time'),
    Field('stop_time','time'),
    Field('monday','boolean',default=True),
    Field('tuesday','boolean',default=True),
    Field('wednesday','boolean',default=True),
    Field('thursday','boolean',default=True),
    Field('friday','boolean',default=True),
    Field('saturday','boolean',default=True),
    Field('sunday','boolean',default=True),
    Field('hourly_rate','double'),
    Field('activity_duration','integer',default=60,requires=IS_INT_IN_RANGE(15,240)))

db.define_table(
    'timeslot',
    Field('facility','reference facility',writable=False), # denorm
    Field('location','reference location',writable=False),
    Field('sport'),                                        # denorm
    Field('start_datetime','datetime'),
    Field('stop_datetime','datetime'),
    Field('info','text'),
    Field('pending','boolean',default=False),
    HField('confirmation_key',default=''),
    Field('available','boolean',default=True),
    Field('reserved_by','reference auth_user',default=None))

# each user is interested in one or more activities (an activity is a sport)
db.define_table(
    'activity',
    HField('user_id','reference auth_user',default=me),
    HField('sport',requires=IS_IN_SET(SPORTS)),
    Field('level',requires=IS_IN_SET(LEVELS),default=LEVELS[0]),
    HField('hourly_rate','double',default=10),
    HField('info','text'),
    ) # a python dict

db.define_table(
    'user_facility',
    Field('user_id','reference auth_user'),
    Field('facility_id','reference facility'))

# the user has time slots dedicated to the activity
db.define_table(
    'user_availability',
    HField('user_id','reference auth_user',default=me),
    Field('start_datetime','datetime'),
    Field('stop_datetime','datetime'))


# when a new user registers or edit profiles, update his list of activities
def profile_onaccept(form):
    dbset = db(db.activity.user_id==form.vars.id)
    activities = dbset.select()
    names = [a.sport for a in activities]
    db(db.activity.user_id==auth.user.id).delete()
    for name in form.vars.sports:
        db.activity.insert(user_id=auth.user.id,sport=name)
    if session.activity and not session.activity.sport in form.vars.sports:
        del session.activity

auth.settings.profile_onaccept = profile_onaccept
auth.settings.register_onaccept = profile_onaccept

# if a user is logged in display a menu with available activities
response.menu = []
if auth.user:
    response.menu.append(
        ('Sports',None,None,
         [(sport,None,URL('default','main',vars=dict(sport=sport))) 
          for sport in auth.user.sports]+
         [('[edit profile]',None,URL('default','user/profile'))]))
    if session.activity:
        response.menu.append(
            ('Preferences',None,None,
             [('Facilities',None,URL('preferences','facilities')),
              ('Availability',None,URL('default','availability')),
              ('Profile',None,URL('default','user/profile')),
              ('Sport Level',None,URL('default','sport_preference'))
              ]))
        response.menu.append(
            ('People',None,None,
             [('Search',None,URL('plugin_social','search')),
              ('Friends',None,URL('plugin_social','friends'))]))
        response.menu.append(
            ('Locations',None,URL('default','status')))
    if auth.user.facility_owner:
        response.menu.append(
            ('Facility Management',None,URL('facilities','manage')))

if auth.user and not hasattr(auth.user,'facilities'):
    _ = db(db.user_facility.user_id==me)\
        (db.user_facility.facility_id==db.facility.id).select(db.facility.ALL)
    auth.user.facilities = dict((f.id,f.name) for f in _)

# example: reserve(datetime.datetime(2012,12,15,8),datetime.datetime(2012,12,15,9),1)

def str2dt(s): return datetime.datetime(*(time.strptime(s,"%Y-%m-%d %H:%M")[0:5]))
