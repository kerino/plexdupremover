# -*- coding: utf-8 -*-
##########################################################
# python
import os
import sys
import datetime
import traceback
import threading
import re
import subprocess
import shutil
import json
import ast
import time
import urllib
import rclone
#import platform
#import daum_tv

# third-party
from sqlalchemy import desc
from sqlalchemy import or_, and_, func, not_
from guessit import guessit

# sjva 공용
import framework.common.celery as celery_shutil
from framework import app, db, scheduler, path_app_root, celery
from framework.job import Job
from framework.util import Util
from system.model import ModelSetting as SystemModelSetting
from framework.logger import get_logger

# 패키지
from .plugin import logger, package_name
from .model import ModelSetting, ModelItem

# Plexaip
from plexapi.server import PlexServer

# urllib
try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin

# requests
import requests

class LogicNormal(object):

    @staticmethod
    @celery.task
    def scheduler_function():
        try:
            plex = LogicNormal.get_plex_server()
            section = ModelSetting.get('plex_library')
            if section is not None and section != '':
                sections = []
                if section.find('|') != -1:
                    for sec in section.split('|'):
                        if sec != '': sections.append(sec)
                else:
                    sections = section
            else:
                logger.debug('Library 정보 없음')
            for sec in sections:
                dup = LogicNormal.get_dup(plex, sec)
                for item in dup:
                    parts = {}
                    for part in item.media:
                        part_info = LogicNormal.get_media_info(part)
                        part_info['score'] = LogicNormal.get_score(part_info)
                        part_info['show_key'] = item.key
                        part_info['section'] = sec
                        parts[part_info['id']] = part_info
                        logger.debug('ID : %s, Score : %s', part.id, part_info.get('score'))
                    items = sorted(parts.items(), key=lambda x: x[1]['score'], reverse=False)
                    logger.debug(ModelSetting.get('move_flag'))
                    if ModelSetting.get('move_flag') == 'True':
                        LogicNormal.move_item(items[0][1])
                    else:
                        LogicNormal.delete_item(items[0][1])
            
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def get_plex_server():
        try:
            plex = PlexServer(ModelSetting.get('plex_server'), ModelSetting.get('plex_token'))
            return plex
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def get_section_type(plex, sectionName):
        try:
            section_type = plex.library.section(sectionName).type
            return 'episode' if section_type == 'show' else 'movie'
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def get_dup(plex, sectionName):
        try:
            section_type = LogicNormal.get_section_type(plex, sectionName)
            dup = plex.library.section(sectionName).search(duplicate=True, libtype=section_type)
            
            return dup
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())            
        
    @staticmethod
    def get_score(media_info):
        score = 0
        audio_codec_scores = eval(ModelSetting.get('audio_codec_scores'))
        video_codec_scores = eval(ModelSetting.get('video_codec_scores'))
        video_resolution_scores = eval(ModelSetting.get('video_resolution_scores'))

        # score audio codec
        for codec, codec_score in audio_codec_scores.items():
            if codec.lower() == media_info['audio_codec'].lower():
                score += int(codec_score)
                #logger.debug("Added %d to score for audio_codec being %r", int(codec_score), str(codec))
                break
        # score video codec
        for codec, codec_score in video_codec_scores.items():
            if codec.lower() == media_info['video_codec'].lower():
                score += int(codec_score)
                #logger.debug("Added %d to score for video_codec being %r", int(codec_score), str(codec))
                break
        # score video resolution
        for resolution, resolution_score in video_resolution_scores.items():
            if resolution.lower() == media_info['video_resolution'].lower():
                score += int(resolution_score)
                #logger.debug("Added %d to score for video_resolution being %r", int(resolution_score), str(resolution))
                break
        # add bitrate to score
        score += int(media_info['video_bitrate']) * 2
        #logger.debug("Added %d to score for video bitrate", int(media_info['video_bitrate']) * 2)
        # add duration to score
        score += int(media_info['video_duration']) / 300
        #logger.debug("Added %d to score for video duration", int(media_info['video_duration']) / 300)
        # add width to score
        score += int(media_info['video_width']) * 2
        #logger.debug("Added %d to score for video width", int(media_info['video_width']) * 2)
        # add height to score
        score += int(media_info['video_height']) * 2
        #logger.debug("Added %d to score for video height", int(media_info['video_height']) * 2)
        # add audio channels to score
        score += int(media_info['audio_channels']) * 1000
        #logger.debug("Added %d to score for audio channels", int(media_info['audio_channels']) * 1000)
        # add file size to score
        score += int(media_info['file_size']) / 100000
        #logger.debug("Added %d to score for total file size", int(media_info['file_size']) / 100000)
        return int(score)

    @staticmethod
    def get_media_info(item):
        info = {
            'id': 'Unknown',
            'video_bitrate': 0,
            'audio_codec': 'Unknown',
            'audio_channels': 0,
            'video_codec': 'Unknown',
            'video_resolution': 'Unknown',
            'video_width': 0,
            'video_height': 0,
            'video_duration': 0,
            'file': [],
            'multipart': False,
            'file_size': 0
        }
        # get id0
        try:
            info['id'] = item.id
        except AttributeError:
            logger.debug("Media item has no id")
        # get bitrate
        try:
            info['video_bitrate'] = item.bitrate if item.bitrate else 0
        except AttributeError:
            logger.debug("Media item has no bitrate")
        # get video codec
        try:
            info['video_codec'] = item.videoCodec if item.videoCodec else 'Unknown'
        except AttributeError:
            logger.debug("Media item has no videoCodec")
        # get video resolution
        try:
            info['video_resolution'] = item.videoResolution if item.videoResolution else 'Unknown'
        except AttributeError:
            logger.debug("Media item has no videoResolution")
        # get video height
        try:
            info['video_height'] = item.height if item.height else 0
        except AttributeError:
            logger.debug("Media item has no height")
        # get video width
        try:
            info['video_width'] = item.width if item.width else 0
        except AttributeError:
            logger.debug("Media item has no width")
        # get video duration
        try:
            info['video_duration'] = item.duration if item.duration else 0
        except AttributeError:
            logger.debug("Media item has no duration")
        # get audio codec
        try:
            info['audio_codec'] = item.audioCodec if item.audioCodec else 'Unknown'
        except AttributeError:
            logger.debug("Media item has no audioCodec")
        # get audio channels
        try:
            for part in item.parts:
                for stream in part.audioStreams():
                    if stream.channels:
                        logger.debug("Added %d channels for %s audioStream", stream.channels,
                                stream.title if stream.title else 'Unknown')
                        info['audio_channels'] += stream.channels
            if info['audio_channels'] == 0:
                info['audio_channels'] = item.audioChannels if item.audioChannels else 0

        except AttributeError:
            logger.debug("Media item has no audioChannels")


        # is this a multi part (cd1/cd2)
        if len(item.parts) > 1:
            info['multipart'] = True
        for part in item.parts:
            info['file'].append(part.file)
            info['file_size'] += part.size if part.size else 0

        return info

    @staticmethod
    def delete_item(item):
        try:
            delete_url = urljoin(ModelSetting.get('plex_server'), '%s/media/%d' % (item['show_key'], item['id']))
            ModelItem.save_as_dict(item)
            if requests.delete(delete_url, headers={'X-Plex-Token': ModelSetting.get('plex_token')}).status_code == 200:
                logger.debug("\t\tDeleted media item: %r" % item['file'][0])
            else:
                logger.debug("\t\tError deleting media item: %r" % ['file'][0])
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def move_item(item):
        logger.debug('Move media item : %s to %s ', item['file'][0], ModelSetting.get('move_path'))
        try:
            celery_shutil.move(item['file'][0], ModelSetting.get('move_path'))
            ModelItem.save_as_dict(item)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())                       
