# -*- coding: utf-8 -*-
##########################################################
# python
import traceback
from datetime import datetime
import json
import os

# third-party
from sqlalchemy import or_, and_, func, not_, desc
from sqlalchemy.orm import backref

# sjva 공용
from framework import app, db, path_app_root
from framework.util import Util

# 패키지
from .plugin import logger, package_name

app.config['SQLALCHEMY_BINDS'][package_name] = 'sqlite:///%s' % (os.path.join(path_app_root, 'data', 'db', '%s.db' % package_name))
#########################################################

class ModelSetting(db.Model):
    __tablename__ = '%s_setting' % package_name
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = package_name

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String, nullable=False)

    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __repr__(self):
        return repr(self.as_dict())

    def as_dict(self):
        return {x.name: getattr(self, x.name) for x in self.__table__.columns}

    @staticmethod
    def get(key):
        try:
            return db.session.query(ModelSetting).filter_by(key=key).first().value.strip()
        except Exception as e:
            logger.error('Exception:%s %s', e, key)
            logger.error(traceback.format_exc())


    @staticmethod
    def get_int(key):
        try:
            return int(ModelSetting.get(key))
        except Exception as e:
            logger.error('Exception:%s %s', e, key)
            logger.error(traceback.format_exc())

    @staticmethod
    def get_bool(key):
        try:
            return (ModelSetting.get(key) == 'True')
        except Exception as e:
            logger.error('Exception:%s %s', e, key)
            logger.error(traceback.format_exc())

    @staticmethod
    def set(key, value):
        try:
            item = db.session.query(ModelSetting).filter_by(key=key).with_for_update().first()
            if item is not None:
                item.value = value.strip()
                db.session.commit()
            else:
                db.session.add(ModelSetting(key, value.strip()))
        except Exception as e:
            logger.error('Exception:%s %s', e, key)
            logger.error(traceback.format_exc())

    @staticmethod
    def to_dict():
        try:
            from framework.util import Util
            return Util.db_list_to_dict(db.session.query(ModelSetting).all())
        except Exception as e:
            logger.error('Exception:%s %s', e, key)
            logger.error(traceback.format_exc())

    @staticmethod
    def setting_save(req):
        try:
            for key, value in req.form.items():
                if key in ['scheduler', 'is_running']:
                    continue
                if key.startswith('tmp_'):
                    continue
                logger.debug('Key:%s Value:%s', key, value)
                entity = db.session.query(ModelSetting).filter_by(key=key).with_for_update().first()
                entity.value = value
            db.session.commit()
            return True                  
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            logger.debug('Error Key:%s Value:%s', key, value)
            return False

    @staticmethod
    def get_list(key):
        try:
            value = ModelSetting.get(key)
            values = [x.strip().strip() for x in value.replace('\n', '|').split('|')]
            values = Util.get_list_except_empty(values)
            return values
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            logger.error('Error Key:%s Value:%s', key, value)









class ModelItem(db.Model):
    __tablename__ = '%s_item' % package_name
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = package_name

    id = db.Column(db.Integer, primary_key=True)
    deleteTime = db.Column(db.DateTime)
    plexSection = db.Column(db.String)
    filePath = db.Column(db.String)
    status = db.Column(db.String)
    
    def __init__(self):
        self.deleteTime = datetime.now()

    def as_dict(self):
        ret = {x.name: getattr(self, x.name) for x in self.__table__.columns}
        ret['deleteTime'] = self.deleteTime.strftime('%Y-%m-%d %H:%M:%S')

        return ret

    @staticmethod
    def save_as_dict(item):
        try:
            entity = ModelItem()
            entity.plexSection = unicode(item['section'])
            entity.filePath = unicode(item['file'][0])
            if ModelSetting.get('move_flag') == 'True':
                entity.status = unicode('이동')
                entity.filePath = entity.filePath + ' -> ' + ModelSetting.get('move_path')
            else:
                entity.status = unicode('삭제')
            db.session.add(entity)
            db.session.commit()
        except Exception as e:
            logger.debug(item)
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def web_list(req):
        try:
            ret = {}
            page = 1
            page_size = 30
            search = ''
            if 'page' in req.form:
                page = int(req.form['page'])
            if 'search_word' in req.form:
                search = req.form['search_word']
            order = req.form['order'] if 'order' in req.form else 'desc'
            query = ModelItem.make_query(search=search, order=order)
            count = query.count()
            query = query.limit(page_size).offset((page-1)*page_size)
            lists = query.all()
            ret['list'] = [item.as_dict() for item in lists]
            ret['paging'] = Util.get_paging_info(count, page, page_size)
            return ret
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def make_query(search, order):
        query = db.session.query(ModelItem)
        if search is not None and search != '':
            if search.find('|') != -1:
                conditions = []
                for tt in search.split('|'):
                    if tt != '': conditions.append(ModelItem.filePath.like('%'+tt.strip()+'%'))
                query = query.filter(or_(*conditions))
            elif search.find(',') != -1:
                for tt in search.split('|'):
                    if tt != '': query = query.filter(ModelItem.filePath.like('%'+tt.strip()+'%'))
            else:
                query = query.filter(ModelItem.filePath.like('%'+search+'%'))

        if order == 'desc':
            query = query.order_by(desc(ModelItem.id))
        else:
            query = query.order_by(ModelItem.id)
        return query