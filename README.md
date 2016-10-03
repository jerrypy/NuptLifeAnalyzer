# 邮迹 | 南邮时光机

邮迹是一个类淘宝时光机的应用，通过爬虫来展示过去的大学时光。

-----------------

## 怎么看懂这个代码？

1. 学会Python
2. 学会Flask，跟着[《Flask Web开发:基于Python的Web应用开发实战》](https://www.amazon.cn/Flask-Web%E5%BC%80%E5%8F%91-%E5%9F%BA%E4%BA%8EPython%E7%9A%84Web%E5%BA%94%E7%94%A8%E5%BC%80%E5%8F%91%E5%AE%9E%E6%88%98-%E6%A0%BC%E6%9E%97%E5%B8%83%E6%88%88/dp/B00QT2TQCG/ref=sr_1_1?ie=UTF8&qid=1475487873&sr=8-1&keywords=flask)这本书一步一步做下去，最少看到工厂模式为止。
3. 了解Celery，以及怎么在[Flask工厂模式中使用Celery](http://blog.miguelgrinberg.com/post/celery-and-the-flask-application-factory-pattern)
4. 了解Redis和Mongo的基本使用
5. HTML5,CSS3动画,Javascript的基础知识（**请绝对绝对不要和我一样写前端**）

好了，你现在肯定能看懂它们了~

## 怎么部署？

1. 你需要`app_config.py`,和`NuptCrawlers/config.py`，配置参考`app_config.example.py`和`NuptCrawlers/config.example.py`
2. 我用了supervisor来管理服务，配置参考`supervisord.conf.example`
3. pip install -r requirements.txt 安装依赖
4. 当然还需要安装Redis和Mongo，具体配置要求，看代码吧~

## 其他问题

提issue或者给我发邮件把~
希望有人能把它做的更好。
