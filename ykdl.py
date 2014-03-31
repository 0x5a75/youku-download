#!usr/bin/env python
#coding=utf-8
import re
import urllib2
import os
import sys
import getopt
import shutil
import subprocess
import locale
import socket
import win32con
import win32clipboard
socket.setdefaulttimeout(15)
default_encoding = locale.getdefaultlocale()[-1]

#----------------------------------------------------------------------
def win32_unicode_argv():
    """Uses shell32.GetCommandLineArgvW to get sys.argv as a list of Unicode
    strings.

    Versions 2.x of Python don't support Unicode in sys.argv on
    Windows, with the underlying Windows API instead replacing multi-byte
    characters with '?'.
    """

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
        # Remove Python executable and commands if present
        start = argc.value - len(sys.argv)
        return [argv[i] for i in
                xrange(start, argc.value)]
sys.argv = win32_unicode_argv()

########################################################################
class Youku(object):
    """youku下载类"""

    #----------------------------------------------------------------------
    def __init__(self,url,defi):
        """参数：视频地址，视频清晰度（1，2，3，4）"""
        self.url = url
        self.defi = defi

    #----------------------------------------------------------------------
    def title(self):
        """获取视频标题"""
        id = self.video_id()
        print id
        html = urllib2.urlopen('http://v.youku.com/v_show/id_%s.html'%id).read()
        video_title = r1_of([r'<title>([^<>]*)</title>'], html).decode('utf-8')
        video_title= self.trim_title(video_title)
        return video_title
    #----------------------------------------------------------------------
    def m3u8(self):
        """下载视频M3U8"""
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
        return chunk
    #----------------------------------------------------------------------  
    def video_id(self):
        """获取视频ID"""
        patterns = [r'^http://v.youku.com/v_show/id_([\w=]+).html',
                    r'^http://player.youku.com/player.php/sid/([\w=]+)/v.swf',
                    r'^loader\.swf\?VideoIDS=([\w=]+)',
                    r'^([\w=]+)$']
        return r1_of(patterns, self.url)
    #----------------------------------------------------------------------
    def trim_title(self,title):
        """格式化视频标题"""
        title = title.replace(u' - 视频 - 优酷视频 - 在线观看', '')
        title = title.replace(u' - 专辑 - 优酷视频', '')
        title = re.sub(ur'—([^—]+)—优酷网，视频高清在线观看', '', title)
        pattern=u'[a-zA-Z0-9\u4e00-\u9fa5]+'
        j=re.findall(pattern,title)
        title=u''
        for i in j:
            title=title+i
        return title.encode(default_encoding)

#----------------------------------------------------------------------
def get_link(m3u8, tmp_dir):
    """分析M3U8，获取分割视频地址，将地址写入aria2c配置文件"""
    aria2_txt_path=os.path.normcase(tmp_dir+'/aria2.txt')
    defi='mp4'
    m3u8_lines = m3u8.readlines()
    cb = ''
    while True:
        for i in m3u8_lines:
            try:
                m=re.match(r'http.*%s'%defi,i)
                if m.group() not in cb:
                    cb=cb+m.group()+'\r\n\tmax-connection-per-server=16\r\n\tmin-split-size=1M\r\n\tsplit=15\r\n'
            except BaseException, e:
                #print e
                continue
        if cb=='':
            defi='flv'
        else:
            break
    f=open(aria2_txt_path,'w+')
    f.write(cb)
    f.close()
    return defi

