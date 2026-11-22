# Toy 资源后台

用 https://app.pagescms.org/ 登录并选择 `a7987083/zonoemenu-config` 的 `main` 分支。

在 **Toy 游戏资源** 中搜索游戏名称、编辑或新增记录。保存会提交到 `toy/entries/<id>.json`，GitHub Actions 随后自动生成 `toy/resources.json`。Toy 仍读取原来的 GitHub Raw 主地址和 jsDelivr 备用地址。

**重要约束**
- 请勿直接编辑 `toy/resources.json`：这是生成产物。
- 修改现有记录时不要更改 `id`，否则用户收藏可能失效。
- 新增记录需设置唯一、稳定、仅含英文字母数字及 `_-` 的 ID。
- 删除记录将导致该资源从下次发布的目录中消失。
- 若修改分类 ID，需同时迁移引用该分类的资源。
- 后台提交后请查看 [Actions](https://github.com/a7987083/zonoemenu-config/actions/workflows/build-toy-resources.yml) 是否成功，失败时线上目录保持上一份。
- 当前支持 `url` 和 `links.百度网盘`；链接必须是有效、获授权的分享内容。

手工验证：`python3 .github/scripts/build-toy-resources.py --check`。
