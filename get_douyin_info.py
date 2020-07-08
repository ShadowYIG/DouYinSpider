#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time       : 2020/6/2 17:32
# @Author     : ShadowY
# @File       : get_douyin_info.py
# @Software   : PyCharm
# @Version    : 1.0
# @Description: 爬取抖音信息


import requests
import time
import awemev2_pb2 as pr
import json
import pprint
import random
import logging
from google.protobuf.json_format import MessageToJson
from pymongo import MongoClient
from pymongo.collection import Collection
import string


client = MongoClient("localhost")
db = client['tkh']
cur_sp = Collection(db, 'douyin_sp')
cur_user = Collection(db, 'douyin_user')
GORGON_URL = "http://192.168.31.111:8800"

def get_proxy():
    """
    获取代理
    :return:
    """
    proxy = requests.get('http://127.0.0.1:5000/get').json().get("proxy")
    return {proxy.split(':')[0]: proxy}


def get_feed(min_count=0, count=6):
    """
    获取热门视频
    :param min_count 起始位置
    :param count:获取数量
    :return:
    """
    page = min_count
    while page < count + min_count:
        page += 6  # 抖音默认6页一次,虽然有参数可以改,但是为了稳定还是不要改
        rticket = int(time.time() * 1000)
        feed_url = f'https://api3-normal-c-lf.amemv.com/aweme/v2/feed/?type=0&max_cursor={page + 6}&min_cursor={page}&count=6&cached_item_num=0&_rticket={str(rticket)}&device_platform=android&device_type=HUAWEI%20MLA-L12&version_code=110200&app_name=aweme&os_version=5.1.1&channel=tengxun_new'
        gorgon = requests.post(GORGON_URL+"/url", data=feed_url).text  # 请求本地搭建的x-gorgon加密接口计算goron
        print(gorgon)
        headers = {
            'user-agent': "okhttp/3.10.0.1",
            # 'accept-encoding': 'json',  # 'accept-encoding': 'gzip, deflate, br',  # 发现可以省略encoding
            'x-gorgon': gorgon,
            'x-khronos': str(int(rticket / 1000)),
        }
        try:
            res = requests.get(feed_url, headers=headers, proxies=get_proxy())
        except requests.exceptions.ProxyError:
            get_feed(count-page)
            return
        # 调用抖音的proto文件转换成的python库将protobuf流数据转换为字典格式
        msg = pr.aweme_v2_feed_response()
        msg.ParseFromString(res.content)
        dict_msg = json.loads(MessageToJson(msg))  # 转换为字典格式
        # with open('1.txt', 'w') as f:
        #     f.write(MessageToJson(msg))
        aweme_list = dict_msg.get('awemeList')
        if not aweme_list:  # 没取到数据
            logging.error('未取到数据')
        else:
            for aweme in aweme_list:
                awemeId = aweme.get('awemeId')  # 视频id
                desc = aweme.get('desc') if aweme.get('desc') else ''  # 视频描述
                createTime = aweme.get('createTime')  # 创建时间
                author_name = aweme.get('author').get('nickname')  # 作者昵称
                author_id = aweme.get('author').get('secUid')  # 作者id
                author_signature = aweme.get('author').get('signature')  # 作者个性签名
                author_region = aweme.get('author').get('region')  # 作者国家
                music_id = aweme.get('music').get('id')  # 音乐id
                music_title = aweme.get('music').get('title')  # 音乐名称
                music_author = aweme.get('music').get('author')  # 音乐作者
                music_playUrl = aweme.get('music').get('playUrl').get('uri')  #播放链接
                chaName = '、'.join([cha.get('chaName') for cha in aweme.get('chaList') if cha.get('desc')]) if aweme.get('chaList') else ''  # 标签1名称
                cha_desc = '、'.join([cha.get('desc') for cha in aweme.get('chaList') if cha.get('desc')]) if aweme.get('chaList') else ''  # 标签1描述
                download_url = aweme.get('video').get('downloadAddr').get('urlList')[0] if aweme.get('video').get('downloadAddr') and aweme.get('video').get('downloadAddr').get('urlList') else ''  # 下载链接
                data_size = aweme.get('video').get('downloadAddr').get('dataSize') if aweme.get('video').get('downloadAddr') else ''  # 视频大小
                comment_count = aweme.get('statistics').get('commentCount') if aweme.get('statistics') else ''  # 评论数量
                digg_count = aweme.get('statistics').get('diggCount') if aweme.get('statistics') else ''  # 点赞数量
                download_count = aweme.get('statistics').get('downloadCount') if aweme.get('statistics') else ''  # 下载数量
                share_count = aweme.get('statistics').get('shareCount') if aweme.get('statistics') else ''  # 分享数量
                forward_count = aweme.get('statistics').get('forwardCount') if aweme.get('statistics') else ''  # 关注数量
                text_extra = '、'.join([extra.get('hashtagName') for extra in aweme.get('textExtra') if extra.get('hashtagName')]) if aweme.get('textExtra') else ''  # 标签2
                yield {
                      'awemeId': awemeId,
                      'desc': desc,
                      'createTime': createTime,
                      'author_name': author_name,
                      'author_id': author_id,
                      'author_signature': author_signature,
                      'author_region': author_region,
                      'music_id': music_id,
                      'music_title': music_title,
                      'music_author': music_author,
                      'music_playUrl': music_playUrl,
                      'chaName': chaName,
                      'cha_desc': cha_desc,
                      'download_url': download_url,
                      'data_size': data_size,
                      'comment_count': comment_count,
                      'digg_count': digg_count,
                      'download_count': download_count,
                      'share_count': share_count,
                      'forward_count': forward_count,
                      'text_extra': text_extra
                }


