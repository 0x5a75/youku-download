#!usr/bin/env python
#coding=utf-8
import re
import urllib2
import os
import sys
import json
import getopt
import shutil
import subprocess
import locale
import socket
import win32con
import win32clipboard

from xml.etree import ElementTree

socket.setdefaulttimeout(15)
default_encoding = locale.getdefaultlocale()[-1]
default_conf = {'tmp_dir': u'',    #缓存地址
                'output_dir': u'd:',    #输出地址
                'defi': '1',    #视频清晰度
                'proxy': ''    #代理地址
                }
#----------------------------------------------------------------------
def win32_unicode_argv():
    '''sys.argv 参数格式为unicode'''
    
    from ctypes import POINTER, byref, cdll, c_int, windll
    from ctypes.wintypes import LPCWSTR, LPWSTR

    GetCommandLineW = cdll.kernel32.GetCommandLineW
    GetCommandLineW.argtypes = []
    GetCommandLineW.restype = LPCWSTR

    CommandLineToArgvW = windll.shell32.CommandLineToArgvW
    CommandLineToArgvW.argtypes = [LPCWSTR, POINTER(c_int)]
    CommandLineToArgvW.restype = POINTER(LPWSTR)

    cmd = GetCommandLineW()
    argc = c_int(0)
    argv = CommandLineToArgvW(cmd, byref(argc))
    if argc.value > 0:
        start = argc.value - len(sys.argv)
        return [argv[i] for i in
                xrange(start, argc.value)]
sys.argv = win32_unicode_argv()


########################################################################
class Youku(object):
    '''youku下载类'''

    #----------------------------------------------------------------------
    def __init__(self,url,defi):
        '''参数：视频地址，视频清晰度（1，2，3，4）'''
        self.url = url
        self.defi = defi
    #----------------------------------------------------------------------
    def info(self):
        '''获取下载信息'''
        title = self.title()
        links = self.links()[0]
        defi = self.links()[1]
        return (title, links, defi)

    #----------------------------------------------------------------------
    def title(self):
        '''获取视频标题'''
        id = self.video_id()
        html = urllib2.urlopen('http://v.youku.com/v_show/id_%s.html'%id).read()
        video_title = r1_of([r'<title>([^<>]*)</title>'], html).decode('utf-8')
        video_title= self.trim_title(video_title)
        return video_title
    #----------------------------------------------------------------------
    def links(self):
        '''下载视频M3U8'''
        id = self.video_id()
        if self.defi=='4':
            defi='flv'
        elif self.defi=='3':
            defi='hd1'
        elif self.defi=='2':
            defi='hd2'
        else:
            defi='mp4'
        url='http://v.youku.com/player/getRealM3U8/vid/'+id+'/type/'+defi+'/video.m3u8'
        chunk=urllib2.urlopen(url)
        m3u8_lines = chunk.readlines()
        links=[]
        while not links:
            for i in m3u8_lines:
                try:
                    m=re.match(r'http.*%s'%defi,i)
                    if m.group() not in links:
                        links.append(m.group())
                except BaseException, e:
                    #print e
                    continue
            if not links:
                defi='flv'
        return (links, defi)
    #----------------------------------------------------------------------  
    def video_id(self):
        '''获取视频ID'''
        patterns = [r'^http://v.youku.com/v_show/id_([\w=]+).html',
                    r'^http://player.youku.com/player.php/sid/([\w=]+)/v.swf',
                    r'^loader\.swf\?VideoIDS=([\w=]+)',
                    r'^([\w=]+)$']
        return r1_of(patterns, self.url)
    #----------------------------------------------------------------------
    def trim_title(self,title):
        '''格式化视频标题'''
        title = title.replace(u' - 视频 - 优酷视频 - 在线观看', '')
        title = title.replace(u' - 专辑 - 优酷视频', '')
        title = re.sub(ur'—([^—]+)—优酷网，视频高清在线观看', '', title)
        pattern=u'[a-zA-Z0-9\u4e00-\u9fa5]+'
        j=re.findall(pattern,title)
        title=u''
        for i in j:
            title=title+i
        return title.encode(default_encoding)

