# 论文一实验结果报告

## 实验设置

- 数据库记录数：200
- 嵌入图像数：200
- 攻击评价样本数：3000
- 负样本数：100
- 水印方法：DWT+DCT 盲水印
- 载荷结构：平台 ID、generation_id、模型版本、时间摘要、内容摘要、CRC16、RS(32,16)
- 重复编码：4 次比特重复
- 嵌入强度：alpha=28

## 图像质量

- 平均 PSNR：39.6522 dB
- 平均 SSIM：0.998980

## 鲁棒性

| Attack | Success rate | Mean BER | Mean score | High | Medium | Low |
|---|---:|---:|---:|---:|---:|---:|
| clean | 1.0000 | 0.0017 | 0.9995 | 200 | 0 | 0 |
| jpeg quality=90 | 1.0000 | 0.0022 | 0.9995 | 200 | 0 | 0 |
| jpeg quality=70 | 0.9950 | 0.0042 | 0.9958 | 199 | 0 | 1 |
| jpeg quality=50 | 0.9950 | 0.0082 | 0.9956 | 199 | 0 | 1 |
| resize scale=0.75 | 0.9950 | 0.0064 | 0.9955 | 199 | 0 | 1 |
| resize scale=1.5 | 1.0000 | 0.0019 | 0.9995 | 200 | 0 | 0 |
| crop ratio=0.9 | 0.9200 | 0.0850 | 0.9377 | 184 | 6 | 10 |
| gaussian_noise sigma=3 | 1.0000 | 0.0020 | 0.9999 | 200 | 0 | 0 |
| gaussian_noise sigma=8 | 0.9950 | 0.0033 | 0.9961 | 199 | 0 | 1 |
| salt_pepper amount=0.002 | 0.9950 | 0.0351 | 0.9958 | 199 | 0 | 1 |
| brightness_contrast | 0.9600 | 0.0238 | 0.9689 | 192 | 2 | 6 |
| blur ksize=3 | 0.9800 | 0.0337 | 0.9846 | 196 | 1 | 3 |
| screenshot | 0.9950 | 0.0105 | 0.9955 | 199 | 0 | 1 |
| real_screen_capture | 0.0000 | 0.5353 | 0.1456 | 0 | 0 | 200 |
| print_scan | 0.0000 | 0.4948 | 0.1423 | 0 | 0 | 200 |

## 负样本误报

- 负样本总数：100
- 误报数：0
- 误报率：0.0000

## 图表

![quality](figures/quality_distribution.png)

![success](figures/robustness_success.png)

![ber](figures/robustness_ber.png)

![trust](figures/trust_distribution.png)

![fpr](figures/false_positive.png)