#----------------------------------------------------------------------
def download(proxy, defi, tmp_dir, video_title, output_dir):
    '''下载分割视频并合并，分别调用外部程序aria2c Flvbind MP4Box'''
    aria2_txt_path=os.path.normcase(tmp_dir+'/aria2.txt')
    video_tmp=os.path.normcase(tmp_dir+'/videos')
    src_path=os.path.normcase(os.getcwd()+'/src')
    output=os.path.normcase(get_output_dir(output_dir))
    proxy=proxy.replace('http://','')    
    if proxy:
        proxy=r' --http-proxy="http://%s"'%proxy
    if os.name=='nt':
        if os.path.exists(video_tmp):
            os.system('rd /S /Q %s'%video_tmp)
        os.mkdir(video_tmp)
        print video_title, u'--正在下载，下载的路径是', output
        dl_split=subprocess.call(args='"%s\\aria2c" -j50 -i%s -d%s %s'%(src_path,aria2_txt_path,video_tmp,proxy),shell=True)
        file_list=os.walk(video_tmp)
        src_flv=''
        src_mp4=''
        for j in file_list.next()[-1]:
            src_mp4=src_mp4+' -cat '+video_tmp+'\\'+j
            src_flv=src_flv+' '+video_tmp+'\\'+j
        if defi=='flv':
            os.system('"%s\\Flvbind" %s\\%s.%s %s'%(src_path,output,video_title,defi,src_flv))
        if defi=='mp4':
            os.system('"%s\\MP4Box" -new %s\\%s.%s %s'%(src_path,output,video_title,defi,src_mp4))
        os.system('rd /S /Q %s'%video_tmp)
        os.remove(aria2_txt_path)
    else:
        if os.path.isdir(video_tmp):
            shutil.rmtree(video_tmp)
        os.mkdir(video_tmp)
        print '%s--正在下载，下载的路径是%s'%(video_title,output)
        dl_split=subprocess.call(args='aria2c -j50 -i%s -d%s%s'%(aria2_txt_path,video_tmp,proxy),shell=True)
        file_list=os.walk(video_tmp)
        src_mp4=''
        src_flv=''
        for j in sorted(file_list.next()[-1]):
            src_mp4=src_mp4+' -cat '+video_tmp+'/'+j
            src_flv=src_flv+' '+video_tmp+'/'+j
        if defi=='flv':
            os.system('mencoder -ovc copy -oac mp3lame -idx -o %s/%s.%s %s'%(output,video_title,defi,src_flv))
        if defi=='mp4':
            os.system('MP4Box -new %s/%s.%s %s'%(output,video_title,defi,src_mp4))
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
    print 'Online Video Download-----@zhiyuan'
    help=u'Usage:\tovd [-h] [-f] [-p] [-o] [-t] url\r\n\
Options:\r\n\
-h:\t帮助\r\n\
-f:\t清晰度 1:高清MP4 2:超清Flv 3:高清Flv 4:标清Flv 例:-f1 默认:1\r\n\
-p:\t代理 例：-p127.0.0.1:1998 默认:不启用\r\n-o:\t输出文件夹 例：-od:\download\ 默认:D盘或用户文件夹\r\n\
-t:\t临时文件夹 默认:系统默认缓存文件夹\r\n\
url:\tyouku视频地址 例：http://v.youku.com/v_show/id_*********.html\r\n\
示例:\tovd -p127.0.0.1:1998 -f2 -od:\download http://v.youku.com/v_show/id_*********.html'
    try:
        opts,args=getopt.getopt(sys.argv[1:],"hf:p:o:t:")
        print opts ,args
    except BaseException, err:
        print err
        print help
        sys.exit()
    tmp_dir=''
    output_dir=''
    defi='1'
    promot=''
    proxy=''
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
            
    tmp_dir=get_tmp_dir(tmp_dir)
    proxy_switch(proxy)
    for url in args:
        print u'开始下载:', url
        youku = Youku(url, defi)
        try:
            title = youku.title()
        except BaseException, e:
            print e
            continue
        try:
            defi = get_link(youku.m3u8(), tmp_dir)
            print defi
        except BaseException, e:
            print e
            continue
        try:
            download(proxy, defi, tmp_dir, title, output_dir)
        except BaseException, e:
            promot = e
            continue

if __name__ == '__main__':
    main()