########################################################################
class Sohu(object):
    '''Sohu下载类'''

    #----------------------------------------------------------------------
    def __init__(self,url, defi):
        '''参数：视频地址'''
        self.url = url
        self.defi = defi

    #----------------------------------------------------------------------
    def info(self):
        '''获取下载信息'''
        html = urllib2.urlopen(self.url).read()
        id = int(re.findall(r'vid="(\d+)"',html)[0])
        data = json.loads(urllib2.urlopen('http://hot.vrs.sohu.com/vrs_flash.action?vid=%s' % id).read())
        if self.defi=='1':
            if data['data']['oriVid'] not in (0, id):
                data = json.loads(urllib2.urlopen('http://hot.vrs.sohu.com/vrs_flash.action?vid=%s' % data['data']['oriVid']).read())
            else:
                self.defi = '2'
        if self.defi=='2':
            if data['data']['superVid'] not in (0, id):
                data = json.loads(urllib2.urlopen('http://hot.vrs.sohu.com/vrs_flash.action?vid=%s' % data['data']['superVid']).read())
            else:
                self.defi = '3'
        if self.defi=='3':
            if data['data']['highVid'] not in (0, id):
                data = json.loads(urllib2.urlopen('http://hot.vrs.sohu.com/vrs_flash.action?vid=%s' % data['data']['highVid']).read())
            else:
                self.defi = '4'
        if self.defi=='4' and data['data']['norVid'] not in (0, id):
            data = json.loads(urllib2.urlopen('http://hot.vrs.sohu.com/vrs_flash.action?vid=%s' % data['data']['norVid']).read())
        links=[]
        host = data['allot']
        prot = data['prot']
        data = data['data']
        title = data['tvName']
        for file, new in zip(data['clipsURL'], data['su']):
            links.append(self.real_url(host, prot, file, new))
        title = self.trim_title(title)
        return (title, links, 'mp4')
    #----------------------------------------------------------------------
    def real_url(self, host, prot, file, new):
        '''实时url'''
        url = 'http://%s/?prot=%s&file=%s&new=%s' % (host, prot, file, new)
        s = urllib2.urlopen(url).read().split('|')
        return '%s%s?key=%s' % (s[0][:-1], new, s[3])
    #----------------------------------------------------------------------
    def trim_title(self,title):
        '''格式化视频标题'''
        pattern=u'[a-zA-Z0-9\u4e00-\u9fa5]+'
        j=re.findall(pattern,title)
        title=u''
        for i in j:
            title=title+i
        return title.encode(default_encoding)

########################################################################
class Tudou(object):
    '''Tudou下载类'''

    #----------------------------------------------------------------------
    def __init__(self,url, defi):
        '''参数：视频地址'''
        self.url = url
        self.defi = defi

    #----------------------------------------------------------------------
    def info(self):
        '''获取下载信息'''
        html = urllib2.urlopen(self.url).read()
        #icode = re.findall('''icode[:=] *['"](.+?)['"]''',html)[0]
        icode = re.findall("\,icode: '(.+?)'",html)[0]
        #vcode = re.findall("\,vcode: '(.+?)'",html)[0]
        title = re.findall("\,kw: '(.+?)'",html)[0]
        data = json.loads(urllib2.urlopen('http://www.tudou.com/outplay/goto/getItemSegs.action?code=%s' % icode).read())
        print icode,title,data
        links=[]
        if self.defi=='1'and '5' in data:
            data  = data['5']
        elif self.defi=='2' and '3' in data:
            data  = data['3']
        elif self.defi=='3' and '2' in data:
            data  = data['2']
        else:
            data = data.items()[0][1]
        for i in data:
            chunk = urllib2.urlopen('http://v2.tudou.com/f?id=%s'%i['k']).read()
            root = ElementTree.fromstring(chunk)
            link = root.getiterator('f')[0].text
            link = re.findall("(.+?)\&bc=",link)[0]
            links.append(link)
        title = self.trim_title(title.decode('utf8'))
        return (title, links, 'flv')

    #----------------------------------------------------------------------
    def trim_title(self,title):
        '''格式化视频标题'''
        pattern=u'[a-zA-Z0-9\u4e00-\u9fa5]+'
        j=re.findall(pattern,title)
        title=u''
        for i in j:
            title=title+i
        return title.encode(default_encoding)


