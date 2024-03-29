# 大饼

## 评测机（直接使用dmoj的）

* [x] docker中运行，能够自我还原
* [x] 分布式部署
* [x] 支持交互题（checker grader）（testlib）
* [x] 判活、可靠性保证
* [x] 安全性保证
* [x] 编译环境配置与更新容易

svr.py是起步阶段的测试服务器，可以连接评测机

配置步骤参考https://docs.dmoj.ca/#/judge/setting_up_a_judge

也可以参考rundocker.txt

## 后端服务器

* [ ] 单数据库多实例模型支持，登录态互斥
* [ ] 提供web api
* [ ] OSS
* [ ] 验证码系统
* [ ] 操作日志

### 题目档系统

* [ ] 单条详细提交记录（仿洛谷）
* [ ] 批量导入（受信用户）
* [ ] 单条编辑、数据、spj导入（非受信用户需要限制）
* [ ] 标程预导入、在线数据生成（受信用户）
* [ ] 自动处理数据crlf
* [ ] 查看错误原因，或testlib那种错误提示（wrong answer expected '1', found '0'）
* [ ] 代码比较（codeforces那种类似git的Previous Submission和Current Submission的Compare）

### 比赛系统

* [ ] 看榜，外榜
* [ ] 基本的交题与罚时
* [ ] 公告广播（牛客）
* [ ] rejudge，赛时修锅
* [ ] 管理端错误点查看（atcoder）
* [ ] 简易查重
* [ ] Clarification
* [ ] IOI、ACM、CF赛制支持
* [ ] Hack功能
* [ ] 发气球界面
* [ ] 自测接口
* [ ] 封榜、管理员手动解封

## Polygon出题系统

* [ ] 题目导入导出
* [ ] Validator
* [ ] 压力测试、TLE/WA测试
* [ ] issue
* [ ] 版本管理

## 数据库

* [ ] 覆写式合并
* [ ] 备份、恢复
