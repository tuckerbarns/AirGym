# -*- coding: utf-8 -*-

def index():
    if auth.user:
        redirect(URL('main'))
    return dict()

def learn():
    return auth.wiki()

@auth.requires_login()
def main():
    sport = request.vars.sport
    if sport in auth.user.sports:
        session.sport = sport
    if not session.sport in auth.user.sports:
        session.sport = None
    if not session.sport and auth.user.sports:
        session.sport =  auth.user.sports[0]
    if not session.sport:
        session.flash = 'No Sport Selected'
        redirect(URL('user/profile'))
    if not auth.user.facilities:
        redirect(URL('preferences','facilities'))
    activity = db.activity(user_id=auth.user.id,sport=session.sport)
    if not activity:
        id = db.activity.insert(user_id=auth.user.id,sport=session.sport)
        activity = db.activity(id)
    session.activity = activity
    return dict()

def sport_preference():
    activity = session.activity
    form = SQLFORM(db.activity,activity,showid=False).process()
    return dict(form=form)

@auth.requires_login()
def home():
    user = db.auth_user(request.args(0,cast=int,default=auth.user.id))
    activities = db(db.activity.user_id==user.id).select()
    slots = db(db.user_availability.user_id==user.id)\
        (db.user_availability.start_datetime>request.now).select()
    response.h1 = user.full_name    
    return locals()

def compute_slots(facility_ids, sport):
    return slots

def status():
    if not session.activity:
        redirect(URL('main'))
    slots = db(db.timeslot.facility.belongs(auth.user.facilities))\
        (db.timeslot.sport==session.activity.sport)\
        (db.timeslot.start_datetime>request.now)\
        (db.timeslot.available==True).select(
        db.timeslot.start_datetime,
        db.timeslot.stop_datetime,
        db.timeslot.id.count().with_alias('spaces'),
        groupby=db.timeslot.start_datetime|db.timeslot.stop_datetime)
    return locals()

def check_friends():
    people = db(db.auth_user).select()
    return TABLE(*[TR(TD(INPUT(_type='checkbox',_id=p.id)),
                      TD(A(p.full_name,_href=URL('home',args=p.id),
                           _target="blank"))) for p in people])

@auth.requires_login()
def availability():
    a = db.user_availability
    import time
    a = db.user_availability
    if request.post_vars:
        id = request.post_vars.id or 0
        if request.post_vars.delete=='true':
            db(a.id==id)(a.user_id==auth.user.id).delete()
            return ''
        start = str2dt(request.post_vars.start)
        end = str2dt(request.post_vars.end)
        if id:
            print 'updating'
            db(a.id==id)(a.user_id==auth.user.id).update(
                start_datetime=start,stop_datetime=end)
        else:
            print 'creating'
            id = a.insert(start_datetime=start,stop_datetime=end)
        print id, start, end
        return str(id)
    # delete past availabilities
    db(a.user_id==auth.user.id)(a.stop_datetime<request.now).delete()
    # seelect future availaibility
    slots = db(
        (a.user_id==auth.user.id)
        &(a.start_datetime>request.now)
        ).select()
    return dict(slots=slots)

@auth.requires_login()
def reserve():
    start = datetime.datetime.strptime(request.vars.start,'%Y-%m-%d %H:%M:%S')
    print start
    slots = db(db.timeslot.facility.belongs(auth.user.facilities))\
        (db.timeslot.sport==session.activity.sport)\
        (db.timeslot.start_datetime==start)\
        (db.timeslot.available==True)\
        (db.timeslot.location==db.location.id).select(
        db.timeslot.start_datetime,db.timeslot.stop_datetime,
        db.location.ALL,
        db.timeslot.id.count().with_alias('spaces'),
        groupby=db.timeslot.location)
    return locals()
        
@auth.requires_login()
def reserve_slot():
    start_time = datetime.datetime.strptime(request.vars.start,'%Y-%m-%d %H:%M:%S')
    location = request.vars.location
    slot = db(db.timeslot.location==location)\
        (db.timeslot.start_datetime==start_time)\
        (db.timeslot.available==True)\
        .select(db.timeslot.ALL).first()
    if not slot:
        session.flash="not no longer available"
        redirect(URL('reserve',vars=dict(start=start_time.isoformat().replace('T',' '))))
    facility = db(db.location.id==slot.location)(db.facility.id==db.location.facility).select(db.facility.ALL).first()
    form = FORM(INPUT(_type='submit',_value='Confirm reservation',_class='btn')).process()
    if form.accepted:        
        slot.update_record(reserved_by=auth.user.id,
                           available=False,
                           pending=facility.proxy)
        if facility.proxy:
            reponse.flash='Reservation pending!'
            mail.send(to=facility.proxy_email,
                      subject='Pending reservation',
                      message=repr(slot))
        else:        
            response.flash='Reserved!'
        form = None
    return locals()

@auth.requires_login()
def my_reservations():
    slots = db(db.timeslot.reserved_by==auth.user.id)\
        (db.timeslot.start_datetime>request.now).select()
    return locals()

@auth.requires_login()
def cancel_reservation():
    """ not implemented """
    return locals()

def confirm_reservation():
    status = request.args(0)
    id = request.args(1,cast=int)    
    confirmation_key = request.args(2)
    s = db(db.timeslot.id==id)(db.timeslot.confirmation_key==confirmation_key)
    record = s.select().first()    
    if record and record.reserved_by:
        user = db.auth_user(record.reserved_by) if record.reserved_by else None
        if status=='confirm':            
            if user:
                mail.send(to=user.email,
                          subject='reservation confirmation',
                          message = str(record))
            record.update_record(pending=False)
            response.flash='reservation confirmed'
        elif status=='cancel':
            if user:
                mail.send(to=user.email,
                          subject='reservation cancelled',
                          message = str(record))
            record.update_record(pending=False,available=True)
            response.flash='reservation cancelled'
    return locals()

def user():
    """
    exposes:
    http://..../[app]/default/user/login
    http://..../[app]/default/user/logout
    http://..../[app]/default/user/register
    http://..../[app]/default/user/profile
    http://..../[app]/default/user/retrieve_password
    http://..../[app]/default/user/change_password
    use @auth.requires_login()
        @auth.requires_membership('group name')
        @auth.requires_permission('read','table name',record_id)
    to decorate functions that need access control
    """
    if request.args(0) in ('login','register','logout'):
        session.sport = session.activity = None
    return dict(form=auth())


def download():
    """
    allows downloading of uploaded files
    http://..../[app]/default/download/[filename]
    """
    return response.download(request, db)


def call():
    """
    exposes services. for example:
    http://..../[app]/default/call/jsonrpc
    decorate with @services.jsonrpc the functions to expose
    supports xml, json, xmlrpc, jsonrpc, amfrpc, rss, csv
    """
    return service()

@auth.requires_signature()
def data():
    """
    http://..../[app]/default/data/tables
    http://..../[app]/default/data/create/[table]
    http://..../[app]/default/data/read/[table]/[id]
    http://..../[app]/default/data/update/[table]/[id]
    http://..../[app]/default/data/delete/[table]/[id]
    http://..../[app]/default/data/select/[table]
    http://..../[app]/default/data/search/[table]
    but URLs must be signed, i.e. linked with
      A('table',_href=URL('data/tables',user_signature=True))
    or with the signed load operator
      LOAD('default','data.load',args='tables',ajax=True,user_signature=True)
    """
    return dict(form=crud())