#----------------------------------------------------------------------
def aria2_conf(links, defi, tmp_dir):
    '''获取分割视频地址，将地址写入aria2c配置文件'''
    aria2_txt_path=os.path.normcase(tmp_dir+'/aria2.txt')
    count = 97
    cb=''
    for i in links:
        cb=cb+i+'\r\n\tout=%s.%s\r\n\tmax-connection-per-server=16\r\n\tmin-split-size=1M\r\n\tsplit=15\r\n'%(chr(count),defi)
        count = count +1
    f=open(aria2_txt_path,'w+')
    f.write(cb)
    f.close()

#----------------------------------------------------------------------
def download(title, defi, tmp_dir, output_dir, proxy):
    '''下载分割视频并合并，分别调用外部程序aria2c Flvbind MP4Box'''
    aria2_txt_path = os.path.normcase(tmp_dir+'/aria2.txt')
    video_tmp = os.path.normcase(tmp_dir+'/videos')
    src_path = os.path.normcase(os.getcwd()+'/src')
    output_dir = os.path.normcase(output_dir)
    proxy = proxy.replace('http://','')
    #header = r'--header="User-Agent: Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.6 Safari/537.36"'
    if proxy:
        proxy=r' --http-proxy="http://%s"'%proxy
    if os.name=='nt':
        if os.path.exists(video_tmp):
            os.system('rd /S /Q %s'%video_tmp)
        os.mkdir(video_tmp)
        print title, u'--正在下载，下载的路径是', output_dir
        dl_split=subprocess.call(args='"%s\\aria2c" -j50 -i%s -d%s %s'%(src_path,aria2_txt_path,video_tmp,proxy),shell=True)
        file_list=os.walk(video_tmp)
        src_flv=''
        src_mp4=''
        for j in file_list.next()[-1]:
            print j
            src_mp4=src_mp4+' -cat '+video_tmp+'\\'+j
            src_flv=src_flv+' '+video_tmp+'\\'+j
        if defi=='flv':
            os.system('"%s\\Flvbind" %s\\%s.%s %s'%(src_path,output_dir,title,defi,src_flv))
        if defi=='mp4':
            os.system('"%s\\MP4Box" -new %s\\%s.%s %s'%(src_path,output_dir,title,defi,src_mp4))
        os.system('rd /S /Q %s'%video_tmp)
        os.remove(aria2_txt_path)
    else:
        if os.path.isdir(video_tmp):
            shutil.rmtree(video_tmp)
        os.mkdir(video_tmp)
        print '%s--正在下载，下载的路径是%s'%(title,output_dir)
        dl_split=subprocess.call(args='aria2c -j50 -i%s -d%s%s'%(aria2_txt_path,video_tmp,proxy),shell=True)
        file_list=os.walk(video_tmp)
        src_mp4=''
        src_flv=''
        for j in sorted(file_list.next()[-1]):
            src_mp4=src_mp4+' -cat '+video_tmp+'/'+j
            src_flv=src_flv+' '+video_tmp+'/'+j
        if defi=='flv':
            os.system('mencoder -ovc copy -oac mp3lame -idx -o %s/%s.%s %s'%(output_dir,title,defi,src_flv))
        if defi=='mp4':
            os.system('MP4Box -new %s/%s.%s %s'%(output_dir,title,defi,src_mp4))
        shutil.rmtree(video_tmp)
        os.remove(aria2_txt_path)    


#----------------------------------------------------------------------
def r1(pattern,text):
    '''re匹配'''
    m=re.search(pattern,text)
    if m:
        return m.group(1)
#----------------------------------------------------------------------
def r1_of(patterns, text):
    '''re匹配'''
    for p in patterns:
        x = r1(p, text)
        if x:
            return x
#----------------------------------------------------------------------
def proxy_switch(proxy):
    '''代理设置'''
    proxy_handler = urllib2.ProxyHandler({"http":proxy})
    null_proxy_handler = urllib2.ProxyHandler({})
    if proxy:
        opener = urllib2.build_opener(proxy_handler)
    else:
        opener = urllib2.build_opener(null_proxy_handler)
    urllib2.install_opener(opener)

