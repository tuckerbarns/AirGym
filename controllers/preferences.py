# -*- coding: utf-8 -*-

@auth.requires_login()
def facilities():    
    if not session.facilities:
        response.flash = "You must associate some facilities to your account"
    form = SQLFORM.factory(Field(
            'name',requires=IS_NOT_EMPTY(),label='Search by Name'))
    if form.process().accepted:
        query = db.facility.name.contains(form.vars.name)
    else:
        query = db.facility.id.belongs(auth.user.facilities.keys())
        query = query|((db.facility.country==auth.user.country)
                       &(db.facility.state==auth.user.state)
                       &(db.facility.zip.startswith(auth.user.state[2:])))
    if form.errors:
        response.flash = form.errors.name
        form.errors.clear()
    facilities = db(query).select(orderby=db.facility.name)
    return locals()

@auth.requires_login()
def callback_facility():
    command, id = request.args(0), request.args(1,cast=int)
    f = db.user_facility
    facilities = auth.user.facilities
    if command=='add' and not id in facilities:
        f.insert(user_id=auth.user.id,facility_id=id)                     
        facilities[id] = db.facility[id].name
    elif command=='del' and id in facilities:
        db(f.user_id==auth.user.id)(f.facility_id==id).delete()
        del facilities[id]
    return 'true' if id in facilities else 'false'



