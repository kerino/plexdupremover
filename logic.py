# -*- coding: utf-8 -*-
##########################################################
# python
import os
import traceback
import time
import threading
 
# third-party
 
# sjva 공용
from framework import db, scheduler, path_app_root
from framework.job import Job
from framework.util import Util
 
# 패키지
from .plugin import logger, package_name
from .model import ModelSetting, ModelItem
from .logic_normal import LogicNormal
#########################################################
 
 
class Logic(object):
 
    ## 보통 설정값 항목과 초기값을 넣어줍니다.
    db_default = { 
        'db_version' : '1',
        'interval' : '0 1 * * *',
        'auto_start' : 'False',
        'plex_server' : '',
        'plex_token' : '',
        'plex_library' : '',
        'telegram' : '',
        'audio_codec_scores' : "{'Unknown': 0, 'wmapro': 200, 'mp2': 500, 'mp3': 1000, 'ac3': 1000, 'dca': 2000, 'pcm': 2500, 'flac': 2500, 'dca-ma': 4000, 'truehd': 4500, 'aac': 1000, 'eac3': 1250}",
        'video_codec_scores' : "{'Unknown': 0, 'h264': 10000, 'h265': 5000, 'hevc': 5000, 'mpeg4': 500, 'vc1': 3000, 'vp9': 1000, 'mpeg1video': 250, 'mpeg2video': 250, 'wmv2': 250, 'wmv3': 250, 'msmpeg4': 100, 'msmpeg4v2': 100, 'msmpeg4v3': 100}",
        'video_resolution_scores' : "{'Unknown': 0, '4k': 20000, '1080': 10000, '720': 5000, '480': 3000, 'sd': 1000}",
        'move_flag' : 'False',
        'move_path' : ''
    }

    @staticmethod
    def db_init():
        try:
            for key, value in Logic.db_default.items():
                if db.session.query(ModelSetting).filter_by(key=key).count() == 0:
                    db.session.add(ModelSetting(key, value))
            db.session.commit()
            
            #Logic.migration()
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
 
    @staticmethod
    def plugin_load():
        try:
            ## 로딩시 호출됩니다. db초기화를 하고 자동실행 기능이 포함되면 이 곳에서 scheduler_start 호출
            logger.debug('%s plugin_load', package_name)
            Logic.db_init()
            if ModelSetting.query.filter_by(key='auto_start').first().value == 'True':
                Logic.scheduler_start()
            # 편의를 위해 json 파일 생성
            from plugin import plugin_info
            Util.save_from_dict_to_json(plugin_info, os.path.join(os.path.dirname(__file__), 'info.json'))
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
 
    ## 플러그인 종료시 실행됩니다. 
    @staticmethod
    def plugin_unload():
        try:
            logger.debug('%s plugin_unload', package_name)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
 
    ## 아래는 이 플러그인에서 사용되지 않아서 주석처리 되어 있습니다. 간단히 의미만 설명합니다.
    ## 플러그인 로딩시 자동실행이 있으면 이 함수를 호출합니다. 작업주기와 작업 함수를 스케쥴러에 등록합니다.

    @staticmethod
    def scheduler_start():
        try:
            logger.debug('PDR Scheduler start!')
            job = Job(package_name, package_name, ModelSetting.get('interval'), Logic.scheduler_function, u"%s 설명" % package_name, False)
            scheduler.add_job_instance(job)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
 
    ## 작업중지
    @staticmethod
    def scheduler_stop():
        try:
            scheduler.remove_job(package_name)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
 
    ## 스케쥴러에서 호출할 함수
    @staticmethod
    def scheduler_function():
        LogicNormal.scheduler_function()
 
    ## DB 모두 삭제
    @staticmethod
    def reset_db():
        try:
            db.session.query(ModelItem).delete()
            db.session.commit()
            return True
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return False
 
    ## 1회 실행
    @staticmethod
    def one_execute():
        try:
            if scheduler.is_include(package_name):
                if scheduler.is_running(package_name):
                    ret = 'is_running'
                else:
                    scheduler.execute_job(package_name)
                    ret = 'scheduler'
            else:
                def func():
                    time.sleep(2)
                    Logic.scheduler_function()
                threading.Thread(target=func, args=()).start()
                ret = 'thread'
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            ret = 'fail'
        return ret
""" 
    ## 텔레그램 봇 데이터 처리
    @staticmethod
    def process_telegram_data(data):
        try:
            logger.debug(data)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    ## DB 마이그레이션
    @staticmethod
    def migration():
        try:
            pass
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
"""
 
