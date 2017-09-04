# !/usr/bin/env python
# -*-encoding: utf-8-*-
# author:LiYanwei
# version:0.1

import requests
import urllib2
import time
import json
import urllib
import re
import os
import sys
from  fake_useragent import UserAgent

default_encoding = sys.getfilesystemencoding()
if default_encoding.lower() == 'ascii':
    default_encoding = 'utf-8'

class Youku():
    def __init__(self):
        # 伪造请求头
        self.headers = {"accept-encoding": "gzip, deflate, sdch",
                        "accept-language": "zh-CN,zh;q=0.8,en;q=0.6,zh-TW;q=0.4",
                        "user-agent": UserAgent().random,
                        }
        # cookies中的cna，优酷请求不能禁用cookies
        self.utid = urllib.quote('iSHtETfbVH8CAduFZTKWBjE+')

    def get_cna(self):
        response = requests.get('http://log.mmstat.com/eg.js').text
        re_obj = re.search('Etag="(.*)"', response)
        cna = re_obj.group(1)
        self.utid = urllib.quote(cna)
        '''默认对cna解码后传到全局变量中，替代原有的utid'''

    def get_video_info(self, video_url, retry=0):
        # 爬取过快cookie会被禁用，直接报错，此处except切换cookie
        try:
            video_id = self.extract_id(video_url)
            # 解析视频真实地址的最关键的请求所有信息都在返回的json格式文件中。
            # 复制粘贴到json在线解析网站（www.json.cn）对照分析
            # 根据分析，包括四个参数，然后程序生成相应参数，构造URL并进行模拟请求，得到返回数据
            print '正在使用的cookie：', self.utid
            url = 'https://ups.youku.com/ups/get.json?vid={}&ccode=0401&client_ip=192.168.1.1&utid={}&client_ts={}'.format(
                video_id, self.utid, int(time.time()))
            # 在headers中增加反盗链
            headers = dict(self.headers, **{"referer": 'http://v.youku.com/v_show/id_{}.html'.format(video_id)})
            response = requests.get(url, headers=headers).text
            print response
            res_json = json.loads(response)
            if 'error' in res_json['data']:
                # 如果出错
                error = res_json['data']['error']
                # print(error)
                if str(error['code']) == '-6004':
                    '''之前有过这个url编码的错误，再次测试遇不到了。先放着，试了几次没遇到，等遇到再解决'''
                    if retry == 0:
                        print 'cookie出错，对URL编码的cookie进行解码'
                        self.utid = urllib.unquote(self.utid)
                        return self.get_video_info(video_url, retry=1)
                    elif retry == 1:
                        print '解码后的cookie仍然不能使用，可能cookie被禁，现重新获取cookie'
                        self.get_cna()
                        return self.get_video_info(video_url)
                elif str(error['code']) == '-3307':
                    # 黄金会员才可观看
                    print '黄金会员视频无法获得视频源', error['note']
                    pass
                elif str(error['code']) == '-2004':
                    # 登录账号订阅up主才可观看
                    print '订阅视频无法获得视频源', error['note']
            else:
                # 解析分段视频
                return self.parse_res(res_json)
        except:
            print 'cookie被禁，现重新获取cookie'
            self.get_cna()
            return self.get_video_info(video_url)


    def extract_id(self, video_url):
        '''
        正则提取输入链接video_url中的优酷视频唯一id
        '''
        result = re.search('id_(.*)\.html', video_url)
        if result:
            video_id = result.group(1)
            return video_id
        else:
            print '请检查url格式是否有误（url中是否包含了视频id）', '\n', '格式应如：http://v.youku.com/v_show/id_XMTU2NTk5MDgxMg==.html'
            exit()

    def parse_res(self, res_json):
        '''
        这个只是尝试解析，应根据项目需要定制自己要的视频源
        '''
        video = res_json.get('data').get('video')
        print '\n''视频标题：', video.get('title')

        # 获取视频的格式
        if video.get('stream_types').get('default') != None:
            # 随便找了几个视频链接试了下，大部分视频格式是在json文件的'default'标签中
            print '\n', '该视频有以下几种格式：', video.get('stream_types').get('default'), '\n'
        else:
            # 试了优酷首页的人民的名义，视频格式在'guoyu'标签中，这里直接连父标签打出来
            print '\n', '该视频有以下几种格式：', video.get('stream_types'), '\n'

        # 获取视频流各种格式
        for stream in res_json.get('data').get('stream'):
            print '*' * 100
            # print '视频类型：', stream.get('stream_type')
            print "视频总时长：", self.milliseconds_to_time(stream.get('milliseconds_video'))
            print '视频总大小:', '%.2f MB' % (float(stream.get('size') / (1024 ** 2)))
            return self.get_seg(stream),video.get('title')
            # 只获取流媒体第一种格式
            break

    # 信息中的视频时长是ms，用此函数转成时分秒的格式
    def milliseconds_to_time(self, milliseconds):
        seconds = milliseconds / 1000
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return "%02d:%02d:%02d" % (h, m, s)

    # 每个视频分成若干段，用此函数获得各段的信息
    def get_seg(self, stream):
        seg_num = len(stream.get('segs'))
        urls = []
        print '+' * 20, '该视频共%d段' % seg_num, '+' * 20
        for i in range(seg_num):
            seg = stream.get('segs')[i]
            # print "第%d段时长：" % (i + 1), self.milliseconds_to_time(seg.get('total_milliseconds_video'))
            # print "第%d段大小：" % (i + 1), '%.2f MB' % (float(seg.get('size') / (1024 ** 2)))
            # print "第%d段视频地址：" % (i + 1), seg.get('cdn_url')
            size = float(seg.get('size'))
            url = seg.get('cdn_url')
            urls.append((url, int(size)))
        return urls

    # 根据上面的到的链接下载视频
    def video_download(self):
        pass


