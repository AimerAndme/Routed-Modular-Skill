# 模块调用契约 v1

输入为 JSON 对象；当前示例要求 text 为字符串，允许空字符串。
脚本从 stdin 读取输入，仅向 stdout 输出一个 JSON 对象，且必须含 result 对象。
失败向 stderr 写诊断并以非零状态退出，不输出伪造结果。
执行器包装成功结果为 status、module_id、result；失败为 status、error。
多个模块的结果不自动聚合，不隐含调用顺序或业务依赖。
