# API endpoints

`auth.py` 提供注册、登录、当前用户和退出；`learning.py` 提供课程、进度、测验、画像和前测分析。
资源通过上一级 `router.py` 统一挂载。鉴权和同源检查从 `app.api.dependencies` 引用，端点之间不互相调用。
输入输出结构位于 `app.schemas`；新资源按实际用例增加，不预先创建空端点。

