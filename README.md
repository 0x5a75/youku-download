youku-download
==============

优酷 搜狐 土豆 在线视频下载，支持各种清晰度

默认监测windows剪切板，复制视频网址，运行程序即可。

Usage:\tovd [-h] [-f] [-p] [-o] [-t] url \n
Options:\n
-h: 帮助\n
-f: 清晰度 1:最高清晰度 2:超清 3:高清 4:标清 例:-f1 默认:1\n
-p: 代理 例：-p127.0.0.1:1998 默认:不启用\n
-o: 输出文件夹 例：-od:\download\ 默认:D盘或用户文件夹\n
-t: 临时文件夹 默认:系统默认缓存文件夹\n
url:  视频地址 例：http://v.youku.com/v_show/id_*********.html\n
示例: ovd -p127.0.0.1:1998 -f2 -od:\download http://v.youku.com/v_show/id_*********.html'\n