def get_comment(aweme_id, count=20):
    """
    获取视频对应的评论
    :param aweme_id:视频id
    :param cursor:
    :param count:
    :return:
    """
    page = 0
    comment = ""
    user = list()
    while page < count:
        page += 20
        rticket = int(time.time() * 1000)
        # comment_url = f'https://api3-normal-c-lf.amemv.com/aweme/v2/comment/list/?aweme_id={aweme_id}&cursor={str(page-20)}&count={str(20)}&address_book_access=2&gps_access=1&forward_page_type=1&channel_id=0&city=360700&hotsoon_filtered_count=0&hotsoon_has_more=0&follower_count=0&is_familiar=0&page_source=0&device_type=HUAWEI%20MLA-L12&app_name=aweme&ts={str(int(rticket / 1000))}&app_type=normal&host_abi=armeabi-v7a&update_version_code=11209900&channel=tengxun_new&_rticket={str(rticket)}&device_platform=android&iid=3913906517462814&version_code=110200&device_id=1257486423178510&os_version=5.1.1d&aid=1128'
        # comment_url = f'https://api3-normal-c-lf.amemv.com/aweme/v2/comment/list/?aweme_id={aweme_id}&cursor=0&count={str(20)}&address_book_access=2&gps_access=1&forward_page_type=1&channel_id=0&city=360700&hotsoon_filtered_count=0&hotsoon_has_more=0&follower_count=0&is_familiar=0&page_source=0&device_type=HUAWEI%20MLA-L12&app_name=aweme&ts={str(int(rticket / 1000))}&app_type=normal&host_abi=armeabi-v7a&update_version_code=11209900&channel=tengxun_new&_rticket={str(rticket)}&device_platform=android&iid=3913906517462814&version_code=110200&device_id=1257486423178510&os_version=5.1.1d&aid=1128'
        comment_url = f'https://api3-normal-c-lf.amemv.com/aweme/v2/comment/list/?aweme_id={aweme_id}&cursor={str(page-20)}&count={str(20)}&address_book_access=2&gps_access=1&forward_page_type=1&channel_id=0&city=360700&hotsoon_filtered_count=0&hotsoon_has_more=0&follower_count=0&is_familiar=0&page_source=0&os_api=22&device_type=HUAWEI%20MLA-L12&ssmix=a&manifest_version_code=110201&dpi=320&uuid=866174010438816&app_name=aweme&version_name=11.2.0&ts={str(int(rticket / 1000))}&cpu_support64=false&app_type=normal&ac=wifi&host_abi=armeabi-v7a&update_version_code=11209900&channel=tengxun_new&_rticket={str(rticket)}&device_platform=android&iid=3913906517462814&version_code=110200&mac_address=2C%3A4D%3A54%3AD1%3ACF%3AE1&cdid=daf746b2-8b90-4207-906f-aee1b95181f3&openudid=25959ac41d3233e9&device_id=1257486423178510&resolution=900*1600&os_version=5.1.1&language=zh&device_brand=Android&aid=1128&mcc_mnc=46007'
        gorgon = requests.post(GORGON_URL+"/url", data=comment_url).text  # 请求本地安卓搭建的x-gorgon加密接口计算goron
        print(gorgon)
        headers = {
            'user-agent': "okhttp/3.10.0.1",
            'x-gorgon': gorgon,
            'x-khronos': str(int(rticket / 1000)),
        }
        try:
            res = requests.get(comment_url, headers=headers, proxies=get_proxy())  # 请求评论页面
            print(res.text)
        except requests.exceptions.ProxyError:
            get_comment(aweme_id, count-page)
            return
        dict_msg = json.loads(res.text)
        if dict_msg.get('comments'):
            comment = comment + '、'.join([com.get('text') for com in dict_msg.get('comments') if com.get('text')]) + '、'  # 评论,通过上面连接控制条数,默认取前20条
            user += [com.get('user').get('sec_uid') for com in dict_msg.get('comments')]  # 拿到所有评论者id
    return comment, user


