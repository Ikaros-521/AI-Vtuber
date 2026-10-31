
# 生成protobuf的Python版结构体脚本
## 声明：本代码库所有代码均只用于学习研究交流，严禁用于包括但不限于商业谋利、破坏系统、盗取个人信息等不良不法行为，违反此声明使用所产生的一切后果均由违反声明使用者承担。
## 侵权或涉及相关利益请联系作者：[微博](https://weibo.com/u/7751075499)、[B站](https://space.bilibili.com/4690313)、[邮箱](mailto:kukushka@126.com)
> 2024年1月2日

## 0.安装[betterproto](https://github.com/danielgtaylor/python-betterproto)
```shell
pip install betterproto
```
注意`betterproto`版本为`2.0.0b6`，必须为2.0以上版本
## 1.在当前目录下打开终端，输入：
```shell
protoc -I . --python_betterproto_out=. douyin.proto
```
当前目录下生成文件`douyin.py`和`__init__.py`即为成功（此程序已经生成可用）。

## Done