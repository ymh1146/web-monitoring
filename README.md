## 功能特点

- 支持多站点监控
- 自动检测网站状态
- 可视化状态展示
- 支持自定义监控网站顺序
- 支持公开/私有模式
- 默认展示24小时、7天、30天状态

## 即将支持

- [x] ~~异常推送通知（慢慢来，我很懒）~~
- [x] ~~网站favicon.ico~~
- [x] ~~自定义请求，支持get和post~~
- [x] ~~域名有效期（本来想用whois自动识别，但查询了很多api都不能匹配小众域名，所以手动设置）~~
- [x] ~~1.5版本新增自定义推送，支持post请求，支持headers、body、timeout设置~~
- [ ] 还没想到

## 快速开始

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 运行程序：

```bash
python app.py
```

3. 访问界面：
   - 打开浏览器访问 `http://localhost:5000`
   - 默认密码 admin , 可在设置中修改

## 升级

1、重新git代码

2、运行

```
python up_app.py
```

本次升级因为数据库结构发生变化，只同步网站配置，不同步其他内容，如果网站不多，最好重新安装使用。密码恢复默认密码：admin

## 许可证

MIT License @ heilo.cn