def get_user_info(sec_user_id):
    """
    获取用户信息
    :param sec_user_id 用户id
    :return:
    """
    rticket = int(time.time() * 1000)
    device_type = random.choice(['RedMi', 'ViVO', 'Xiaomi', 'huawei', 'Meizu']) + '%20' + random.choice(['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '10']) + '%20' + random.choice(['', 'i', 'x', 'pro', ''])
    # user_info_url = f'https://aweme-lq.snssdk.com/aweme/v1/user/?sec_user_id={sec_user_id}&address_book_access=1&retry_type=no_retry&iid=103707347463&device_id=70793717943&ac=wifi&channel=wandoujia_aweme2&aid=1128&app_name=aweme&version_code=790&version_name=7.9.0&device_platform=android&ssmix=a&device_type=R831T&device_platform=android&language=zh&os_api=19&os_version=4.4.2&uuid=864394010882332&openudid=88E9FE8804850000&manifest_version_code=790&resolution=720*1280&dpi=240&update_version_code=7902&_rticket={str(rticket)}&mcc_mnc=46007&app_type=normal'
    user_info_url = f'https://api3-core-c-lf.amemv.com/aweme/v1/user/profile/other/?sec_user_id={sec_user_id}&address_book_access=2&from=0&publish_video_strategy_type=0&os_api=22&device_type={device_type}&ssmix=a&manifest_version_code=110201&dpi=320&uuid=866174010438816&app_name=aweme&version_name=11.2.0&cpu_support64=false&app_type=normal&ac=wifi&host_abi=armeabi-v7a&update_version_code=11209900&channel=tengxun_new&_rticket={str(rticket)}&device_platform=android&iid=3913906517462814&version_code=110200&mac_address=2C%3A4D%3A54%3AD1%3ACF%3AE2&cdid=daf746b2-8b90-4207-906f-aee1b95181f3&openudid=25959ac41d3233e9&device_id=1257486423178510&resolution=900*1600&os_version=5.1.1&language=zh&device_brand=Android&aid=1128&mcc_mnc=46007'
    gorgon = requests.post(GORGON_URL + "/url", data=user_info_url).text
    print(gorgon)
    headers = {
        'user-agent': "okhttp/3.10.0.1",
        'x-gorgon': gorgon,
        'x-khronos': str(int(rticket / 1000)),
    }
    # print(requests.get(user_info_url, headers=headers, proxies=get_proxy()).text)
    try:
        res = requests.get(user_info_url, headers=headers, proxies=get_proxy()).json().get('user')
    except requests.exceptions.ProxyError:
        get_user_info(sec_user_id)
        return
    aweme_count = res.get('aweme_count')  # 作品数量
    sec_uid = res.get('sec_uid')  # id
    gender = res.get('gender')  # 性别
    dongtai_count = res.get('dongtai_count')  # 动态数量
    shop_entry = res.get('with_fusion_shop_entry')  # 开通商城
    favorited_count = res.get('total_favorited')  # 被关注
    modify_time = res.get('unique_id_modify_time')
    country = res.get('country')
    is_activity_user = res.get('is_activity_user')
    school_name = res.get('school_name')
    following_count = res.get('following_count')  # 关注
    location = res.get('location')  # 地址
    province = res.get('province')  # 省份
    nickname = res.get('nickname')  # 昵称
    college_name = res.get('college_name')  # 大学名称
    mplatform_followers_count = res.get('mplatform_followers_count')  # 关注数
    birthday = res.get('birthday')  # 出生日期
    signature = res.get('signature')  # 个性签名
    return {
        'sec_uid': sec_uid,
        'aweme_count': aweme_count,
        'gender': gender,
        'dongtai_count': dongtai_count,
        'shop_entry': shop_entry,
        'favorited_count': favorited_count,
        'modify_time': modify_time,
        'country': country,
        'is_activity_user': is_activity_user,
        'school_name': school_name,
        'following_count': following_count,
        'location': location,
        'province': province,
        'nickname': nickname,
        'college_name': college_name,
        'mplatform_followers_count': mplatform_followers_count,
        'birthday': birthday,
        'signature': signature
    }


def write_to_db(info, cur, op):
    """
    将信息写入对应数据库
    :param info:
    :param cur: 游标
    :param op: 0:视频,1用户
    :return:
    """
    if op:
        if not info:
            return
        if info and info.get('sec_uid') and not cur.find_one({"sec_uid": info.get('sec_uid')}):
            cur.insert_one(info)
            print(info)
        else:
            cur.update_one({"sec_uid": info.get('sec_uid')}, {'$set': info})
            print('update' + str(info))
    else:
        if info and info.get('awemeId') and not cur.find_one({"awemeId": info.get('awemeId')}):
            cur.insert_one(info)
            print(info)
        else:
            cur.update_one({"awemeId": info.get('awemeId')}, {'$set': info})
            print('update' + str(info))


# import threading
# def test(str, flag):
#     datas = cur_user.find({}).sort(str, flag)
#     for data in datas:
#         if not data.get('gender'):
#             user_info = get_user_info(data['sec_uid'])
#             write_to_db(user_info, cur_user, 1)

if __name__ == '__main__':
    awemes = get_feed(0, 100)
    for aweme in awemes:
        comm_data = get_comment(aweme.get('awemeId'), count=50)
        if comm_data:
            comm, usr_list = comm_data  # 取视频的评论
            for usr in usr_list:
                user_info = get_user_info(usr)  # 获取用户数据
                write_to_db(user_info, cur_user, 1)
            aweme.update({'comment': comm})
        if aweme.get('sec_uid'):
            user_info = get_user_info(aweme.get('sec_uid'))  # 获取发视频者数据
        write_to_db(aweme, cur_sp, 0)
    # print(get_user_info("MS4wLjABAAAATxB54rmn2GAb1SKQDUpakWBil52_Wh6HYkSWW9SDuMI"))

    # 更新数据
    # datas = cur_user.find({})
    # for data in datas:
    #     if not data.get('gender') and data.get('gender') != 0:
    #         user_info = get_user_info(data['sec_uid'])
    #         # print(user_info)
    #         write_to_db(user_info, cur_user, 1)