# -*- coding: utf-8 -*-

def home():
    return dict(facility=db.facility(request.args(0,cast=int)))

@auth.requires_login()
def manage():
    response.h1 = 'Facility Management'
    db.facility.owner.default = auth.user_id
    if request.args(1)=='location_availability.facility':
        facility = int(request.args(2))
        options = db(db.location.facility==facility).select().as_dict()
        requires = IS_IN_SET([(k,v['name']) for (k,v) in options.iteritems()],
                             multiple=True)
        db.location_availability.locations.requires=requires
    
    grid = SQLFORM.smartgrid(
        db.facility,
        fields={'facility':[db.facility.id,db.facility.name]},
        constraints={'facility':db.facility.owner==auth.user_id},
        links={'facility':[lambda row: A('Recompute',_href=URL('update_slots',args=row.id))],
               'location':[lambda row: A('Availability',_href=URL('location_availability',args=row.id))],
},
        csv=False,
        )
    return locals()

@auth.requires_login()
def update_slots():
    facility = db.facility(request.args(0,cast=int),owner=auth.user.id)
    compute_slots(facility.id,7)
    session.flash = "slots recomputed for 7 days"
    redirect(URL('manage'))


def compute_slots(facility_id,ndays=7):
    """
    this is a critical function if finds all available slots for sport at facility_ids
    it returns a list of 
    [..., (start_datetime, stop_datetime, availablities), ...]
    for each slot availabilities is a list 
    [..., (location.id, location.name, free_capacity), ...]

    Note to self:
    this should be re-done using a temp table for slots for each facility
    updated when a facility is updated or a new reservation is made
    perhaps the info should be cached in ram, perhaps in db
    anyway, we output is ok so this is a reference implementation
    """
    db(db.timeslot.facility==facility_id)(db.timeslot.available==True).delete()
    dlocations = db(db.location.facility==facility_id).select().as_dict(storage_to_dict=False)
    loc_ids = set(dlocations.keys())
    la = db.location_availability    
    today = datetime.date.today()
    slots = db((la.facility==facility_id)&(la.stop_date>today)).select()
    open = slots.find(lambda row: (
        row.open_status == 'open' and set(row.locations).intersection(loc_ids)))
    closed = slots.find(lambda row: (
        row.open_status == 'closed' and set(row.locations).intersection(loc_ids)))
    events = {}
    td = datetime.timedelta
    WEEKDAYS=['monday','tuesday','wednesday','thursday','friday','saturday','sunday']
    slots = []
    for item in open:
        d0 = max(datetime.date.today(),item.start_date)
        d1 = min(item.stop_date,today+td(days=ndays))
        for k in range((d1-d0).days+1):
            d = d0 + td(days=k)
            ds = datetime.datetime.combine(d,item.start_time)
            weekday = WEEKDAYS[d.weekday()]
            if not item[weekday]:
                continue # does not look like the facility is open
            dt = (60*(item.stop_time.hour-item.start_time.hour)+
                  item.stop_time.minute-item.start_time.minute)
            for t in range(0,dt,item.activity_duration):
                start_datetime = ds + td(seconds=60*t)
                if start_datetime<request.now:
                    continue # this slot is in the past
                stop_datetime = start_datetime + td(seconds=60*item.activity_duration)
                locations = item.locations
                daytime = datetime.time(start_datetime.hour,start_datetime.minute)
                for other in closed:
                    if other.start_date <= d <= other.stop_date and \
                            other[weekday] and \
                            other.start_time <= daytime < other.stop_time:
                        # this location in facility is closed
                        locations = [c for c in locations if not c in other.locations]
                availabilities = []
                for location_id in locations:
                    location = dlocations.get(location_id,None)
                    if not location:
                        continue # something broken, ignore the location
                    n=location.capacity
                    n -= db(db.timeslot.location==location.id)\
                        (((db.timeslot.start_datetime<=start_datetime)
                          &(db.timeslot.stop_datetime>start_datetime))|
                         ((db.timeslot.start_datetime<stop_datetime)
                          &(db.timeslot.stop_datetime>=start_datetime)))\
                          (db.timeslot.available==False).count()
                    for k in xrange(n):
                        db.timeslot.insert(                           
                            facility=facility_id,
                            location=location.id,
                            sport=location.sport,
                            start_datetime=start_datetime,
                            stop_datetime=stop_datetime)
                db.commit()            

@auth.requires_login()
def location_availability():
    location = db.location(request.args(0,cast=int)) or redirect(URL('manage'))
    facility = db.facility(location.id,owner=auth.user.id) or redirect(URL('manage'))
    slots = db(db.timeslot.location==location.id)\
        (db.timeslot.start_datetime>request.now).select(
        db.timeslot.start_datetime,
        db.timeslot.stop_datetime,
        db.timeslot.id.count().with_alias('spaces'),
        groupby=db.timeslot.start_datetime|db.timeslot.stop_datetime)
    return locals()
