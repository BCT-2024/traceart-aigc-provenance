# 论文一数据集校验报告

- 元数据总行数：300
- 图片目录数量：{'images_positive_general': 200, 'images_negative_other': 50, 'images_natural_512': 50}
- 分组数量：{'positive': 200, 'negative_ai': 50, 'natural': 50}
- 图片尺寸分布：{(512, 512): 300}
- 重复 SHA-256：0

## 分组标签

- positive platform_id：{'TraceArt-Lab': 200}
- positive is_platform_sample：{'1': 200}
- negative_ai platform_id：{'Other-Platform': 50}
- negative_ai is_platform_sample：{'0': 50}
- natural platform_id：{'Natural-Image': 50}
- natural is_platform_sample：{'0': 50}

## 类别分布

- positive：{'landscape': 25, 'portrait': 25, 'city': 25, 'object': 25, 'animal': 25, 'food': 25, 'fantasy': 25, 'abstract': 25}
- negative_ai：{'landscape': 10, 'portrait': 10, 'city': 5, 'object': 5, 'animal': 5, 'food': 5, 'fantasy': 5, 'abstract': 5}
- natural：{'animal': 10, 'architecture': 10, 'food': 10, 'landscape': 10, 'plant': 10}

## 自然图 512 处理

- 参数表行数：50
- 缩放模式：{'short_side_resize_center_crop': 50}
- 输出尺寸：{('512', '512'): 50}
- 哈希不匹配数：0

## 结论

未发现错误。

