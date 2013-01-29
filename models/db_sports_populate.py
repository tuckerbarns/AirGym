from gluon.contrib.populate import populate
if DEVELOPMENT_MODE and db(db.auth_user).count()==2:
    populate(db.auth_user,100)
    
    populate(db.location,100)
    db(db.auth_user).update(
        city='Oak Park',
        state='IL',
        country='US',
        zip='60302')
    populate(db.facility,10)
    db(db.facility).update(owner=1)