def download_urls(urls, title, type, total_size ,refer=None, merge=True):
    # 本地编码
    title = to_native_string(title)
    # 替换标题的特殊字符
    title = escape_file_path(title)
    # 目录名
    dirname = './youku/'
    # 如果目录不存在，则创建目录
    if (not os.path.exists(dirname)):
        os.makedirs(dirname)
    # 文件名
    filename = '%s.%s' % (title, type)
    # 路径
    filepath = os.path.join(dirname, filename)
    # 判断视频是否已经下载
    if total_size:
        if os.path.exists(filepath) and os.path.getsize(filepath) >= total_size * 0.9:
            print 'Skip %s: file already exists' % filepath
            return
    # 分段视频只有一个时
    if len(urls) == 1:
        url = urls[0]
        print 'Downloading %s ...' % filename
        url_save(url, filepath, refer=refer)

    else:
        flvs = []
        print 'Downloading %s.%s ...' % (title, type)
        for i, url in enumerate(urls):
            filename = '%s[%02d].%s' % (title, i, type)
            filepath = os.path.join(dirname, filename)
            flvs.append(filepath)
            url_save(url, filepath, refer=refer)
        if not merge:
            return
        if type == 'flv':
            from flv_join import concat_flvs
            concat_flvs(flvs, os.path.join(dirname, title + '.flv'))
            # 移除分段下载的flv
            for flv in flvs:
                os.remove(flv)
        elif type == 'mp4':
            from mp4_join import concat_mp4s
            concat_mp4s(flvs, os.path.join(dirname, title + '.mp4'))
            for flv in flvs:
                os.remove(flv)
        else:
            print "Can't join %s files" % type



def file_type_of_url(url):
    # 文件类型
	return str(re.search(r'.*\.(.*?)\?', url).group(1))

def to_native_string(s):
    if type(s) == unicode:
        return s.encode(default_encoding)
    else:
        return s


def escape_file_path(path):
    path = path.replace('/', '-')
    path = path.replace('\\', '-')
    path = path.replace('*', '-')
    path = path.replace('?', '-')
    return path

def url_save(url, filepath, refer=None):
	headers = {}
	if refer:
		headers['Referer'] = refer
	request = urllib2.Request(url, headers=headers)
	response = urllib2.urlopen(request)
	file_size = int(response.headers['content-length'])
	print file_size
	if os.path.exists(filepath):
		if file_size == os.path.getsize(filepath):
			print 'Skip %s: file already exists' % os.path.basename(filepath)
			return
		else:
			print 'Overwriting', os.path.basename(filepath), '...'
	with open(filepath, 'wb') as output:
		received = 0
		while True:
			buffer = response.read(1024*256)
			if not buffer:
				break
			received += len(buffer)
			output.write(buffer)
	print received == file_size == os.path.getsize(filepath), '%s == %s == %s' % (received, file_size, os.path.getsize(filepath))

if __name__ == '__main__':
    # 单个视频地址
    # http://v.youku.com/v_show/id_XMjkwMDE4NDQyNA==.html
    url_input = raw_input('输入或粘贴网址,完成之后加空格并回车：')
    youku = Youku()
    title = youku.get_video_info(url_input)[1]
    urls, sizes = zip(*youku.get_video_info(url_input)[0])
    total_size = sum(sizes)
    download_urls(urls, title , file_type_of_url(urls[0]), total_size)
