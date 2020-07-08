from flask import Flask, request, render_template, jsonify
from pymongo import MongoClient
from pymongo.collection import Collection
import jieba
import collections
import json
import time
from LAC import LAC

app = Flask(__name__)
app.debug = True
FLASK_DEBUG = 1
client = MongoClient("localhost")
db = client['tkh']
cur_sp = Collection(db, 'douyin_sp')
cur_user = Collection(db, 'douyin_user')
pre_select = '广东'  # 设置上一个点击的省份，以便数据刷新
lac = LAC(mode='seg')


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")  # 返回前端模板


@app.route("/gender", methods=["GET"])
def gender():
    """
    获取性别人数
    :return: json
    """
    if request.method == "GET":
        no_set = cur_user.find({'gender': 0}).count()
        male = cur_user.find({'gender': 1}).count()
        female = cur_user.find({'gender': 2}).count()
        return jsonify(noset=no_set, male=male, female=female)


@app.route("/getCount", methods=["GET"])
def get_count():
    """
    获取视频以及用户数量
    :return:
    """
    if request.method == "GET":
        user_count = cur_user.find({}).count()
        video_count = cur_sp.find({}).count()
        return jsonify(cuser=user_count, cvideo=video_count)


def get_stop_word():
    """
    读取所有停用词
    :return:
    """
    with open('cn_stopwords.txt', 'r', encoding='utf-8') as f:
        data = f.read()
    data_list = data.split('\n')
    with open('badwords.txt', 'r', encoding='utf-8') as f:
        data = f.read()
    data_list += data.split('\n')
    with open('无用词.txt', 'r', encoding='utf-8') as f:
        data = f.read()
    data_list += data.split('\n')
    with open('info.json', 'r', encoding='utf-8') as f:
        dict_data = json.load(f).get('stickers')
        for d in dict_data:
            data_list.append(d.get('display_name').replace('[', '').replace(']', ''))
    return data_list


@app.route("/wordCloud", methods=["GET"])
def word_cloud():
    """
    返回前100词频率
    :return:
    """
    if request.method == "GET":
        time1 = time.time()
        stop_word = get_stop_word()
        text = ''
        data = cur_sp.find({}, {"comment": 1})
        for d in data:  # 将所有评论用、连接在一起
            text = text + d.get('comment') + '、'
        for sw in stop_word:
            text = text.replace(sw, '')
        seq_list = jieba.cut(text)  # 分词
        word_counts = collections.Counter(seq_list)  # 统计数量
        word_list = list()
        for key, value in word_counts.items():  # 去除停用词，去除单字
            if len(key.strip()) > 1:
                word_list.append({'name': key, 'value': value})
        word_list = sorted(word_list, key=lambda x: x['value'], reverse=True)[:100]
        print("总用时"+str(time.time() - time1))

        # 以下方式耗时较长13s左右已弃用
        # word_counts_top100 = word_list.most_common(100)
        # word_list = list()
        # print(len(stop_word))
        # for key in seq_list:  # 去除停用词，去除单字
        #     if not (key.strip() in stop_word) and (len(key.strip()) > 1):
        #         word_list.append(key)
        # word_counts = collections.Counter(seq_list)
        # word_counts_top100 = word_counts.most_common(100)
        # 转为字典列表格式
        # re = list()
        # for word in word_counts_top100:
        #     re.append({'name': word[0], 'value': word[1]})
        # print(re)
        return jsonify(word_list)


@app.route("/birthday", methods=["GET"])
def get_birthday():
    """
    返回出生日期以及对应的人数
    :return:
    """
    if request.method == "GET":
        user_birthday = cur_user.find({}, {"birthday": 1})
        years = list()
        for user in user_birthday:
            date = user.get('birthday').split('-')
            years.append(date[0])
        year_counts = collections.Counter(years)
        year_counts.pop('')
        year_top_30 = year_counts.most_common(20)
        categories = list()
        data = list()
        year_top_30.sort()
        for k, v in year_top_30:
            categories.append(k)
            data.append({'name': k, 'value': v})
        return jsonify({'categories': categories, 'data': data})


@app.route("/map", methods=["GET"])
def get_user_map():
    """
    返回每个地区的人数
    :return:
    """
    if request.method == "GET":
        user_province = cur_user.find({}, {"province": 1})
        province = list()
        for user in user_province:
            province.append(user.get('province').replace('省', ''))
        province_counts = collections.Counter(province)
        province_counts.pop('')
        data = list()
        for k, v in province_counts.items():
            data.append({'name': k, 'value': v})
        return jsonify(data)


@app.route("/country", methods=["GET"])
def get_user_country():
    """
    返回国外各国人数
    :return:
    """
    if request.method == "GET":
        user_country = cur_user.find({}, {"country": 1})
        country = list()
        for user in user_country:
            country.append(user.get('country'))
        country_counts = collections.Counter(country)
        country_counts.pop('')
        country_counts.pop('中国')  # 仅分析国外人数，去除中国以及未设置的
        country_counts.pop('暂不设置')
        country_counts_10 = country_counts.most_common(10)
        data = list()
        categories = list()
        for k, v in country_counts_10:
            categories.append(k)
            data.append({'name': k, 'value': v})
        return jsonify({'categories': categories, 'data': data})


@app.route("/analysis", methods=["GET"])
def get_user_analysis():
    """
    返回指定省份的分析数据
    :return:
    """
    global pre_select
    if request.method == "GET":
        if request.args.get('province'):
            province = request.args.get('province')  # 获取参数
            pre_select = province
        elif pre_select:  # 如果没传值优先上一个点击的
            province = pre_select
        else:
            province = '广东'
        user_data = cur_user.find({'province': province}, {"birthday": 1})
        no_set = cur_user.find({'province': province, 'gender': 0}).count()
        male = cur_user.find({'province': province, 'gender': 1}).count()
        female = cur_user.find({'province': province, 'gender': 2}).count()
        birthday = list()  # 出生日期
        for user in user_data:
            years = user.get('birthday').split('-')[0][:-1]+'0后'  # 取倒数第二位，如1990取到9加0和后得到90后
            birthday.append(years)
        birthday_counts = collections.Counter(birthday)
        birthday_counts.pop('0后')
        birthday_counts_5 = birthday_counts.most_common(5)  # 取前5个
        birthday_counts_5.sort(reverse=True)  # 排序
        data_birthday = list()
        categories = list()
        for k, v in birthday_counts_5:
            categories.append(k[-3:])
            data_birthday.append({'name': k[-3:], 'value': v})
        return jsonify({
            'province': province,
            'birthday': {'categories': categories, 'data': data_birthday},
            'gender': {'male': male, 'no_set': no_set, 'female': female}
        })


if __name__ == "__main__":
    # STOP_WORD = get_stop_word()
    app.run(port=7000, threaded=True)
