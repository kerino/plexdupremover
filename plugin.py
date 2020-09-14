# -*- coding: utf-8 -*-
#########################################################
# python
import os
import traceback
 
# third-party
from flask import Blueprint, request, render_template, redirect, jsonify 
from flask_login import login_required
 
# sjva 공용
from framework.logger import get_logger
from framework import app, db, scheduler, path_data, socketio, check_api
from system.model import ModelSetting as SystemModelSetting
 
# 패키지
package_name = __name__.split('.')[0]
logger = get_logger(package_name)
from .logic import Logic
from .model import ModelSetting, ModelItem
#########################################################
 
## Framework 에서 사용하는 것들
blueprint = Blueprint(package_name, package_name, url_prefix='/%s' %  package_name, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
## blueprint는 고정입니다. 변경하지 마세요
 
## SJVA 메뉴에서 어떻게 나타날것인가에 대한 dict입니다.
menu = {
    'main' : [package_name, 'PLEX DUP Remover'],
    'sub' : [
        ['setting', '설정'], ['list', '목록'], ['log', '로그']
    ],
    'category' : 'plex'
}
 
## 설정 - 플러그인 에서 보여줄 정보를 포함하고 있습니다.
plugin_info = {
    'version' : '0.1.0.1',
    'name' : 'PLEX DUP Remover',
    'category_name' : 'plex',
    'developer' : 'kerino',
    'description' : 'PLEX 중복 파일 삭제',
    'home' : 'https://github.com/kerino/plexdupremover',
    'more' : '',
}
 
## 보통 Logic 에서 일처리를 합니다.
def plugin_load():
    Logic.plugin_load()
 
def plugin_unload():
    Logic.plugin_unload()
 
#########################################################
# WEB Menu   
#########################################################
## /package_name 으로만 접속할 때 어느 sub 화면으로 보낼지 설정합니다. 
@blueprint.route('/')
def home():
    return redirect('/%s/setting' % package_name)
 
## 메뉴가 클릭되었을때 어떤 정보를 가공하여 어떤 html 페이지를 보여줄지 선택합니다.
@blueprint.route('/<sub>')
@login_required
def first_menu(sub): 
    ## setting 메뉴가 호출되면
    if sub == 'setting':
        ## 화면에 보여줄 모든 정보를 arg 에 넣습니다.
        arg = ModelSetting.to_dict()
        arg['package_name']  = package_name
        arg['scheduler'] = str(scheduler.is_include(package_name))
        arg['is_running'] = str(scheduler.is_running(package_name))
        return render_template('{package_name}_{sub}.html'.format(package_name=package_name, sub=sub), arg=arg)
    ## 아래 로그와 샘플을 그대로 사용
    elif sub == 'list':
        arg = {}
        arg['package_name']  = package_name
        return render_template('{package_name}_{sub}.html'.format(package_name=package_name, sub=sub), arg=arg)
    elif sub == 'log':
        return render_template('log.html', package=package_name)
    return render_template('sample.html', title='%s - %s' % (package_name, sub))
 
#########################################################
# For UI                                                          
#########################################################
## 웹에서 사용자가 무언가를 요청하였을 경우 이 곳을 통해 받아서 처리하고 그 결과를 리턴합니다.
## 보통 jsonify 를 통해 json 형태로 리턴합니다.
@blueprint.route('/ajax/<sub>', methods=['GET', 'POST'])
## 이 데코레이터 필수
@login_required
def ajax(sub):
    try:
        ## 사용자가 설정 저장버튼을 눌렀을 경우 
        if sub == 'setting_save':
            ret = ModelSetting.setting_save(request)
            return jsonify(ret)
        elif sub == 'scheduler':
            go = request.form['scheduler']
            logger.debug('scheduler :%s', go)
            if go == 'true':
                Logic.scheduler_start()
            else:
                Logic.scheduler_stop()
            return jsonify(go)
        elif sub == 'one_execute':
            ret = Logic.one_execute()
            return jsonify(ret)
        elif sub == 'reset_db':
            ret = Logic.reset_db()
            return jsonify(ret)

        elif sub == 'web_list':
            ret = ModelItem.web_list(request)
            return jsonify(ret)
    except Exception as e: 
        logger.error('Exception:%s', e)
        logger.error(traceback.format_exc())  
 