#----------------------------------------------------------------------
def get_cb_text():
    '''win读取剪切板'''
    win32clipboard.OpenClipboard()  
    try :
        text = win32clipboard.GetClipboardData(win32con.CF_TEXT)
    except:
        text=''
    win32clipboard.CloseClipboard()
    return text 
#----------------------------------------------------------------------
def get_home_dir():
    '''获取用于文件夹'''
    try:
        path1=os.path.expanduser('~')
    except:
        path1=''
    try:
        path2=os.environ["HOME"]
    except:
        path2=''
    try:
        path3=os.environ["USERPROFILE"]
    except:
        path3=''
    if os.path.exists(path1): return path1
    if os.path.exists(path2): return path2
    if os.path.exists(path3): return path3
    return ''
#----------------------------------------------------------------------
def get_tmp_dir(tmp_dir):
    '''获取缓存文件夹'''
    if not os.path.isdir(tmp_dir):
        for tmp_dir in ('/tmp',r'c:\Windows\Temp'):
            if os.path.isdir(tmp_dir):
                break
            else:
                tmp_dir=os.getcwd()
    else:
        tmp_dir = tmp_dir.encode(default_encoding)    
    return tmp_dir
#----------------------------------------------------------------------
def get_output_dir(output_dir):
    '''获取输出文件夹'''
    if not os.path.isdir(output_dir):
        output_dir1=os.path.normcase(get_home_dir()+'/视频')
        for output_dir in (r'd:',output_dir1,get_home_dir()):
            if os.path.isdir(output_dir):
                break
            else:
                output_dir=os.getcwd()
    else:
        output_dir = output_dir.encode(default_encoding)
    return output_dir
#----------------------------------------------------------------------
def main():
    '''主程序'''
    tmp_dir = default_conf['tmp_dir']
    output_dir = default_conf['output_dir']
    defi = default_conf['defi']
    proxy = default_conf['proxy']
    
    print 'Online Video Download-----@zhiyuan'
    help=u'Usage:\tovd [-h] [-f] [-p] [-o] [-t] url\r\n\
Options:\r\n\
-h:\t帮助\r\n\
-f:\t清晰度 1:高清MP4 2:超清Flv 3:高清Flv 4:标清Flv 例:-f1 默认:1\r\n\
-p:\t代理 例：-p127.0.0.1:1998 默认:不启用\r\n-o:\t输出文件夹 例：-od:\download\ 默认:D盘或用户文件夹\r\n\
-t:\t临时文件夹 默认:系统默认缓存文件夹\r\n\
url:\t视频地址 例：http://v.youku.com/v_show/id_*********.html\r\n\
示例:\tovd -p127.0.0.1:1998 -f2 -od:\download http://v.youku.com/v_show/id_*********.html'

    try:
        opts,args=getopt.getopt(sys.argv[1:],"hf:p:o:t:")
    except BaseException, e:
        print e
        print help
        sys.exit()

    for o,a in opts:
        if o=='-h':
            print help
            sys.exit()
        elif o=='-f':
            defi = a
        elif o=='-p':
            proxy = a
        elif o=='-t':
            tmp_dir = a
        elif o=='-o':
            output_dir=a
        else:
            print help
            sys.exit()
    if not args:
        if get_cb_text():
            args.append(get_cb_text().decode(default_encoding))
        else:
            print help
            sys.exit()

    tmp_dir = get_tmp_dir(tmp_dir)
    output_dir = get_output_dir(output_dir)
    proxy_switch(proxy)
    
    for url in args:
        print u'开始下载:', url
        if 'youku' in url:
            ovd = Youku(url, defi)
        elif 'sohu' in url:
            ovd = Sohu(url, defi)
        #elif 'tudou' in url:
            #ovd = Tudou(url, defi)
        else:
            continue
        try:
            info = ovd.info()
        except BaseException, e:
            print e
            continue
        title = info[0]
        links = info[1]
        defi = info[2]
        try:
            aria2_conf(links, defi, tmp_dir)
        except BaseException, e:
            print e
            continue
        try:
            download(title, defi, tmp_dir, output_dir, proxy)
        except BaseException, e:
            print e
            continue        

if __name__ == '__main__':
    main()


